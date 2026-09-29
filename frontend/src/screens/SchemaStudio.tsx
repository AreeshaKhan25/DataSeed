import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { api, type AiProposal, type Column, type Privacy } from "../lib/api";
import { rise, row } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconKey, IconLink, IconSearch, IconSpark } from "../components/Icons";
import { Banner, Button, Card, EmptyState, PageTitle, Pill } from "../components/ui";

const PRIVACY_MODES: Privacy[] = ["synthesize", "hash", "mask", "noise", "passthrough"];

const PRIVACY_HELP: Record<Privacy, string> = {
  synthesize: "Generate a fresh, realistic value",
  hash: "One-way hash, joins still work, the value does not",
  mask: "Partially redact, keeping the shape",
  noise: "Add calibrated noise (numeric only)",
  passthrough: "Keep the generated value as-is",
};

function PiiChip({ level }: { level?: Column["pii"] }) {
  if (level === "direct") return <Pill tone="rose">Direct PII</Pill>;
  if (level === "quasi") return <Pill tone="amber">Quasi PII</Pill>;
  return <span className="text-[12px] text-secondary font-medium">None</span>;
}

export function SchemaStudio() {
  const { schema, project, setSchema, go, run } = useStore();
  const [active, setActive] = useState(0);
  const [proposals, setProposals] = useState<AiProposal[] | null>(null);
  const [mode, setMode] = useState<string>("");
  const [thinking, setThinking] = useState(false);
  const [colSearch, setColSearch] = useState("");

  const tableCount = schema?.tables?.length ?? 0;
  const safeActive = Math.min(Math.max(0, active), Math.max(0, tableCount - 1));
  const table = schema?.tables?.[safeActive];

  const fkColumns = useMemo(() => {
    const set = new Set<string>();
    if (!schema?.foreign_keys || !table?.name) return set;
    schema.foreign_keys.forEach((fk) => {
      if (fk.child_table === table.name) set.add(fk.child_column);
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

  const handleSelectTable = (index: number) => {
    setActive(index);
    setProposals(null); // Reset proposals when table switches to prevent stale mismatch
  };

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
  const piiCount = (table.columns ?? []).filter((c) => c.pii === "direct").length;
  const totalColumns = (schema.tables ?? []).reduce((n, t) => n + (t.columns?.length ?? 0), 0);

  const filteredColumns = (table.columns ?? []).filter((c) =>
    c.name.toLowerCase().includes(colSearch.toLowerCase()) ||
    c.dtype.toLowerCase().includes(colSearch.toLowerCase()) ||
    c.semantic.toLowerCase().includes(colSearch.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle
          sub={`${schema.tables.length} tables · ${totalColumns} columns · ${schema.foreign_keys?.length ?? 0} relationships`}
        >
          Schema Studio
        </PageTitle>
        <div className="flex gap-2">
          <Button icon={<IconSpark size={15} />} loading={thinking} onClick={infer}>
            Infer types with AI
          </Button>
          <Button variant="primary" onClick={() => go("workspace")}>
            Synthesize dataset
          </Button>
        </div>
      </motion.div>

      {proposals && (
        <Banner
          tone="iris"
          icon={<IconSpark size={18} />}
          title={
            mode === "live"
              ? `AI reviewed ${proposals.length} columns and flagged ${proposals.filter((p) => p.pii === "direct").length} as direct PII`
              : `Heuristics classified ${proposals.length} columns (no API key set)`
          }
          body="Review the suggestions below, or accept them all to update column attributes."
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

      <div className="grid gap-5 lg:grid-cols-[240px_1fr]">
        {/* Table Selector List */}
        <motion.div variants={rise} className="min-w-0 space-y-3">
          <Card className="overflow-hidden p-2.5">
            <div className="px-2 py-1.5 text-[11px] font-bold text-secondary uppercase tracking-wider">
              Tables ({schema.tables.length})
            </div>
            <div className="space-y-1 mt-1">
              {schema.tables.map((t, i) => (
                <button
                  key={t.name}
                  type="button"
                  onClick={() => handleSelectTable(i)}
                  className={`relative flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-left transition-all duration-150 ${
                    i === safeActive
                      ? "bg-secondary-container text-primary font-semibold shadow-xs"
                      : "text-on-surface hover:bg-surface-container-low"
                  }`}
                >
                  <span className="truncate text-[13px]">{t.name}</span>
                  <span className="tnum shrink-0 text-[11px] font-medium text-secondary">
                    {(t.row_count ?? 0).toLocaleString()}
                  </span>
                </button>
              ))}
            </div>
          </Card>

          {piiCount > 0 && (
            <div className="rounded-2xl border border-rose/20 bg-rose-wash px-4 py-3">
              <div className="text-[12px] font-bold text-rose flex items-center gap-1.5">
                <span>{piiCount} Direct PII {piiCount === 1 ? "column" : "columns"}</span>
              </div>
              <div className="mt-1 text-[11.5px] leading-snug text-rose/85">
                Privacy-safe synthetic values will be generated from scratch.
              </div>
            </div>
          )}
        </motion.div>

        {/* Table Columns Matrix */}
        <motion.div variants={rise} className="min-w-0">
          <Card className="overflow-hidden p-0">
            {/* Table Header Bar */}
            <div className="flex flex-wrap items-center justify-between border-b border-outline-variant/30 bg-surface-container-low px-5 py-3.5 gap-3">
              <div className="flex items-center gap-2">
                <span className="font-sans text-[17px] font-bold text-on-surface">{table.name}</span>
                <span className="rounded-full bg-primary-fixed text-primary text-[11px] font-bold px-2.5 py-0.5">
                  {(table.row_count ?? 0).toLocaleString()} rows
                </span>
                {table.primary_key && (
                  <span className="flex items-center gap-1 text-[11px] font-semibold text-secondary">
                    <IconKey size={12} className="text-primary" /> PK: {table.primary_key}
                  </span>
                )}
              </div>
              <div className="relative w-56">
                <IconSearch size={14} className="absolute left-3 top-2.5 text-secondary" />
                <input
                  type="text"
                  value={colSearch}
                  onChange={(e) => setColSearch(e.target.value)}
                  placeholder="Filter columns..."
                  className="w-full pl-8 pr-3 py-1 bg-white border border-outline-variant/40 rounded-full text-[12px] placeholder:text-secondary/50 focus:outline-none focus:border-primary text-on-surface"
                />
              </div>
            </div>

            {/* Matrix Table */}
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-surface-container-lowest border-b border-outline-variant/30">
                    {["Column", "Type", "Semantic", "PII", "Privacy", "Nulls", "Sample"].map((h) => (
                      <th
                        key={h}
                        className="whitespace-nowrap px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-secondary"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredColumns.map((c, i) => {
                    const p = proposalFor(c.name);
                    const changed =
                      Boolean(p) && (p?.semantic !== c.semantic || p?.pii !== c.pii || p?.privacy !== c.privacy);
                    const isKey = c.name === table.primary_key;
                    const isFk = fkColumns.has(c.name);
                    return (
                      <motion.tr
                        key={c.name}
                        custom={i}
                        variants={row}
                        initial="hidden"
                        animate="show"
                        className={`border-b border-outline-variant/20 last:border-0 transition-colors ${
                          changed ? "bg-secondary-container/40" : "hover:bg-surface-container-low/50"
                        }`}
                      >
                        <td className="whitespace-nowrap px-4 py-3">
                          <span className="flex items-center gap-1.5 text-[13px] font-semibold text-on-surface font-sans">
                            {isKey && <IconKey size={14} className="text-primary" />}
                            {isFk && <IconLink size={14} className="text-teal" />}
                            {c.name}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 font-mono text-[12px] text-secondary">
                          {c.dtype}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-[12.5px] font-medium text-on-surface">
                          {p?.semantic ?? c.semantic}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <PiiChip level={p?.pii ?? c.pii} />
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <select
                            value={p?.privacy ?? c.privacy}
                            onChange={(e) => setPrivacy(c.name, e.target.value as Privacy)}
                            title={PRIVACY_HELP[p?.privacy ?? c.privacy]}
                            className="rounded-full border border-outline-variant/40 bg-white px-2.5 py-1 text-[11.5px] font-medium text-on-surface focus:border-primary focus:outline-none"
                          >
                            {PRIVACY_MODES.map((pm) => (
                              <option key={pm} value={pm}>
                                {pm}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-[12px] font-mono text-secondary">
                          {((c.null_rate ?? 0) * 100).toFixed(0)}%
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 font-mono text-[12px] text-secondary max-w-[180px] truncate">
                          {c.sample ?? "—"}
                        </td>
                      </motion.tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
