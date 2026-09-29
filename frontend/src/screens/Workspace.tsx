import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, trackJob, type EdgeCase, type Pii, type Row } from "../lib/api";
import { ease, rise, spring } from "../lib/motion";
import { useStore } from "../lib/store";
import { DataTable } from "../components/DataTable";
import { IconCheck, IconDice, IconSpark } from "../components/Icons";
import {
  AnimatedNumber,
  Banner,
  Button,
  Card,
  EmptyState,
  Field,
  Meter,
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

  const table = schema?.tables[tableIndex];

  const loadPreview = useCallback(async () => {
    if (!project || !table) return;
    setLoading(true);
    // Before a generation exists we sample live; afterwards we page the real
    // output. The two endpoints return different shapes, so branch explicitly
    // rather than union them.
    if (hasOutput) {
      const res = await run(() => api.data(project.id, table.name, 40));
      if (res) setPreview(res.rows);
    } else {
      const res = await run(() =>
        api.preview(project.id, {
          table: table.name,
          rows: 40,
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
  }, [project, table, seed, nullRate, outlierRate, hasOutput, run]);

  // Debounced so dragging a slider does not fire a request per frame.
  useEffect(() => {
    const t = setTimeout(() => void loadPreview(), 220);
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
        await loadPreview();
      }
    }
    setGenerating(false);
  };

  const generated = job?.result?.rows?.[table.name];
  const target = generated ?? rows;
  const pct = job?.percent ?? 0;

  return (
    <div className="space-y-5">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle sub={`${schema.name} · seed ${seed} · ${schema.tables.length} tables`}>
          Workspace
        </PageTitle>
        <div className="flex flex-wrap gap-1.5">
          {schema.tables.map((t, i) => (
            <Pill key={t.name} active={i === tableIndex} onClick={() => setTableIndex(i)}>
              {t.name}
              <span className="tnum ml-1 opacity-60">
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
            <Card className="p-5">
              <div className="mb-3 flex items-baseline justify-between">
                <span className="font-serif text-[15px] font-semibold text-ink">{job.phase}</span>
                <span className="tnum text-[12.5px] text-ink-mute">{job.message}</span>
              </div>
              <Meter value={pct} tone="navy" height={7} />
              <div className="mt-4 grid gap-1.5 sm:grid-cols-3">
                {PHASES.map((p, i) => {
                  const reached = pct >= (i / PHASES.length) * 100;
                  const current = job.phase === p;
                  return (
                    <div key={p} className="flex items-center gap-2 text-[12px]">
                      <span
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full
                                    ${reached ? "bg-grass text-white" : "bg-canvas-sunken text-transparent"}`}
                      >
                        <IconCheck size={9} />
                      </span>
                      <span className={current ? "font-semibold text-ink" : "text-ink-mute"}>{p}</span>
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
              ? `Generated ${job.result.total_rows?.toLocaleString()} rows across ${Object.keys(job.result.rows ?? {}).length} tables — all gates passed`
              : "Generated, but the trust report did not pass every gate"
          }
          body={`${job.result.integrity.total_orphans} orphan keys · ${job.result.integrity.total_reconciliation_mismatches} reconciliation mismatches · seed ${job.result.seed}`}
          actions={
            <Button size="sm" variant="primary" onClick={() => go("trust")}>
              View trust report
            </Button>
          }
        />
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_330px]">
        <motion.div variants={rise} className="min-w-0">
          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5">
              <span className="text-[12.5px] font-medium text-ink">
                {table.name}
                <span className="ml-2 text-ink-mute">
                  {hasOutput ? "generated output" : "live preview"}
                </span>
              </span>
              <span className="tnum text-[11.5px] text-ink-mute">
                showing {preview.length} of {target.toLocaleString()}
              </span>
            </div>

            <DataTable columns={columns} rows={preview} pii={piiMap} loading={loading} />

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line bg-canvas/50 px-4 py-2.5">
              <div className="flex flex-wrap items-center gap-3">
                <span className="tnum text-[11.5px] text-ink-mute">
                  <AnimatedNumber value={generated ?? 0} /> of {rows.toLocaleString()} rows
                </span>
                <div className="w-40 max-w-full">
                  <Meter value={generated ? 100 : pct} tone="navy" height={4} />
                </div>
              </div>
              <span className="tnum text-[11.5px] text-ink-mute">seed {seed}</span>
            </div>
          </Card>
        </motion.div>

        <motion.div variants={rise} className="min-w-0 space-y-3">
          <Card className="p-5">
            <div className="label mb-3 uppercase">Output</div>
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
                    className="rounded-lg p-1.5 text-ink-mute transition-colors hover:bg-canvas-sunken"
                  >
                    <IconDice size={15} />
                  </button>
                }
              />
            </div>
            <p className="mt-2.5 text-[11.5px] leading-snug text-ink-mute">
              The same seed always produces byte-identical output.
            </p>
          </Card>

          <Card className="space-y-4 p-5">
            <div className="label uppercase">Quality</div>
            <Slider label="Null rate" value={nullRate} onChange={setNullRate} />
            <Slider label="Outlier rate" value={outlierRate} onChange={setOutlierRate} max={0.1} />
          </Card>

          {/* Every control here reflects something the engine actually does.
              A mode selector with no backend behind it is worse than no
              selector: it promises behaviour that never runs. */}
          <Card className="p-5">
            <div className="label mb-2.5 uppercase">Privacy</div>
            <div className="mb-3 space-y-1.5">
              {(["synthesize", "hash", "mask", "noise", "passthrough"] as const).map((mode) => {
                const n = schema.tables
                  .flatMap((t) => t.columns)
                  .filter((c) => c.privacy === mode).length;
                if (!n) return null;
                return (
                  <div key={mode} className="flex items-center justify-between text-[12px]">
                    <span className="text-ink-mute">{mode}</span>
                    <span className="tnum font-semibold text-ink">{n}</span>
                  </div>
                );
              })}
            </div>
            <Button size="sm" className="mb-1 w-full" onClick={() => go("schema")}>
              Edit per column
            </Button>
            <Toggle
              checked
              locked
              label="Block exact matches with real rows"
              hint="Always enforced. Source values are kept only as one-way fingerprints, so a collision is rejected without any real data being stored."
            />
          </Card>

          <Card className="p-5">
            <div className="mb-2.5 flex items-center gap-1.5">
              <IconSpark size={14} className="text-iris" />
              <span className="label uppercase">Edge cases</span>
            </div>
            <p className="mb-2 text-[11px] leading-snug text-ink-mute">
              Proposed for this schema. The outlier and null rates above inject them; per-case
              selection is not wired to the engine yet.
            </p>
            <div className="space-y-1.5">
              {edges.map((e) => (
                <div key={e.name} className="rounded-lg px-1 py-1">
                  <span className="block text-[12.5px] font-medium text-ink">{e.name}</span>
                  <span className="block text-[11px] leading-snug text-ink-mute">
                    {e.description}
                  </span>
                </div>
              ))}
              {edges.length === 0 && (
                <p className="text-[12px] text-ink-mute">Loading proposals…</p>
              )}
            </div>
          </Card>

          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="space-y-2"
          >
            <Button
              variant="primary"
              className="w-full"
              loading={generating}
              icon={<IconSpark size={16} />}
              onClick={generate}
            >
              {generating ? "Generating" : "Generate"}
            </Button>
            <Button className="w-full" disabled={!hasOutput} onClick={() => go("export")}>
              Export
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
