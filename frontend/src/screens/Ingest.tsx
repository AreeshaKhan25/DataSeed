import { motion } from "framer-motion";
import { useRef, useState } from "react";
import { api } from "../lib/api";
import { rise, spring } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconCheck, IconUpload } from "../components/Icons";
import { Button, Card, PageTitle } from "../components/ui";

const STEPS = ["Ingest", "Schema", "Relationships", "Generate", "Validate", "Export"];

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
    <div className="mx-auto max-w-[760px] space-y-7">
      <motion.div variants={rise} className="text-center">
        <PageTitle sub="We learn the shape of your data — the distributions, the keys, the relationships — and never keep a real record.">
          Bring your schema
        </PageTitle>
      </motion.div>

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
          className={`flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed
                      px-8 py-14 text-center transition-colors
                      ${dragging ? "border-navy bg-navy-wash" : "border-line-strong bg-canvas-raised hover:border-navy-light"}`}
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
            animate={{ y: dragging ? -5 : 0, scale: dragging ? 1.06 : 1 }}
            transition={spring}
            className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-navy text-white shadow-card"
          >
            <IconUpload size={24} />
          </motion.div>
          <div className="font-serif text-[17px] font-semibold text-ink">
            Drop a CSV, or several
          </div>
          <div className="mt-1.5 text-[13px] text-ink-mute">
            Each file becomes one table. Relationships between them are detected automatically.
          </div>
        </label>
      </motion.div>

      {files.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
          <Card className="p-5">
            <div className="mb-4 space-y-1.5">
              {files.map((f) => (
                <div
                  key={f.name}
                  className="flex items-center justify-between rounded-xl bg-canvas px-3 py-2"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <IconCheck size={15} className="shrink-0 text-grass" />
                    <span className="truncate text-[13px] font-medium text-ink">{f.name}</span>
                  </div>
                  <span className="tnum shrink-0 text-[11.5px] text-ink-mute">
                    {(f.size / 1024).toFixed(0)} KB
                  </span>
                </div>
              ))}
            </div>

            <div className="flex items-end gap-3">
              <label className="flex-1">
                <div className="label mb-1.5 uppercase">Project name</div>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Untitled project"
                  className="h-10 w-full rounded-xl border border-line bg-canvas-raised px-3 text-[13.5px]
                             outline-none focus:border-navy-light"
                />
              </label>
              <Button variant="primary" loading={busy} onClick={upload}>
                Analyse schema
              </Button>
            </div>
          </Card>
        </motion.div>
      )}

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="mb-3 font-serif text-[15px] font-semibold text-ink">
            Or start from the demo
          </div>
          <p className="mb-4 text-[13px] leading-relaxed text-ink-mute">
            A three-table retail schema — customers, orders and order items — with real foreign keys
            and order totals that genuinely reconcile with their line items. It exercises every part
            of the pipeline.
          </p>
          <Button
            onClick={async () => {
              await loadDemo();
              await refreshProjects();
              go("schema");
            }}
          >
            Load the demo project
          </Button>
        </Card>
      </motion.div>

      <motion.ol variants={rise} className="flex flex-wrap items-center justify-center gap-2">
        {STEPS.map((s, i) => (
          <li key={s} className="flex items-center gap-2">
            <span
              className={`rounded-lg px-2.5 py-1 text-[11.5px] font-semibold
                          ${i === 0 ? "bg-navy text-white" : "bg-canvas-sunken text-ink-mute"}`}
            >
              {s}
            </span>
            {i < STEPS.length - 1 && <span className="h-px w-4 bg-line-strong" />}
          </li>
        ))}
      </motion.ol>
    </div>
  );
}
