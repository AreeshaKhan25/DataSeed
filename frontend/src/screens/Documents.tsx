import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { api, type InvoiceDoc, type StatementDoc } from "../lib/api";
import { ease, rise } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconCheck, IconDownload, IconSpark } from "../components/Icons";
import {
  Banner,
  Button,
  Card,
  EmptyState,
  Field,
  Label,
  PageTitle,
  Spinner,
  Toggle,
} from "../components/ui";

type Kind = "invoice" | "statement";

const TEMPLATES: { kind: Kind; region: string; label: string; note: string }[] = [
  { kind: "invoice", region: "EU", label: "Invoice, EU", note: "VAT 20%" },
  { kind: "invoice", region: "UK", label: "Invoice, UK", note: "VAT 20%" },
  { kind: "invoice", region: "US", label: "Invoice, US", note: "Sales tax 8.75%" },
  { kind: "invoice", region: "IN", label: "Invoice, India", note: "GST 18%" },
  { kind: "statement", region: "UK", label: "Bank statement", note: "Running balance" },
];

const money = (v: number, currency: string) =>
  new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 2 }).format(v);

function InvoicePreview({ doc }: { doc: InvoiceDoc }) {
  return (
    <div className="mx-auto max-w-[520px] rounded-2xl border border-line bg-white p-8 shadow-lift">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-serif text-[24px] font-semibold text-navy">INVOICE</div>
          <div className="tnum mt-1 text-[12px] text-ink-mute">#{doc.number}</div>
        </div>
        <div className="text-right text-[11px] leading-relaxed text-ink-mute">
          Issued <span className="tnum text-ink">{doc.issued}</span>
          <br />
          Due <span className="tnum text-ink">{doc.due}</span>
        </div>
      </div>

      <div className="mt-7 flex gap-10">
        {[
          { label: "Billed to", name: doc.bill_to_name, addr: doc.bill_to_address },
          { label: "From", name: doc.from_name, addr: doc.from_address },
        ].map((party) => (
          <div key={party.label} className="flex-1">
            <div className="label uppercase">{party.label}</div>
            <div className="mt-1.5 text-[13px] font-semibold text-ink">{party.name}</div>
            <div className="mt-0.5 text-[11.5px] leading-relaxed text-ink-mute">
              {party.addr.map((l) => (
                <div key={l}>{l}</div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <table className="mt-7 w-full border-collapse">
        <thead>
          <tr>
            {["Item", "Qty", "Price", "Amount"].map((h, i) => (
              <th
                key={h}
                className={`border-b border-line pb-2 text-[10.5px] font-semibold uppercase tracking-[0.05em]
                            text-ink-mute ${i ? "text-right" : "text-left"}`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {doc.lines.map((l, i) => (
            <tr key={i} className="border-b border-line-soft">
              <td className="py-2.5 text-[12.5px] text-ink">{l.description}</td>
              <td className="tnum py-2.5 text-right text-[12px] text-ink">{l.quantity}</td>
              <td className="tnum py-2.5 text-right text-[12px] text-ink">
                {money(l.unit_price, doc.currency)}
              </td>
              <td className="tnum py-2.5 text-right text-[12px] text-ink">
                {money(l.amount, doc.currency)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="ml-auto mt-5 w-[220px] space-y-1.5">
        <div className="flex justify-between text-[12px] text-ink-mute">
          <span>Subtotal</span>
          <span className="tnum">{money(doc.subtotal, doc.currency)}</span>
        </div>
        <div className="flex justify-between text-[12px] text-ink-mute">
          <span>
            {doc.tax_label} {(doc.tax_rate * 100).toFixed(doc.tax_rate * 100 % 1 ? 2 : 0)}%
          </span>
          <span className="tnum">{money(doc.tax, doc.currency)}</span>
        </div>
        <div className="flex justify-between border-t-2 border-navy pt-2.5 font-serif text-[17px] font-semibold text-navy">
          <span>Total</span>
          <span className="tnum">{money(doc.total, doc.currency)}</span>
        </div>
      </div>

      {doc.reconciles && (
        <div className="mt-6 flex items-center gap-1.5 border-t border-line pt-4 text-[11px] text-grass">
          <IconCheck size={13} />
          Subtotal equals the sum of its line items; total equals subtotal plus tax.
        </div>
      )}
    </div>
  );
}

function StatementPreview({ doc }: { doc: StatementDoc }) {
  return (
    <div className="mx-auto max-w-[560px] rounded-2xl border border-line bg-white p-8 shadow-lift">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-serif text-[20px] font-semibold text-navy">Account statement</div>
          <div className="tnum mt-1 text-[12px] text-ink-mute">
            {doc.account_number} · {doc.holder}
          </div>
        </div>
        <div className="tnum text-right text-[11px] leading-relaxed text-ink-mute">
          {doc.period_start}
          <br />
          to {doc.period_end}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-4 gap-2.5">
        {[
          { k: "Opening", v: doc.opening_balance, c: "text-ink" },
          { k: "Paid in", v: doc.total_credits, c: "text-grass" },
          { k: "Paid out", v: doc.total_debits, c: "text-rose" },
          { k: "Closing", v: doc.closing_balance, c: "text-navy" },
        ].map((s) => (
          <div key={s.k} className="rounded-xl border border-line px-3 py-2.5">
            <div className="label uppercase">{s.k}</div>
            <div className={`tnum mt-1 font-serif text-[14px] font-semibold ${s.c}`}>
              {money(s.v, doc.currency)}
            </div>
          </div>
        ))}
      </div>

      <table className="mt-6 w-full border-collapse">
        <thead>
          <tr>
            {["Date", "Description", "Out", "In", "Balance"].map((h, i) => (
              <th
                key={h}
                className={`border-b border-line pb-2 text-[10.5px] font-semibold uppercase tracking-[0.05em]
                            text-ink-mute ${i > 1 ? "text-right" : "text-left"}`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {doc.transactions.slice(0, 14).map((t, i) => (
            <tr key={i} className="border-b border-line-soft">
              <td className="tnum py-2 text-[11.5px] text-ink-mute">{t.date}</td>
              <td className="py-2 text-[12px] text-ink">{t.description}</td>
              <td className="tnum py-2 text-right text-[11.5px] text-rose">
                {t.debit ? money(t.debit, doc.currency) : ""}
              </td>
              <td className="tnum py-2 text-right text-[11.5px] text-grass">
                {t.credit ? money(t.credit, doc.currency) : ""}
              </td>
              <td className="tnum py-2 text-right text-[12px] font-semibold text-ink">
                {money(t.balance, doc.currency)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {doc.reconciles && (
        <div className="mt-5 flex items-center gap-1.5 border-t border-line pt-4 text-[11px] text-grass">
          <IconCheck size={13} />
          Every running balance follows arithmetically from the one before it.
        </div>
      )}
    </div>
  );
}

export function Documents() {
  const { project, go, run } = useStore();
  const [template, setTemplate] = useState(0);
  const [count, setCount] = useState(20);
  const [query, setQuery] = useState("");
  const [docs, setDocs] = useState<(InvoiceDoc | StatementDoc)[]>([]);
  const [meta, setMeta] = useState<{
    all_reconciled: boolean;
    reconciled: number;
    from_generated_data: boolean;
    interpretation: string | null;
  } | null>(null);
  const [index, setIndex] = useState(0);
  const [busy, setBusy] = useState(false);

  const safeTemplate = Math.min(Math.max(0, template), TEMPLATES.length - 1);
  const t = TEMPLATES[safeTemplate] ?? TEMPLATES[0];

  const safeIndex = Math.min(Math.max(0, index), Math.max(0, (docs?.length ?? 1) - 1));
  const current = docs[safeIndex];

  const build = useCallback(async () => {
    if (!project) return;
    setBusy(true);
    const res = await run(() =>
      api.documents(project.id, {
        kind: t.kind,
        count,
        region: t.region,
        query: t.kind === "statement" && query ? query : undefined,
      }),
    );
    if (res) {
      setDocs(res.documents);
      setMeta(res);
      setIndex(0);
    }
    setBusy(false);
  }, [project, t, count, query, run]);

  useEffect(() => {
    void build();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project, template]);

  if (!project) {
    return (
      <EmptyState
        title="No project open"
        body="Open a project to render invoices and statements from its data."
        action={<Button variant="primary" onClick={() => go("projects")}>Go to projects</Button>}
      />
    );
  }

  return (
    <div className="space-y-5">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle sub="Documents are a rendering of the generated tables, the same data, laid out.">
          Documents
        </PageTitle>
        <div className="flex gap-2">
          <a href={api.documentBundleUrl(project.id, t.kind, t.region, count, t.kind === "statement" ? query : undefined)} download>
            <Button icon={<IconDownload size={15} />}>Download all</Button>
          </a>
          <a
            href={api.documentHtmlUrl(project.id, index, t.kind, t.region, count, t.kind === "statement" ? query : undefined)}
            target="_blank"
            rel="noreferrer"
          >
            <Button variant="primary">Open printable</Button>
          </a>
        </div>
      </motion.div>

      {meta && (
        <Banner
          tone={meta.all_reconciled ? "grass" : "rose"}
          title={
            meta.all_reconciled
              ? `All ${meta.reconciled} documents reconcile`
              : `${meta.reconciled} of ${docs.length} documents reconcile`
          }
          body={
            t.kind === "invoice"
              ? meta.from_generated_data
                ? "Line items come from the generated order_items table; totals are computed from them, not invented."
                : "Line items are generated standalone; totals are still computed from them."
              : "Running balances are computed in a single pass from the opening balance."
          }
        />
      )}

      <div className="grid gap-4 lg:grid-cols-[220px_1fr_290px]">
        <motion.div variants={rise}>
          <Card className="p-2">
            {TEMPLATES.map((tpl, i) => (
              <button
                key={tpl.label}
                type="button"
                onClick={() => setTemplate(i)}
                className={`relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors
                            ${i === template ? "bg-navy-wash" : "hover:bg-canvas"}`}
              >
                {i === template && (
                  <span className="absolute inset-y-1 left-0 w-[3px] rounded-full bg-navy" />
                )}
                <span className="flex h-[38px] w-[30px] shrink-0 flex-col justify-center gap-[3px] rounded-md border border-line bg-white px-1.5">
                  {[0, 1, 2, 3].map((n) => (
                    <span key={n} className="h-[2px] rounded-full bg-line-strong" />
                  ))}
                </span>
                <span className="min-w-0">
                  <span
                    className={`block truncate text-[12.5px] font-medium ${i === template ? "text-navy" : "text-ink"}`}
                  >
                    {tpl.label}
                  </span>
                  <span className="block text-[11px] text-ink-mute">{tpl.note}</span>
                </span>
              </button>
            ))}
          </Card>
        </motion.div>

        <motion.div variants={rise} className="min-w-0">
          {busy ? (
            <div className="flex h-72 items-center justify-center gap-2 text-[13px] text-ink-mute">
              <Spinner /> Rendering documents
            </div>
          ) : current ? (
            <AnimatePresence mode="wait">
              <motion.div
                key={index + t.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={ease}
              >
                {t.kind === "invoice" ? (
                  <InvoicePreview doc={current as InvoiceDoc} />
                ) : (
                  <StatementPreview doc={current as StatementDoc} />
                )}
              </motion.div>
            </AnimatePresence>
          ) : (
            <EmptyState title="No documents" body="Adjust the filter and generate again." />
          )}

          {docs.length > 1 && (
            <div className="mt-4 flex items-center justify-center gap-3">
              <Button size="sm" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>
                Previous
              </Button>
              <span className="tnum text-[12px] text-ink-mute">
                {index + 1} of {docs.length}
              </span>
              <Button
                size="sm"
                disabled={index >= docs.length - 1}
                onClick={() => setIndex((i) => i + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </motion.div>

        <motion.div variants={rise} className="space-y-3">
          <Card className="space-y-4 p-5">
            <div className="label uppercase">Settings</div>
            <Field label="Count" type="number" value={count} onChange={(v) => setCount(Number(v) || 1)} />
            <div>
              <Label>Region</Label>
              <div className="rounded-xl bg-canvas px-3 py-2.5 text-[12.5px] text-ink">
                {t.label} · {t.note}
              </div>
            </div>
            <Button variant="primary" className="w-full" loading={busy} onClick={build}>
              Generate {count} documents
            </Button>
          </Card>

          {t.kind === "statement" && (
            <Card className="p-5">
              <div className="mb-2 flex items-center gap-1.5">
                <IconSpark size={14} className="text-iris" />
                <span className="label uppercase">Ask in plain English</span>
              </div>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="last 90 days, balance over 500"
                rows={2}
                className="w-full resize-none rounded-xl border border-line bg-canvas-raised px-3 py-2.5
                           text-[12.5px] outline-none focus:border-navy-light"
              />
              <Button size="sm" className="mt-2 w-full" loading={busy} onClick={build}>
                Apply filter
              </Button>
              {meta?.interpretation && (
                <p className="mt-2.5 rounded-lg bg-iris-wash px-3 py-2 text-[11.5px] leading-snug text-iris">
                  {meta.interpretation}
                </p>
              )}
              <p className="mt-2 text-[11px] leading-snug text-ink-mute">
                The request is parsed into filters, then applied by code, the model plans, it never
                writes a balance.
              </p>
            </Card>
          )}

          <Card className="p-5">
            <div className="label mb-2 uppercase">Reconciliation</div>
            <Toggle
              checked
              locked
              label={t.kind === "invoice" ? "Totals computed from line items" : "Balances computed in one pass"}
              hint="Always enforced, and re-checked on every document before it renders."
            />
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
