import { motion } from "framer-motion";
import { useRef, useState } from "react";
import { api } from "../lib/api";
import { rise, spring } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconCheck, IconUpload } from "../components/Icons";
import { Button, Card, PageTitle } from "../components/ui";

const STEPS = ["Ingest", "Schema Studio", "Relationships", "Rules", "Synthesize", "Trust Report", "Export"];

export function Ingest() {
  const { go, openProject, loadDemo, refreshProjects, run } = useStore();
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = (list: FileList | null) => {
    if (!list) return;
    const csvs = Array.from(list).filter((f) => f.name.toLowerCase().endsWith(".csv"));
    setFiles(csvs);
    if (csvs.length && !name) setName(csvs[0].name.replace(/\.csv$/i, "").replace(/[_-]/g, " "));
  };

  const upload = async () => {
    if (!files.length) return;
    setBusy(true);
    const res = await run(() => api.ingest(files, name || "Untitled project"));
    if (res) {
      await openProject(res.project.id);
      await refreshProjects();
      go("schema");
    }
    setBusy(false);
  };

  return (
    <div className="mx-auto max-w-[800px] space-y-7">
      <motion.div variants={rise} className="text-center">
        <PageTitle sub="Synthesize realistic, privacy-safe tabular and relational data on demand. We analyze schema distributions without storing raw PII.">
          New Project Setup
        </PageTitle>
      </motion.div>

      {/* Drag & Drop File Upload Area */}
      <motion.div variants={rise}>
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            accept(e.dataTransfer.files);
          }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed px-8 py-14 text-center transition-all duration-200 bento-shadow ${
            dragging
              ? "border-primary bg-primary-fixed/50 scale-[1.01]"
              : "border-outline-variant/50 bg-white hover:border-primary/60 hover:bg-surface-container-low/40"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            multiple
            className="sr-only"
            onChange={(e) => accept(e.target.files)}
          />
          <motion.div
            animate={{ y: dragging ? -6 : 0, scale: dragging ? 1.08 : 1 }}
            transition={spring}
            className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-on-primary shadow-lg shadow-primary/25"
          >
            <IconUpload size={28} />
          </motion.div>
          <div className="font-sans text-[18px] font-bold text-on-surface">
            Drop CSV file(s) here, or browse
          </div>
          <div className="mt-1.5 text-[13.5px] text-secondary max-w-md">
            Upload single or multi-table CSVs. Column semantics, types, and foreign key relationships will be detected automatically.
          </div>
        </label>
      </motion.div>

      {/* Selected File List */}
      {files.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
          <Card className="p-6">
            <div className="mb-4 space-y-2">
              <div className="text-[12px] font-bold text-secondary uppercase tracking-wider">
                Ingesting Files ({files.length})
              </div>
              {files.map((f) => (
                <div
                  key={f.name}
                  className="flex items-center justify-between rounded-xl bg-surface-container-low px-4 py-2.5"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <IconCheck size={16} className="shrink-0 text-grass" />
                    <span className="truncate text-[13.5px] font-semibold text-on-surface">{f.name}</span>
                  </div>
                  <span className="tnum shrink-0 text-[12px] font-medium text-secondary">
                    {(f.size / 1024).toFixed(0)} KB
                  </span>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-end gap-3 pt-2">
              <label className="flex-1 min-w-[240px]">
                <div className="label mb-1.5 uppercase font-semibold text-[11px] text-secondary">
                  Project Title
                </div>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Untitled project"
                  className="h-10 w-full rounded-xl border border-outline-variant/40 bg-white px-3.5 text-[13.5px] outline-none focus:border-primary focus:ring-2 focus:ring-primary-fixed-dim/50"
                />
              </label>
              <Button variant="primary" size="lg" loading={busy} onClick={upload}>
                Analyze Schema
              </Button>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Demo Loader Card */}
      <motion.div variants={rise}>
        <Card className="p-6 border-l-4 border-l-primary">
          <div className="mb-2 font-sans text-[16px] font-bold text-on-surface">
            Quick Start: Load E-Commerce Demo Dataset
          </div>
          <p className="mb-4 text-[13.5px] leading-relaxed text-secondary">
            Instantly spin up a 3-table relational schema (customers, orders, order items) with full foreign keys, business rules, and pre-computed integrity gates.
          </p>
          <Button
            variant="secondary"
            onClick={async () => {
              await loadDemo();
              await refreshProjects();
              go("schema");
            }}
          >
            Load Demo Project
          </Button>
        </Card>
      </motion.div>

      {/* Workflow Step Indicators */}
      <motion.ol variants={rise} className="flex flex-wrap items-center justify-center gap-2 pt-2">
        {STEPS.map((s, i) => (
          <li key={s} className="flex items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-[11.5px] font-bold ${
                i === 0
                  ? "bg-primary text-on-primary"
                  : "bg-surface-container-low text-secondary border border-outline-variant/30"
              }`}
            >
              {s}
            </span>
            {i < STEPS.length - 1 && <span className="h-px w-3 bg-outline-variant/40" />}
          </li>
        ))}
      </motion.ol>
    </div>
  );
}
