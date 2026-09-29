import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { rise } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconAlert, IconCheck, IconDownload, IconLock } from "../components/Icons";
import { Banner, Button, Card, EmptyState, PageTitle, Toggle } from "../components/ui";

const DESCRIPTIONS: Record<string, string> = {
  csv: "One CSV per table, zipped with the schema and trust report",
  json: "Every table plus the full trust report in one document",
  sql: "Postgres dump: DDL, data, then foreign keys, restores in any order",
  parquet: "Columnar files, zipped. Smallest on disk",
  excel: "One workbook, one sheet per table",
};

export function ExportScreen() {
  const { project, report, go, run } = useStore();
  const [formats, setFormats] = useState<{ id: string; label: string }[]>([]);
  const [chosen, setChosen] = useState("csv");
  const [includeSchema, setIncludeSchema] = useState(true);
  const [includeReport, setIncludeReport] = useState(true);

  useEffect(() => {
    void run(async () => {
      const res = await api.formats();
      setFormats(res.formats);
    });
  }, [run]);

  if (!project) {
    return (
      <EmptyState
        title="No project open"
        body="Open a project to export its generated data."
        action={<Button variant="primary" onClick={() => go("projects")}>Go to projects</Button>}
      />
    );
  }

  if (!project.has_output) {
    return (
      <EmptyState
        title="Nothing to export yet"
        body="Generate a dataset first. Export is deliberately unavailable until there is validated output."
        action={<Button variant="primary" onClick={() => go("workspace")}>Generate a dataset</Button>}
      />
    );
  }

  const allowed = report?.export_allowed ?? true;
  const failed = Object.entries(report?.gates ?? {}).filter(([, ok]) => !ok);
  const totalRows = project.tables.reduce((n, t) => n + t.generated_rows, 0);

  const url =
    api.exportUrl(project.id, chosen) +
    `&include_schema=${includeSchema}&include_report=${includeReport}`;

  return (
    <div className="mx-auto max-w-[840px] space-y-5">
      <motion.div variants={rise}>
        <PageTitle
          sub={`${project.name} · ${project.tables.length} tables · ${totalRows.toLocaleString()} rows · seed ${project.seed}`}
        >
          Export
        </PageTitle>
      </motion.div>

      <Banner
        tone={allowed ? "grass" : "rose"}
        icon={allowed ? <IconCheck size={17} /> : <IconLock size={17} />}
        title={
          allowed
            ? "All integrity gates passed"
            : `Export blocked: ${failed.map(([k]) => k.replace(/_/g, " ")).join(", ")}`
        }
        body={
          allowed
            ? "This dataset met every threshold, so it is cleared to leave the platform."
            : "The platform refuses to export data that fails its own checks. Fix the schema or regenerate."
        }
        actions={
          !allowed && (
            <Button size="sm" onClick={() => go("trust")}>
              See what failed
            </Button>
          )
        }
      />

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="label mb-3 uppercase">Format</div>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {formats.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setChosen(f.id)}
                className={`rounded-2xl border px-4 py-3.5 text-left transition-colors
                            ${
                              chosen === f.id
                                ? "border-navy bg-navy-wash"
                                : "border-line bg-canvas-raised hover:border-line-strong"
                            }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-[13.5px] font-semibold ${chosen === f.id ? "text-navy" : "text-ink"}`}
                  >
                    {f.label}
                  </span>
                  {chosen === f.id && (
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-navy text-white">
                      <IconCheck size={10} />
                    </span>
                  )}
                </div>
                <div className="mt-1 text-[11.5px] leading-snug text-ink-mute">
                  {DESCRIPTIONS[f.id] ?? ""}
                </div>
              </button>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="label mb-1 uppercase">Include</div>
          <Toggle
            checked={includeSchema}
            onChange={setIncludeSchema}
            label="Schema definition"
            hint="The full Schema IR, so the run can be reproduced exactly."
          />
          <Toggle
            checked={includeReport}
            onChange={setIncludeReport}
            label="Trust report"
            hint="The evidence that this dataset is usable, shipped alongside it."
          />
        </Card>
      </motion.div>

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="label mb-2.5 uppercase">Reproduce this exact dataset</div>
          <pre className="overflow-x-auto rounded-xl bg-ink px-4 py-3.5 text-[11.5px] leading-relaxed text-white/90">
{`curl -X POST http://127.0.0.1:8000/api/projects/${project.id}/generate \
  -H "Content-Type: application/json" \
  -d '{"rows": ${totalRows || 10000}, "seed": ${project.seed}}'`}
          </pre>
          <p className="mt-2 text-[11.5px] text-ink-mute">
            The same seed always produces byte-identical output.
          </p>
        </Card>
      </motion.div>

      <motion.div variants={rise} className="flex justify-end gap-2">
        <Button onClick={() => go("trust")}>Back to report</Button>
        {allowed ? (
          <a href={url} download>
            <Button variant="primary" icon={<IconDownload size={16} />}>
              Download
            </Button>
          </a>
        ) : (
          <Button variant="primary" disabled icon={<IconAlert size={16} />}>
            Download blocked
          </Button>
        )}
      </motion.div>
    </div>
  );
}
