import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { api, type AiProposal, type Column, type Privacy } from "../lib/api";
import { rise, row } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconKey, IconLink, IconSpark } from "../components/Icons";
import { Banner, Button, Card, EmptyState, PageTitle, Pill } from "../components/ui";

const PRIVACY_MODES: Privacy[] = ["synthesize", "hash", "mask", "noise", "passthrough"];

const PRIVACY_HELP: Record<Privacy, string> = {
  synthesize: "Generate a fresh, realistic value",
  hash: "One-way hash — joins still work, the value does not",
  mask: "Partially redact, keeping the shape",
  noise: "Add calibrated noise (numeric only)",
  passthrough: "Keep the generated value as-is",
};

function PiiChip({ level }: { level: Column["pii"] }) {
  if (level === "direct") return <Pill tone="rose">Direct</Pill>;
  if (level === "quasi") return <Pill tone="amber">Quasi</Pill>;
  return <span className="text-[12px] text-ink-faint">—</span>;
}

export function SchemaStudio() {
  const { schema, project, setSchema, go, run } = useStore();
  const [active, setActive] = useState(0);
  const [proposals, setProposals] = useState<AiProposal[] | null>(null);
  const [mode, setMode] = useState<string>("");
  const [thinking, setThinking] = useState(false);

  const table = schema?.tables[active];

  const fkColumns = useMemo(() => {
    const set = new Set<string>();
    schema?.foreign_keys.forEach((fk) => {
      if (fk.child_table === table?.name) set.add(fk.child_column);
    });
    return set;
  }, [schema, table]);

  if (!schema || !project || !table) {
    return (
      <EmptyState
        title="No project open"
        body="Open a project or load the demo to inspect its schema."
        action={<Button variant="primary" onClick={() => go("projects")}>Go to projects</Button>}
      />
    );
  }

  const infer = async () => {
    setThinking(true);
    const res = await run(() => api.inferTypes(project.id, table.name));
    if (res) {
      setProposals(res.proposals);
      setMode(res.mode);
    }
    setThinking(false);
  };

  const acceptAll = async () => {
    if (!proposals) return;
    const res = await run(() => api.applyProposals(project.id, table.name, proposals));
    if (res) {
      setSchema(res.schema);
      setProposals(null);
    }
  };

  const setPrivacy = async (column: string, privacy: Privacy) => {
    const res = await run(() => api.applyProposals(project.id, table.name, [{ column, privacy }]));
    if (res) setSchema(res.schema);
  };

  const proposalFor = (name: string) => proposals?.find((p) => p.column === name);
  const piiCount = table.columns.filter((c) => c.pii === "direct").length;

  return (
    <div className="space-y-5">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle
          sub={`${schema.tables.length} tables · ${schema.tables.reduce((n, t) => n + t.columns.length, 0)} columns · ${schema.foreign_keys.length} relationships`}
        >
          Schema
        </PageTitle>
        <div className="flex gap-2">
          <Button icon={<IconSpark size={15} />} loading={thinking} onClick={infer}>
            Infer types
          </Button>
          <Button variant="primary" onClick={() => go("workspace")}>
            Generate
          </Button>
        </div>
      </motion.div>

      {proposals && (
        <Banner
          tone="iris"
          icon={<IconSpark size={17} />}
          title={
            mode === "live"
              ? `AI reviewed ${proposals.length} columns and flagged ${proposals.filter((p) => p.pii === "direct").length} as direct PII`
              : `Heuristics classified ${proposals.length} columns — no API key set, so no model was called`
          }
          body="Nothing has changed yet. Review the suggestions below, or accept them all."
          actions={
            <>
              <Button size="sm" onClick={() => setProposals(null)}>
                Dismiss
              </Button>
              <Button size="sm" variant="primary" onClick={acceptAll}>
                Accept all
              </Button>
            </>
          }
        />
      )}

      <div className="grid gap-4 lg:grid-cols-[210px_1fr]">
        <motion.div variants={rise} className="min-w-0">
          <Card className="overflow-hidden p-2">
            {schema.tables.map((t, i) => (
              <button
                key={t.name}
                type="button"
                onClick={() => setActive(i)}
                className={`relative flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition-colors
                            ${i === active ? "bg-navy-wash" : "hover:bg-canvas"}`}
              >
                {i === active && (
                  <motion.span
                    layoutId="table-active"
                    className="absolute inset-y-1 left-0 w-[3px] rounded-full bg-navy"
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
                <span
                  className={`truncate text-[13px] font-medium ${i === active ? "text-navy" : "text-ink"}`}
                >
                  {t.name}
                </span>
                <span className="tnum shrink-0 text-[11px] text-ink-mute">
                  {t.row_count.toLocaleString()}
                </span>
              </button>
            ))}
          </Card>

          {piiCount > 0 && (
            <div className="mt-3 rounded-2xl border border-rose/18 bg-rose-wash px-3.5 py-3">
              <div className="text-[12px] font-semibold text-rose">
                {piiCount} direct PII {piiCount === 1 ? "column" : "columns"}
              </div>
              <div className="mt-1 text-[11.5px] leading-snug text-rose/85">
                These are regenerated from scratch, never resampled from your data.
              </div>
            </div>
          )}
        </motion.div>

        <motion.div variants={rise} className="min-w-0">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-canvas/60">
                    {["Column", "Type", "Semantic", "PII", "Privacy", "Nulls", "Sample"].map((h) => (
                      <th
                        key={h}
                        className="whitespace-nowrap border-b border-line px-4 py-2.5 text-left text-[11px]
                                   font-semibold uppercase tracking-[0.05em] text-ink-mute"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.columns.map((c, i) => {
                    const p = proposalFor(c.name);
                    const changed =
                      p && (p.semantic !== c.semantic || p.pii !== c.pii || p.privacy !== c.privacy);
                    const isKey = c.name === table.primary_key;
                    const isFk = fkColumns.has(c.name);
                    return (
                      <motion.tr
                        key={c.name}
                        custom={i}
                        variants={row}
                        initial="hidden"
                        animate="show"
                        className={`border-b border-line-soft last:border-0 transition-colors
                                    ${changed ? "bg-iris-wash/50" : "hover:bg-canvas/60"}`}
                      >
                        <td className="whitespace-nowrap px-4 py-3">
                          <span className="flex items-center gap-1.5 text-[13px] font-medium text-ink">
                            {isKey && <IconKey size={13} className="text-navy" />}
                            {isFk && <IconLink size={13} className="text-teal" />}
                            {c.name}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[12.5px] text-ink-mute">{c.dtype}</td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1.5 text-[12.5px] text-ink">
                            {changed ? (
                              <>
                                <span className="text-ink-faint line-through">{c.semantic}</span>
                                <span className="font-semibold text-iris">{p!.semantic}</span>
                                <IconSpark size={12} className="text-iris" />
                              </>
                            ) : (
                              <>
                                {c.semantic}
                                {c.ai_inferred && <IconSpark size={12} className="text-iris" />}
                              </>
                            )}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <PiiChip level={changed ? p!.pii : c.pii} />
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={c.privacy}
                            onChange={(e) => void setPrivacy(c.name, e.target.value as Privacy)}
                            title={PRIVACY_HELP[c.privacy]}
                            disabled={isKey || isFk}
                            className="rounded-lg border border-line bg-canvas-raised px-2 py-1 text-[12px]
                                       text-ink outline-none focus:border-navy-light disabled:opacity-45"
                          >
                            {PRIVACY_MODES.map((m) => (
                              <option key={m} value={m}>
                                {m}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="tnum px-4 py-3 text-[12.5px] text-ink-mute">
                          {(c.null_rate * 100).toFixed(1)}%
                        </td>
                        <td className="max-w-[18ch] truncate px-4 py-3 text-[12.5px] text-ink-mute">
                          {c.sample ?? "—"}
                        </td>
                      </motion.tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          {table.derived.length > 0 && (
            <div className="mt-3 rounded-2xl border border-grass/18 bg-grass-wash px-4 py-3">
              <div className="text-[12.5px] font-semibold text-grass">
                {table.derived.length} computed {table.derived.length === 1 ? "field" : "fields"}
              </div>
              <div className="mt-1 space-y-0.5 text-[11.5px] text-grass/85">
                {table.derived.map((d) => (
                  <div key={d.column}>
                    <span className="font-semibold">{d.column}</span> = {d.agg.toUpperCase()}(
                    {d.expr ?? "rows"}) over {d.child_table} — computed after generation, never invented
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
