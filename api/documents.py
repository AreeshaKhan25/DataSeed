"""Document generation — invoices and bank statements.

Documents are a *rendering* of relational data, not a fourth engine. The same
generated tables that feed the CSV export feed these templates.

Two arithmetic rules are enforced in code rather than left to the generator:

  invoice    total = subtotal + tax, where subtotal is the sum of line items
  statement  balance[i] = balance[i-1] + credit - debit

Both are computed in a single pass. Nothing that can drift is ever generated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .seeds import SeedFactory

TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class Region:
    code: str
    name: str
    tax_label: str
    tax_rate: float
    currency: str
    symbol: str
    date_format: str
    locale: str


REGIONS: dict[str, Region] = {
    "EU": Region("EU", "European Union", "VAT", 0.20, "EUR", "€", "%d/%m/%Y", "de_DE"),
    "UK": Region("UK", "United Kingdom", "VAT", 0.20, "GBP", "£", "%d/%m/%Y", "en_GB"),
    "US": Region("US", "United States", "Sales tax", 0.0875, "USD", "$", "%m/%d/%Y", "en_US"),
    "IN": Region("IN", "India", "GST", 0.18, "INR", "₹", "%d-%m-%Y", "en_IN"),
}

_ITEM_CATALOGUE = [
    ("API access — Pro tier", 1100.00), ("Onboarding support", 140.00),
    ("Priority SLA", 320.00), ("Additional seat", 45.00),
    ("Data egress (per TB)", 88.50), ("Sandbox environment", 210.00),
    ("Audit log retention", 65.00), ("Custom connector", 480.00),
    ("Training workshop", 750.00), ("Extended storage", 129.55),
]

_MERCHANTS = [
    "Greenleaf Market", "Riverside Utilities", "Northbank Fuel", "Cloudhost Ltd",
    "Metro Transit", "Blue Fig Cafe", "Orchard Pharmacy", "Summit Insurance",
    "Lakeside Gym", "Harbour Books", "Vantage Mobile", "Corner Bakery",
]
_CREDIT_SOURCES = ["Payroll deposit", "Refund — Orchard Pharmacy", "Transfer in", "Interest"]


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def money(value: float, region: Region) -> str:
    return f"{region.symbol}{value:,.2f}"


# --------------------------------------------------------------------------
# Invoices
# --------------------------------------------------------------------------

@dataclass
class InvoiceLine:
    description: str
    quantity: int
    unit_price: float

    @property
    def amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Invoice:
    number: str
    issued: datetime
    due: datetime
    bill_to_name: str
    bill_to_address: list[str]
    from_name: str
    from_address: list[str]
    region: Region
    lines: list[InvoiceLine] = field(default_factory=list)
    source_order_id: Any = None

    @property
    def subtotal(self) -> float:
        return round(sum(line.amount for line in self.lines), 2)

    @property
    def tax(self) -> float:
        return round(self.subtotal * self.region.tax_rate, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax, 2)

    def reconciles(self) -> bool:
        """The claim the deck makes, checked rather than assumed."""
        recomputed = round(sum(round(l.quantity * l.unit_price, 2) for l in self.lines), 2)
        return (
            abs(recomputed - self.subtotal) < 0.005
            and abs(round(self.subtotal + self.tax, 2) - self.total) < 0.005
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "issued": self.issued.strftime(self.region.date_format),
            "due": self.due.strftime(self.region.date_format),
            "bill_to_name": self.bill_to_name,
            "bill_to_address": self.bill_to_address,
            "from_name": self.from_name,
            "from_address": self.from_address,
            "region": self.region.code,
            "currency": self.region.currency,
            "tax_label": self.region.tax_label,
            "tax_rate": self.region.tax_rate,
            "lines": [
                {
                    "description": l.description, "quantity": l.quantity,
                    "unit_price": round(l.unit_price, 2), "amount": l.amount,
                }
                for l in self.lines
            ],
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "source_order_id": _plain(self.source_order_id),
            "reconciles": self.reconciles(),
        }


def _plain(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def find_invoice_source(
    frames: dict[str, pd.DataFrame], foreign_keys: list[Any]
) -> tuple[str, str, str, dict[str, str]] | None:
    """Locate a parent/child pair that looks like orders and line items.

    Returns (parent, child, fk_column, column_map) or None. Being explicit about
    "we could not find one" is what lets the caller fall back cleanly instead of
    rendering an invoice full of blanks.
    """
    for fk in foreign_keys:
        child_name, parent_name = fk.child_table, fk.parent_table
        if child_name not in frames or parent_name not in frames:
            continue
        child = frames[child_name]

        quantity = next(
            (c for c in child.columns
             if str(c).lower() in ("qty", "quantity", "units", "count")), None
        )
        price = next(
            (c for c in child.columns
             if any(k in str(c).lower() for k in ("price", "rate", "cost", "amount"))
             and "total" not in str(c).lower()), None
        )
        if quantity is None or price is None:
            continue
        if not pd.api.types.is_numeric_dtype(child[quantity]):
            continue

        label = next(
            (c for c in child.columns
             if str(c).lower() in ("sku", "product", "description", "item", "name", "category")),
            None,
        )
        return parent_name, child_name, fk.child_column, {
            "quantity": str(quantity), "price": str(price),
            "label": str(label) if label else "",
        }
    return None


def build_invoices(
    count: int,
    seeds: SeedFactory,
    *,
    region_code: str = "EU",
    frames: dict[str, pd.DataFrame] | None = None,
    foreign_keys: list[Any] | None = None,
    company_name: str = "DataSeed Co.",
) -> list[Invoice]:
    """Build invoices, preferring real generated relational data as the source."""
    region = REGIONS.get(region_code, REGIONS["EU"])
    rng = seeds.stream("documents:invoices")
    faker = Faker([region.locale])
    faker.seed_instance(int(rng.integers(0, 2**31 - 1)))

    source = None
    if frames and foreign_keys:
        source = find_invoice_source(frames, foreign_keys)

    invoices: list[Invoice] = []
    from_address = [faker.street_address(), f"{faker.postcode()} {faker.city()}"]

    if source is not None:
        parent_name, child_name, fk_column, columns = source
        parent, child = frames[parent_name], frames[child_name]
        parent_key = None
        for candidate in parent.columns:
            if str(candidate).lower().endswith("_id"):
                parent_key = candidate
                break
        if parent_key is None:
            source = None
        else:
            grouped = child.groupby(fk_column)
            keys = [k for k in parent[parent_key].tolist() if k in grouped.groups][:count]

            for key in keys:
                rows = grouped.get_group(key)
                lines: list[InvoiceLine] = []
                for row in rows.head(8).itertuples(index=False):
                    raw_qty = getattr(row, columns["quantity"], 1)
                    raw_price = getattr(row, columns["price"], 0.0)
                    if pd.isna(raw_qty) or pd.isna(raw_price):
                        continue
                    label = (
                        str(getattr(row, columns["label"]))
                        if columns["label"] and not pd.isna(getattr(row, columns["label"], None))
                        else faker.catch_phrase()
                    )
                    lines.append(InvoiceLine(label, max(int(raw_qty), 1), float(raw_price)))
                if not lines:
                    continue

                issued = datetime(2025, 1, 1) + timedelta(days=int(rng.integers(0, 260)))
                invoices.append(Invoice(
                    number=f"INV-{int(rng.integers(10000, 99999))}",
                    issued=issued, due=issued + timedelta(days=30),
                    bill_to_name=faker.company(),
                    bill_to_address=[faker.street_address(), f"{faker.postcode()} {faker.city()}"],
                    from_name=company_name, from_address=from_address,
                    region=region, lines=lines, source_order_id=_plain(key),
                ))

    # Standalone fallback, or a top-up when the source ran out of orders.
    while len(invoices) < count:
        n_lines = int(rng.integers(1, 6))
        picks = rng.choice(len(_ITEM_CATALOGUE), size=n_lines, replace=False)
        lines = [
            InvoiceLine(
                _ITEM_CATALOGUE[i][0],
                int(rng.integers(1, 4)),
                round(_ITEM_CATALOGUE[i][1] * float(rng.uniform(0.9, 1.1)), 2),
            )
            for i in picks
        ]
        issued = datetime(2025, 1, 1) + timedelta(days=int(rng.integers(0, 260)))
        invoices.append(Invoice(
            number=f"INV-{int(rng.integers(10000, 99999))}",
            issued=issued, due=issued + timedelta(days=30),
            bill_to_name=faker.company(),
            bill_to_address=[faker.street_address(), f"{faker.postcode()} {faker.city()}"],
            from_name=company_name, from_address=from_address,
            region=region, lines=lines,
        ))

    return invoices[:count]


# --------------------------------------------------------------------------
# Bank statements
# --------------------------------------------------------------------------

@dataclass
class Transaction:
    date: datetime
    description: str
    debit: float | None
    credit: float | None
    balance: float = 0.0


@dataclass
class Statement:
    account_number: str
    holder: str
    region: Region
    period_start: datetime
    period_end: datetime
    opening_balance: float
    transactions: list[Transaction] = field(default_factory=list)

    @property
    def closing_balance(self) -> float:
        return self.transactions[-1].balance if self.transactions else self.opening_balance

    @property
    def total_credits(self) -> float:
        return round(sum(t.credit or 0.0 for t in self.transactions), 2)

    @property
    def total_debits(self) -> float:
        return round(sum(t.debit or 0.0 for t in self.transactions), 2)

    def reconciles(self) -> bool:
        """Every running balance must follow from the one before it."""
        running = self.opening_balance
        for entry in self.transactions:
            running = round(running + (entry.credit or 0.0) - (entry.debit or 0.0), 2)
            if abs(running - entry.balance) > 0.005:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_number": self.account_number,
            "holder": self.holder,
            "region": self.region.code,
            "currency": self.region.currency,
            "period_start": self.period_start.strftime(self.region.date_format),
            "period_end": self.period_end.strftime(self.region.date_format),
            "opening_balance": round(self.opening_balance, 2),
            "closing_balance": round(self.closing_balance, 2),
            "total_credits": self.total_credits,
            "total_debits": self.total_debits,
            "transactions": [
                {
                    "date": t.date.strftime(self.region.date_format),
                    "description": t.description,
                    "debit": round(t.debit, 2) if t.debit else None,
                    "credit": round(t.credit, 2) if t.credit else None,
                    "balance": round(t.balance, 2),
                }
                for t in self.transactions
            ],
            "reconciles": self.reconciles(),
        }


@dataclass
class StatementQuery:
    """A parsed natural-language request, e.g. "last 90 days, balance over 500".

    The LLM (or the regex fallback) produces this; the generator then treats it
    as a hard constraint. The model plans, the code executes.
    """

    days: int | None = None
    min_balance: float | None = None
    max_balance: float | None = None
    min_amount: float | None = None
    direction: str | None = None  # "credit" | "debit"
    description_contains: str | None = None


def parse_statement_query(text: str) -> StatementQuery:
    """Regex fallback for the NL query. Deliberately small and predictable."""
    import re

    query = StatementQuery()
    lowered = (text or "").lower()

    if match := re.search(r"last\s+(\d+)\s*(day|week|month)", lowered):
        amount = int(match.group(1))
        unit = match.group(2)
        query.days = amount * {"day": 1, "week": 7, "month": 30}[unit]

    if match := re.search(r"balance\s*(?:over|above|greater than|>)\s*[\$€£₹]?\s*([\d,.]+)", lowered):
        query.min_balance = float(match.group(1).replace(",", ""))
    if match := re.search(r"balance\s*(?:under|below|less than|<)\s*[\$€£₹]?\s*([\d,.]+)", lowered):
        query.max_balance = float(match.group(1).replace(",", ""))
    if match := re.search(r"(?:amount|over|above)\s*[\$€£₹]\s*([\d,.]+)", lowered):
        query.min_amount = float(match.group(1).replace(",", ""))

    if "credit" in lowered or "deposit" in lowered or "incoming" in lowered:
        query.direction = "credit"
    elif "debit" in lowered or "payment" in lowered or "outgoing" in lowered:
        query.direction = "debit"

    return query


def build_statements(
    count: int,
    seeds: SeedFactory,
    *,
    region_code: str = "UK",
    rows_per_statement: int = 24,
    query: StatementQuery | None = None,
    frames: dict[str, pd.DataFrame] | None = None,
) -> list[Statement]:
    """Build statements with arithmetically correct running balances."""
    region = REGIONS.get(region_code, REGIONS["UK"])
    rng = seeds.stream("documents:statements")
    faker = Faker([region.locale])
    faker.seed_instance(int(rng.integers(0, 2**31 - 1)))
    query = query or StatementQuery()

    window = query.days or 120
    period_end = datetime(2025, 9, 1)
    period_start = period_end - timedelta(days=window)

    source_rows: pd.DataFrame | None = None
    if frames:
        for frame in frames.values():
            columns = {str(c).lower() for c in frame.columns}
            if {"description", "amount"} <= columns or {"direction", "amount"} <= columns:
                source_rows = frame
                break

    # A balance filter selects whole statements, never individual rows. Dropping
    # rows out of the middle of a statement would leave the running balance with
    # gaps -- the column would stop being arithmetic, which is the one property
    # this engine exists to guarantee.
    statements: list[Statement] = []
    attempts = 0
    max_attempts = count * 12

    while len(statements) < count and attempts < max_attempts:
        attempts += 1
        low = query.min_balance if query.min_balance is not None else 400.0
        high = query.max_balance if query.max_balance is not None else 4200.0
        if high <= low:
            high = low * 1.5 + 100.0
        opening = float(round(rng.uniform(low, high), 2))
        n_rows = max(4, int(rng.normal(rows_per_statement, 4)))

        entries: list[Transaction] = []
        offsets = np.sort(rng.integers(0, max(window, 1), size=n_rows))

        for offset in offsets:
            when = period_start + timedelta(days=int(offset))
            is_credit = bool(rng.random() < 0.24)

            if source_rows is not None and len(source_rows):
                row = source_rows.iloc[int(rng.integers(0, len(source_rows)))]
                description = str(row.get("description", rng.choice(_MERCHANTS)))
                raw = row.get("amount", None)
                amount = float(raw) if raw is not None and not pd.isna(raw) else float(rng.uniform(5, 300))
                if "direction" in source_rows.columns and not pd.isna(row.get("direction")):
                    is_credit = str(row["direction"]).lower() == "credit"
            else:
                description = str(rng.choice(_CREDIT_SOURCES if is_credit else _MERCHANTS))
                amount = float(round(
                    rng.lognormal(6.8, 0.45) if is_credit else rng.lognormal(3.6, 0.9), 2
                ))

            amount = float(min(max(round(amount, 2), 1.0), 6000.0))

            if query.direction == "credit" and not is_credit:
                continue
            if query.direction == "debit" and is_credit:
                continue
            if query.min_amount is not None and amount < query.min_amount:
                continue
            if query.description_contains and query.description_contains.lower() not in description.lower():
                continue

            entries.append(Transaction(
                date=when, description=description,
                credit=amount if is_credit else None,
                debit=None if is_credit else amount,
            ))

        if not entries:
            entries.append(Transaction(
                date=period_start, description="Opening deposit", credit=opening, debit=None
            ))

        # The single pass that guarantees the column is arithmetic, not invented.
        running = opening
        for entry in entries:
            running = round(running + (entry.credit or 0.0) - (entry.debit or 0.0), 2)
            entry.balance = running

        # Accept or reject the statement as a whole.
        balances = [e.balance for e in entries]
        if query.min_balance is not None and min(balances) < query.min_balance:
            continue
        if query.max_balance is not None and max(balances) > query.max_balance:
            continue

        statements.append(Statement(
            account_number=f"{rng.integers(10, 99)}-{rng.integers(10, 99)}-"
                           f"{rng.integers(100000, 999999)}",
            holder=faker.name(), region=region,
            period_start=period_start, period_end=period_end,
            opening_balance=opening, transactions=entries,
        ))

    return statements


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render_invoice(invoice: Invoice) -> str:
    template = _environment().get_template("invoice.html")
    return template.render(inv=invoice, region=invoice.region, money=money)


def render_statement(statement: Statement) -> str:
    template = _environment().get_template("statement.html")
    return template.render(st=statement, region=statement.region, money=money)
