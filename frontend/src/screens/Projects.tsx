import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { IconArrow, IconSearch } from "../components/Icons";
import { AnimatedNumber, Button, Card, EmptyState, Meter, PageTitle, Pill } from "../components/ui";
import { rise } from "../lib/motion";
import { useStore } from "../lib/store";
import type { ProjectSummary } from "../lib/api";

const STAT_CARDS = [
  { key: "projects", label: "Projects", tone: "from-navy to-navy-deep" },
  { key: "rows", label: "Rows generated", tone: "from-teal to-[#0b5c72]" },
  { key: "utility", label: "Avg utility", tone: "from-iris to-[#4c1d95]" },
  { key: "exports", label: "Validated", tone: "from-amber to-[#8a4b00]" },
] as const;

/** A card that tilts toward the cursor. Cheap depth cue, no library needed. */
function TiltCard({
  children,
  className = "",
  gradient,
}: {
  children: React.ReactNode;
  className?: string;
  gradient: string;
}) {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  return (
    <motion.div
      variants={rise}
      onMouseMove={(e) => {
        const box = e.currentTarget.getBoundingClientRect();
        setTilt({
          x: ((e.clientY - box.top - box.height / 2) / (box.height / 2)) * -5,
          y: ((e.clientX - box.left - box.width / 2) / (box.width / 2)) * 5,
        });
      }}
      onMouseLeave={() => setTilt({ x: 0, y: 0 })}
      animate={{ rotateX: tilt.x, rotateY: tilt.y }}
      transition={{ type: "spring", stiffness: 260, damping: 22 }}
      style={{ transformPerspective: 900 }}
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br p-4 text-white shadow-card ${gradient} ${className}`}
    >
      <div className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-white/12 blur-2xl" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/12 to-black/10" />
      <div className="relative">{children}</div>
    </motion.div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  const tone = value === null ? "navy" : value >= 90 ? "grass" : value >= 70 ? "amber" : "rose";
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-ink-mute">
          {label}
        </span>
        <span className="tnum text-[11.5px] font-semibold text-ink">
          {value === null ? " ": Math.round(value)}
        </span>
      </div>
      <Meter value={value ?? 0} tone={tone as "grass"} height={4} />
    </div>
  );
}

function ProjectCard({ p, onOpen }: { p: ProjectSummary; onOpen: () => void }) {
  const kinds = [
    { label: "Tabular", tone: "navy" as const, show: p.tables.length >= 1 },
    { label: "Relational", tone: "teal" as const, show: p.foreign_keys > 0 },
    { label: "Documents", tone: "iris" as const, show: p.has_output },
  ].filter((k) => k.show);

  const totalRows = (p.tables ?? []).reduce((n, t) => n + (t.generated_rows || t.source_rows || 0), 0);

  return (
    <Card interactive className="flex flex-col p-5" onClick={onOpen}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate font-serif text-[16.5px] font-semibold text-ink">{p.name}</h3>
          <p className="tnum mt-1 text-[11.5px] text-ink-mute">
            {p.tables.length} {p.tables.length === 1 ? "table" : "tables"} ·{" "}
            {totalRows.toLocaleString()} rows · seed {p.seed}
          </p>
        </div>
        <IconArrow size={16} className="mt-1 shrink-0 text-ink-faint" />
      </div>

      <div className="mb-4 flex flex-wrap gap-1.5">
        {kinds.map((k) => (
          <Pill key={k.label} tone={k.tone}>
            {k.label}
          </Pill>
        ))}
      </div>

      {p.scores ? (
        <div className="mt-auto grid grid-cols-2 gap-x-4 gap-y-2.5">
          <ScoreBar label="Integrity" value={p.scores.integrity} />
          <ScoreBar label="Fidelity" value={p.scores.fidelity} />
          <ScoreBar label="Utility" value={p.scores.utility} />
          <ScoreBar label="Privacy" value={p.scores.privacy} />
        </div>
      ) : (
        <div className="mt-auto rounded-xl border border-dashed border-line bg-canvas/60 px-3 py-3 text-center text-[11.5px] text-ink-mute">
          Not generated yet
        </div>
      )}
    </Card>
  );
}

export function Projects() {
  const { projects, refreshProjects, openProject, loadDemo, go, run } = useStore();
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  const filtered = projects.filter((p) => p.name.toLowerCase().includes(query.toLowerCase()));

  const withReport = projects.filter((p) => p.scores?.utility != null);
  const avgUtility = withReport.length
    ? withReport.reduce((n, p) => n + (p.scores?.utility ?? 0), 0) / withReport.length
    : 0;
  const totalRows = (projects ?? []).reduce(
    (n, p) => n + (p.tables ?? []).reduce((m, t) => m + (t.generated_rows || t.source_rows || 0), 0),
    0,
  );

  const stats: Record<string, { value: number; decimals?: number; suffix?: string }> = {
    projects: { value: projects.length },
    rows: { value: totalRows / 1000, decimals: 1, suffix: "k" },
    utility: { value: avgUtility, suffix: "%" },
    exports: { value: projects.filter((p) => p.has_report).length },
  };

  return (
    <div className="space-y-6">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle sub="Every dataset you have generated, with the evidence that it is usable.">
          Projects
        </PageTitle>
        <div className="flex items-center gap-2">
          <div className="flex h-10 items-center gap-2 rounded-xl border border-line bg-canvas-raised px-3 focus-within:border-navy-light">
            <IconSearch size={15} className="text-ink-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search projects"
              className="w-44 bg-transparent text-[13px] outline-none placeholder:text-ink-faint"
            />
          </div>
          <Button
            variant="primary"
            loading={creating}
            onClick={async () => {
              setCreating(true);
              await run(async () => {
                await loadDemo();
                await refreshProjects();
              });
              setCreating(false);
            }}
          >
            Load demo
          </Button>
          <Button onClick={() => go("ingest")}>New project</Button>
        </div>
      </motion.div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {STAT_CARDS.map((s) => {
          const stat = stats[s.key];
          return (
            <TiltCard key={s.key} gradient={s.tone}>
              <div className="text-[11px] font-semibold uppercase tracking-[0.06em] opacity-80">
                {s.label}
              </div>
              <div className="mt-2 font-serif text-[27px] font-semibold leading-none">
                <AnimatedNumber value={stat.value} decimals={stat.decimals ?? 0} />
                {stat.suffix}
              </div>
            </TiltCard>
          );
        })}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={query ? "No projects match that search" : "No projects yet"}
          body={
            query
              ? "Try a different search term, or clear the box to see everything."
              : "Load the demo dataset to see the full pipeline, or bring your own CSV."
          }
          action={
            <div className="flex gap-2">
              <Button variant="primary" onClick={() => void loadDemo()}>
                Load demo
              </Button>
              <Button onClick={() => go("ingest")}>Upload a CSV</Button>
            </div>
          }
        />
      ) : (
        <motion.div variants={rise} className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((p) => (
            <ProjectCard
              key={p.id}
              p={p}
              onOpen={async () => {
                await openProject(p.id);
                go("schema");
              }}
            />
          ))}
        </motion.div>
      )}
    </div>
  );
}
