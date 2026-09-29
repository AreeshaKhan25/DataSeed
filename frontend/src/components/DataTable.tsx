import { motion } from "framer-motion";
import { row } from "../lib/motion";
import type { Pii, Row } from "../lib/api";
import { Skeleton } from "./ui";

// Dense but readable: hairline row rules, no zebra striping, no vertical lines.
// Numbers are right-aligned with tabular figures so columns stay on axis while
// values stream in.

const STATUS_TONES: Record<string, string> = {
  shipped: "bg-grass-wash text-grass",
  delivered: "bg-grass-wash text-grass",
  paid: "bg-grass-wash text-grass",
  active: "bg-grass-wash text-grass",
  pending: "bg-amber-wash text-amber",
  processing: "bg-amber-wash text-amber",
  refunded: "bg-rose-wash text-rose",
  cancelled: "bg-rose-wash text-rose",
  failed: "bg-rose-wash text-rose",
};

const NUMERIC = /^-?[\d,]*\.?\d+$/;

function isNumeric(v: unknown): v is number {
  return typeof v === "number" || (typeof v === "string" && NUMERIC.test(v) && v.trim() !== "");
}

function Cell({ value, column }: { value: unknown; column: string }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-[12.5px] italic text-ink-faint">null</span>;
  }

  const text = String(value);
  const tone = STATUS_TONES[text.toLowerCase()];
  if (tone) {
    return (
      <span className={`inline-flex rounded-md px-2 py-[3px] text-[11.5px] font-semibold ${tone}`}>
        {text}
      </span>
    );
  }

  const lower = column.toLowerCase();
  const money = /total|amount|price|balance|revenue|cost|salary|fee/.test(lower);
  if (isNumeric(value)) {
    const n = Number(value);
    const shown = money
      ? n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : Number.isInteger(n)
        ? n.toLocaleString()
        : n.toLocaleString(undefined, { maximumFractionDigits: 2 });
    return (
      <span className={`tnum text-[13px] ${money ? "font-semibold text-navy" : "text-ink"}`}>
        {shown}
      </span>
    );
  }

  return (
    <span className="block max-w-[26ch] truncate text-[13px] text-ink" title={text}>
      {text}
    </span>
  );
}

export function DataTable({
  columns,
  rows,
  pii,
  loading,
  maxHeight = 460,
}: {
  columns: string[];
  rows: Row[];
  pii?: Record<string, Pii>;
  loading?: boolean;
  maxHeight?: number;
}) {
  if (loading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
    );
  }

  if (!rows.length) {
    return (
      <div className="px-5 py-14 text-center text-[13px] text-ink-mute">
        No rows yet. Generate a dataset to see output here.
      </div>
    );
  }

  const numericColumn = (c: string) =>
    rows.some((r) => isNumeric(r[c])) && !STATUS_TONES[String(rows[0]?.[c]).toLowerCase()];

  return (
    <div className="w-full max-w-full overflow-x-auto overflow-y-auto" style={{ maxHeight }}>
      <table className="w-full border-collapse">
        <thead className="sticky top-0 z-10 bg-canvas-raised">
          <tr>
            {columns.map((c) => (
              <th
                key={c}
                className={`whitespace-nowrap border-b border-line px-4 py-2.5 text-[11px] font-semibold
                            uppercase tracking-[0.05em] text-ink-mute
                            ${numericColumn(c) ? "text-right" : "text-left"}`}
              >
                <span className="inline-flex items-center gap-1.5">
                  {c}
                  {pii?.[c] === "direct" && (
                    <span className="rounded bg-rose-wash px-1 py-px text-[9px] font-bold text-rose">
                      PII
                    </span>
                  )}
                  {pii?.[c] === "quasi" && (
                    <span className="rounded bg-amber-wash px-1 py-px text-[9px] font-bold text-amber">
                      Q
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <motion.tr
              key={i}
              custom={i}
              variants={row}
              initial="hidden"
              animate="show"
              className="border-b border-line-soft last:border-0 hover:bg-canvas/70"
            >
              {columns.map((c) => (
                <td
                  key={c}
                  className={`whitespace-nowrap px-4 py-[9px] align-middle
                              ${numericColumn(c) ? "text-right" : "text-left"}`}
                >
                  <Cell value={r[c]} column={c} />
                </td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
