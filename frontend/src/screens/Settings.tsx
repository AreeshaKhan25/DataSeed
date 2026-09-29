import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { rise } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconSpark } from "../components/Icons";
import { Card, Field, Label, PageTitle, Pill, Toggle } from "../components/ui";

export function Settings() {
  const { schema, aiMode, run } = useStore();
  const [limits, setLimits] = useState<Record<string, number>>({});
  const [ai, setAi] = useState<{ provider: string; reasoning_model: string; bulk_model: string; cached_responses: number } | null>(null);
  const [seed, setSeed] = useState(schema?.seed ?? 42);
  const [rows, setRows] = useState(10000);

  useEffect(() => {
    void run(async () => {
      const [health, status] = await Promise.all([api.health(), api.aiStatus()]);
      setLimits(health.limits);
      setAi(status);
    });
  }, [run]);

  return (
    <div className="mx-auto max-w-[820px] space-y-5">
      <motion.div variants={rise}>
        <PageTitle sub="Defaults for new generations, and what the platform is currently wired to.">
          Settings
        </PageTitle>
      </motion.div>

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="label mb-3 uppercase">Generation defaults</div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Default rows" type="number" value={rows} onChange={(v) => setRows(Number(v) || 1)} />
            <Field label="Default seed" type="number" value={seed} onChange={(v) => setSeed(Number(v) || 0)} />
          </div>
          <div className="mt-4">
            <Label>Engine</Label>
            <div className="flex gap-1.5">
              <Pill active>Gaussian copula</Pill>
              <Pill>CTGAN (not installed)</Pill>
            </div>
            <p className="mt-2 text-[11.5px] leading-snug text-ink-mute">
              The copula is deterministic, needs no GPU, and cannot fail to converge. It is the
              default for exactly those reasons.
            </p>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="mb-3 flex items-center gap-2">
            <IconSpark size={15} className="text-iris" />
            <span className="label uppercase">AI layer</span>
            <span
              className={`ml-auto rounded-lg border px-2 py-0.5 text-[11px] font-semibold
                          ${aiMode === "live" ? "border-iris/20 bg-iris-wash text-iris" : "border-line bg-canvas-sunken text-ink-mute"}`}
            >
              {aiMode === "live" ? "Live" : "Heuristics"}
            </span>
          </div>
          <dl className="space-y-2 text-[12.5px]">
            {[
              ["Provider", ai?.provider ?? "—"],
              ["Reasoning model", ai?.reasoning_model ?? "—"],
              ["Bulk model", ai?.bulk_model ?? "—"],
              ["Cached responses", String(ai?.cached_responses ?? 0)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <dt className="text-ink-mute">{k}</dt>
                <dd className="tnum font-medium text-ink">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 rounded-xl bg-canvas px-3.5 py-2.5 text-[11.5px] leading-relaxed text-ink-mute">
            {aiMode === "live"
              ? "Set. Every response is still validated against a schema before it reaches the pipeline, and falls back to heuristics on any failure."
              : "No usable AI credential, so the platform is running on deterministic heuristics. Every feature still works — the AI layer only ever adds polish, never load-bearing behaviour. Set ANTHROPIC_API_KEY or MISTRAL_API_KEY to switch it live."}
          </p>
        </Card>
      </motion.div>

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="label mb-1 uppercase">Privacy defaults</div>
          <Toggle checked label="Block exact matches with real rows" hint="Source values are kept as one-way fingerprints so a collision can be rejected without retaining real data." />
          <Toggle checked label="Regenerate direct PII from scratch" hint="Names, emails and addresses are never resampled from the source." />
          <Toggle checked locked label="Require a passing trust report before export" hint="Always enforced." />
        </Card>
      </motion.div>

      <motion.div variants={rise}>
        <Card className="p-5">
          <div className="label mb-3 uppercase">Limits</div>
          <dl className="space-y-2 text-[12.5px]">
            {Object.entries(limits).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <dt className="text-ink-mute">{k.replace(/_/g, " ")}</dt>
                <dd className="tnum font-medium text-ink">{v.toLocaleString()}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-[11.5px] leading-snug text-ink-mute">
            Every loop in the pipeline is bounded. Preview is capped so a slider can never queue a
            long job, and repair attempts are capped so constraint solving cannot hang.
          </p>
        </Card>
      </motion.div>
    </div>
  );
}
