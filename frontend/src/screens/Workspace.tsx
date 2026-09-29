import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, trackJob, type EdgeCase, type Pii, type Row } from "../lib/api";
import { ease, rise, spring } from "../lib/motion";
import { useStore } from "../lib/store";
import { DataTable } from "../components/DataTable";
import { IconCheck, IconDice, IconSpark } from "../components/Icons";
import {
  Banner,
  Button,
  Card,
  EmptyState,
  Field,
  Meter,
  Modal,
  PageTitle,
  Pill,
  Slider,
  Toggle,
} from "../components/ui";

const PHASES = [
  "Reading schema",
  "Fitting distributions",
  "Generating tables",
  "Reconciling derived fields",
  "Validating integrity",
  "Building trust report",
];

export function Workspace() {
  const { schema, project, setReport, go, run, job, setJob } = useStore();
  const [tableIndex, setTableIndex] = useState(0);
  const [rows, setRows] = useState(10000);
  const [seed, setSeed] = useState(schema?.seed ?? 42);
  const [nullRate, setNullRate] = useState(0.02);
  const [outlierRate, setOutlierRate] = useState(0.01);
  const [preview, setPreview] = useState<Row[]>([]);
  const [piiMap, setPiiMap] = useState<Record<string, Pii>>({});
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [edges, setEdges] = useState<EdgeCase[]>([]);
  const [hasOutput, setHasOutput] = useState(false);

  // Pagination state: 50, 100, 500, 1000, Custom, or Full
  const [pageSize, setPageSize] = useState<number | "full">(50);
  const [page, setPage] = useState<number>(0);
  const [customSizeInput, setCustomSizeInput] = useState<string>("250");
  const [showCustomModal, setShowCustomModal] = useState<boolean>(false);

  const tableCount = schema?.tables?.length ?? 0;
  const safeTableIndex = Math.min(Math.max(0, tableIndex), Math.max(0, tableCount - 1));
  const table = schema?.tables?.[safeTableIndex];

  const totalTableRows = useMemo(() => {
    if (!table) return 10000;
    return (job?.result?.rows?.[table.name] ?? table.row_count ?? rows);
  }, [table, job, rows]);

  const effectiveLimit = useMemo(() => {
    if (pageSize === "full") return Math.min(totalTableRows, 1000);
    return pageSize;
  }, [pageSize, totalTableRows]);

  const totalPages = useMemo(() => {
    if (pageSize === "full") return 1;
    return Math.max(1, Math.ceil(totalTableRows / pageSize));
  }, [pageSize, totalTableRows]);

  const loadPreview = useCallback(async () => {
    if (!project || !table) return;
    setLoading(true);
    const limit = effectiveLimit;
    const offset = page * limit;

    if (hasOutput) {
      const res = await run(() => api.data(project.id, table.name, limit, offset));
      if (res) setPreview(res.rows);
    } else {
      const res = await run(() =>
        api.preview(project.id, {
          table: table.name,
          rows: limit,
          seed,
          null_rate: nullRate,
          outlier_rate: outlierRate,
        }),
      );
      if (res) {
        setPreview(res.rows);
        const map: Record<string, Pii> = {};
        res.columns.forEach((c) => (map[c.name] = c.pii));
        setPiiMap(map);
      }
    }
    setLoading(false);
  }, [project, table, seed, nullRate, outlierRate, hasOutput, page, effectiveLimit, run]);

  // Debounced preview refresh
  useEffect(() => {
    const t = setTimeout(() => void loadPreview(), 200);
    return () => clearTimeout(t);
  }, [loadPreview]);

  useEffect(() => {
    if (!project) return;
    void run(async () => {
      const res = await api.edgeCases(project.id);
      setEdges(res.edge_cases.slice(0, 6));
    });
  }, [project, run]);

  const columns = useMemo(
    () => (preview[0] ? Object.keys(preview[0]) : table?.columns.map((c) => c.name) ?? []),
    [preview, table],
  );

  if (!schema || !project || !table) {
    return (
      <EmptyState
        title="No project open"
        body="Open a project or load the demo to start generating."
        action={<Button variant="primary" onClick={() => go("projects")}>Go to projects</Button>}
      />
    );
  }

  const handleSelectTable = (index: number) => {
    setTableIndex(index);
    setPage(0);
  };

  const generate = async () => {
    setGenerating(true);
    setJob(null);
    const started = await run(() =>
      api.generate(project.id, {
        rows,
        seed,
        null_rate: nullRate,
        outlier_rate: outlierRate,
      }),
    );
    if (started) {
      const done = await run(() => trackJob(started.job.id, setJob));
      if (done) {
        setHasOutput(true);
        const report = await run(() => api.report(project.id));
        if (report) setReport(report);
        setPage(0);
        await loadPreview();
      }
    }
    setGenerating(false);
  };

  const pct = job?.percent ?? 0;

  return (
    <div className="space-y-6">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle sub={`${schema.name} · seed ${seed} · ${schema.tables.length} tables`}>
          Workspace & Data Synthesis
        </PageTitle>
        <div className="flex flex-wrap gap-1.5">
          {schema.tables.map((t, i) => (
            <Pill key={t.name} active={i === tableIndex} onClick={() => handleSelectTable(i)}>
              {t.name}
              <span className="tnum ml-1.5 opacity-75">
                {(job?.result?.rows?.[t.name] ?? t.row_count).toLocaleString()}
              </span>
            </Pill>
          ))}
        </div>
      </motion.div>

      <AnimatePresence>
        {job && job.status !== "done" && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={ease}
            className="overflow-hidden"
          >
            <Card className="p-6 border-l-4 border-l-primary">
              <div className="mb-3 flex items-baseline justify-between">
                <span className="font-sans text-[16px] font-bold text-on-surface">{job.phase}</span>
                <span className="tnum text-[13px] font-medium text-secondary">{job.message}</span>
              </div>
              <Meter value={pct} tone="navy" height={8} />
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {PHASES.map((p, i) => {
                  const reached = pct >= (i / PHASES.length) * 100;
                  const current = job.phase === p;
                  return (
                    <div key={p} className="flex items-center gap-2 text-[12.5px]">
                      <span
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${
                          reached ? "bg-grass text-white" : "bg-surface-container-high text-transparent"
                        }`}
                      >
                        <IconCheck size={10} />
                      </span>
                      <span className={current ? "font-bold text-primary" : "text-secondary"}>{p}</span>
                    </div>
                  );
                })}
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {job?.status === "done" && job.result.integrity && (
        <Banner
          tone={job.result.export_allowed ? "grass" : "amber"}
          title={
            job.result.export_allowed
              ? `Generated ${job.result.total_rows?.toLocaleString()} rows across ${Object.keys(job.result.rows ?? {}).length} tables, all integrity gates passed`
              : "Generated, but trust report requires inspection"
          }
          body={`${job.result.integrity.total_orphans} orphan keys · ${job.result.integrity.total_reconciliation_mismatches} reconciliation mismatches · seed ${job.result.seed}`}
          actions={
            <Button size="sm" variant="primary" onClick={() => go("trust")}>
              View Trust Report
            </Button>
          }
        />
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        {/* Left: Main Data Matrix Table with Pagination Bar */}
        <motion.div variants={rise} className="min-w-0">
          <Card className="overflow-hidden p-0">
            {/* Table Top Status Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/30 bg-surface-container-low px-5 py-3.5">
              <div className="flex items-center gap-2">
                <span className="font-sans text-[16px] font-bold text-on-surface">{table.name}</span>
                <span className="rounded-full bg-primary-fixed text-primary text-[11px] font-bold px-2.5 py-0.5">
                  {hasOutput ? "Generated Output" : "Live Preview"}
                </span>
              </div>
              <span className="tnum text-[12.5px] font-medium text-secondary">
                {(totalTableRows).toLocaleString()} total rows
              </span>
            </div>

            {/* Data Table */}
            <DataTable columns={columns} rows={preview} pii={piiMap} loading={loading} maxHeight={480} />

            {/* Pagination Controls Footer */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant/30 bg-surface-container-low px-5 py-3 text.xs select-none">
              {/* Row count range indicator */}
              <div className="flex items-center gap-1.5 text-secondary text-[12.5px]">
                <span>
                  Showing{" "}
                  <strong className="text-on-surface font-semibold">
                    {totalTableRows === 0
                      ? 0
                      : (page * (pageSize === "full" ? totalTableRows : pageSize) + 1).toLocaleString()}
                  </strong>{" "}
                  -{" "}
                  <strong className="text-on-surface font-semibold">
                    {Math.min(
                      totalTableRows,
                      (page + 1) * (pageSize === "full" ? totalTableRows : pageSize)
                    ).toLocaleString()}
                  </strong>{" "}
                  of <strong className="text-primary font-bold">{totalTableRows.toLocaleString()}</strong> rows
                </span>
              </div>

              {/* Page size selectors */}
              <div className="flex items-center gap-1.5">
                <span className="text-[12px] font-semibold text-secondary mr-1">Rows:</span>
                {[50, 100, 500, 1000].map((size) => (
                  <button
                    key={size}
                    type="button"
                    onClick={() => {
                      setPageSize(size);
                      setPage(0);
                    }}
                    className={`px-2.5 py-1 rounded-full text-[11.5px] font-bold transition-all ${
                      pageSize === size
                        ? "bg-primary text-on-primary shadow-xs"
                        : "bg-white border border-outline-variant/40 text-secondary hover:bg-surface-container-high"
                    }`}
                  >
                    {size}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setShowCustomModal(true)}
                  className={`px-2.5 py-1 rounded-full text-[11.5px] font-bold transition-all ${
                    typeof pageSize === "number" && ![50, 100, 500, 1000].includes(pageSize)
                      ? "bg-primary text-on-primary shadow-xs"
                      : "bg-white border border-outline-variant/40 text-secondary hover:bg-surface-container-high"
                  }`}
                >
                  {typeof pageSize === "number" && ![50, 100, 500, 1000].includes(pageSize)
                    ? `Custom (${pageSize})`
                    : "Custom"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPageSize("full");
                    setPage(0);
                  }}
                  className={`px-2.5 py-1 rounded-full text-[11.5px] font-bold transition-all ${
                    pageSize === "full"
                      ? "bg-primary text-on-primary shadow-xs"
                      : "bg-white border border-outline-variant/40 text-secondary hover:bg-surface-container-high"
                  }`}
                >
                  Full
                </button>
              </div>

              {/* Page Navigation */}
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  Previous
                </Button>
                <span className="text-[12px] font-semibold text-secondary px-1">
                  Page {page + 1} of {totalPages}
                </span>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Right: Synthesis Controls & Configuration */}
        <motion.div variants={rise} className="min-w-0 space-y-4">
          <Card className="p-5 space-y-4">
            <div className="label uppercase font-bold text-secondary text-[11px]">Output Configuration</div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Rows" type="number" value={rows} onChange={(v) => setRows(Number(v) || 1)} />
              <Field
                label="Seed"
                type="number"
                value={seed}
                onChange={(v) => setSeed(Number(v) || 0)}
                suffix={
                  <button
                    type="button"
                    aria-label="Randomise seed"
                    onClick={() => setSeed(Math.floor(Math.random() * 99999))}
                    className="rounded-full p-1.5 text-secondary hover:bg-surface-container-low transition-colors"
                  >
                    <IconDice size={16} />
                  </button>
                }
              />
            </div>
            <p className="text-[11.5px] leading-snug text-secondary">
              Determintic seed guarantees byte-identical reproducible output.
            </p>
          </Card>

          <Card className="space-y-4 p-5">
            <div className="label uppercase font-bold text-secondary text-[11px]">Quality Noise & Outliers</div>
            <Slider label="Null rate" value={nullRate} onChange={setNullRate} />
            <Slider label="Outlier rate" value={outlierRate} onChange={setOutlierRate} max={0.1} />
          </Card>

          <Card className="p-5">
            <div className="label mb-2.5 uppercase font-bold text-secondary text-[11px]">Privacy Protection</div>
            <div className="mb-3 space-y-1.5">
              {(["synthesize", "hash", "mask", "noise", "passthrough"] as const).map((mode) => {
                const n = (schema?.tables ?? [])
                  .flatMap((t) => t.columns ?? [])
                  .filter((c) => c?.privacy === mode).length;
                if (!n) return null;
                return (
                  <div key={mode} className="flex items-center justify-between text-[12.5px]">
                    <span className="text-secondary font-medium">{mode}</span>
                    <span className="tnum font-bold text-primary">{n}</span>
                  </div>
                );
              })}
            </div>
            <Button size="sm" className="mb-2 w-full" onClick={() => go("schema")}>
              Edit Column Privacy
            </Button>
            <Toggle
              checked
              locked
              label="Block exact matches with real rows"
              hint="Source values are kept as one-way fingerprints to prevent row collisions."
            />
          </Card>

          <Card className="p-5">
            <div className="mb-2.5 flex items-center gap-1.5">
              <IconSpark size={15} className="text-primary" />
              <span className="label uppercase font-bold text-secondary text-[11px]">Edge Cases</span>
            </div>
            <div className="space-y-2">
              {edges.map((e) => (
                <div key={e.name} className="rounded-xl bg-surface-container-low p-2.5">
                  <span className="block text-[12.5px] font-bold text-on-surface">{e.name}</span>
                  <span className="block text-[11.5px] leading-snug text-secondary mt-0.5">
                    {e.description}
                  </span>
                </div>
              ))}
              {edges.length === 0 && (
                <p className="text-[12px] text-secondary">Loading edge cases…</p>
              )}
            </div>
          </Card>

          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="space-y-2.5 pt-1"
          >
            <Button
              variant="primary"
              size="lg"
              className="w-full"
              loading={generating}
              icon={<IconSpark size={18} />}
              onClick={generate}
            >
              {generating ? "Synthesizing Data..." : "Synthesize Dataset"}
            </Button>
            <Button size="lg" className="w-full" disabled={!hasOutput} onClick={() => go("export")}>
              Proceed to Export
            </Button>
          </motion.div>
        </motion.div>
      </div>

      {/* Custom Page Size Modal */}
      <Modal
        open={showCustomModal}
        onClose={() => setShowCustomModal(false)}
        title="Custom Page Size"
        sub="Specify the exact number of rows to display per page (1 to 1,000)."
      >
        <div className="space-y-4 pt-2">
          <Field
            label="Rows Per Page"
            type="number"
            value={customSizeInput}
            onChange={setCustomSizeInput}
            placeholder="e.g. 250"
            min={1}
            max={1000}
          />
          <div className="flex justify-end gap-2 pt-3">
            <Button variant="secondary" onClick={() => setShowCustomModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                const val = Math.max(1, Math.min(1000, Number(customSizeInput) || 50));
                setPageSize(val);
                setPage(0);
                setShowCustomModal(false);
              }}
            >
              Apply Page Size
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
