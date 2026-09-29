import { motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { api, type Rule, type RuleResult } from "../lib/api";
import { rise, row } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconCheck, IconClose, IconSpark } from "../components/Icons";
import {
  Banner,
  Button,
  Card,
  EmptyState,
  PageTitle,
  Pill,
  SectionTitle,
} from "../components/ui";

const KIND_TONE: Record<string, "navy" | "teal" | "iris" | "amber" | "grass"> = {
  range: "navy",
  comparison: "amber",
  enum: "teal",
  not_null: "grass",
  computed: "iris",
  conditional: "iris",
  unique: "navy",
  regex: "teal",
};

const KIND_HELP: Record<string, string> = {
  range: "Keeps a number inside bounds. Repaired by clamping.",
  comparison: "Orders one column against another. Repaired by mirroring the gap.",
  enum: "Restricts a column to known values. Repaired by resampling.",
  not_null: "Requires a value. Repaired from the column's own distribution.",
  computed: "Derives a column from others. Repaired by recomputing.",
  conditional: "Applies only when another column takes a given value.",
  unique: "Forbids duplicates. Repaired by redrawing from unused values.",
  regex: "Requires a pattern. Cannot be repaired, so violating rows are dropped.",
};

export function Rules() {
  const { project, go, run } = useStore();
  const [rules, setRules] = useState<Rule[]>([]);
  const [results, setResults] = useState<Record<string, RuleResult[]>>({});
  const [busy, setBusy] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [aiNote, setAiNote] = useState("");
  const [filter, setFilter] = useState<string>("all");

  const load = useCallback(async () => {
    if (!project) return;
    const res = await run(() => api.rules(project.id));
    if (res) {
      setRules(res.rules);
      setResults(res.results);
    }
  }, [project, run]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!project) {
    return (
      <EmptyState
        title="No project open"
        body="Open a project to see the rules its data must satisfy."
        action={<Button variant="primary" onClick={() => go("projects")}>Go to projects</Button>}
      />
    );
  }

  const tables = Array.from(new Set(rules.map((r) => r.table)));
  const shown = filter === "all" ? rules : rules.filter((r) => r.table === filter);

  const fired = Object.entries(results).flatMap(([table, list]) =>
    list.filter((r) => r.violations_before > 0).map((r) => ({ ...r, table })),
  );
  const totalFound = fired.reduce((n, r) => n + r.violations_before, 0);
  const totalRepaired = fired.reduce((n, r) => n + r.repaired, 0);
  const totalDropped = fired.reduce((n, r) => n + r.dropped, 0);

  const toggle = async (rule: Rule) => {
    const res = await run(() => api.toggleRule(project.id, rule.id, !rule.enabled));
    if (res) setRules((rs) => rs.map((r) => (r.id === rule.id ? res.rule : r)));
  };

  const remove = async (rule: Rule) => {
    const res = await run(() => api.deleteRule(project.id, rule.id));
    if (res) setRules((rs) => rs.filter((r) => r.id !== rule.id));
  };

  return (
    <div className="space-y-5">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle sub="What makes a row valid — the domain logic a distribution cannot express.">
          Business rules
        </PageTitle>
        <div className="flex gap-2">
          <Button
            icon={<IconSpark size={15} />}
            loading={thinking}
            onClick={async () => {
              setThinking(true);
              const res = await run(() => api.aiRules(project.id));
              if (res) setAiNote(res.note);
              setThinking(false);
            }}
          >
            Propose rules
          </Button>
          <Button
            loading={busy}
            onClick={async () => {
              setBusy(true);
              await run(() => api.inferRules(project.id));
              await load();
              setBusy(false);
            }}
          >
            Re-read from data
          </Button>
          <Button variant="primary" onClick={() => go("workspace")}>
            Generate
          </Button>
        </div>
      </motion.div>

      {aiNote && <Banner tone="iris" icon={<IconSpark size={17} />} title={aiNote} />}

      {fired.length > 0 && (
        <Banner
          tone={totalDropped > 0 ? "amber" : "grass"}
          title={`${totalFound.toLocaleString()} violations caught in the last run — ${totalRepaired.toLocaleString()} repaired${
            totalDropped ? `, ${totalDropped} dropped` : ", none dropped"
          }`}
          body="Statistical fitting produces rows that break domain logic. These rules catch them before the data leaves the platform."
        />
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <motion.div variants={rise}>
          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center gap-1.5 border-b border-line px-4 py-3">
              <Pill active={filter === "all"} onClick={() => setFilter("all")}>
                All
                <span className="ml-1 opacity-60">{rules.length}</span>
              </Pill>
              {tables.map((t) => (
                <Pill key={t} active={filter === t} onClick={() => setFilter(t)}>
                  {t}
                  <span className="ml-1 opacity-60">
                    {rules.filter((r) => r.table === t).length}
                  </span>
                </Pill>
              ))}
            </div>

            {shown.length === 0 ? (
              <div className="px-5 py-14 text-center text-[13px] text-ink-mute">
                No rules yet. Use “Re-read from data” to learn them from your sample.
              </div>
            ) : (
              <div className="max-h-[560px] overflow-auto">
                {shown.map((rule, i) => {
                  const outcome = (results[rule.table] ?? []).find((r) => r.id === rule.id);
                  return (
                    <motion.div
                      key={rule.id}
                      custom={i}
                      variants={row}
                      initial="hidden"
                      animate="show"
                      className={`flex items-start gap-3 border-b border-line-soft px-4 py-3 last:border-0
                                  ${rule.enabled ? "" : "opacity-45"}`}
                    >
                      <button
                        type="button"
                        onClick={() => void toggle(rule)}
                        aria-label={rule.enabled ? "Disable rule" : "Enable rule"}
                        className={`mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-md border
                                    transition-colors ${
                                      rule.enabled
                                        ? "border-navy bg-navy text-white"
                                        : "border-line-strong bg-canvas-raised"
                                    }`}
                      >
                        {rule.enabled && <IconCheck size={11} />}
                      </button>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[13px] font-medium text-ink">{rule.label}</span>
                          <Pill tone={KIND_TONE[rule.kind] ?? "navy"}>{rule.kind}</Pill>
                          {rule.source !== "inferred" && (
                            <Pill tone="iris">{rule.source === "ai" ? "AI" : "yours"}</Pill>
                          )}
                        </div>
                        <div className="mt-0.5 text-[11.5px] text-ink-mute">
                          {rule.table}
                          {rule.column ? `.${rule.column}` : ""} — {KIND_HELP[rule.kind] ?? ""}
                        </div>
                        {outcome && outcome.violations_before > 0 && (
                          <div className="mt-1.5 inline-flex items-center gap-1.5 rounded-lg bg-grass-wash px-2 py-1 text-[11px] font-medium text-grass">
                            <IconCheck size={11} />
                            {outcome.violations_before.toLocaleString()} caught,{" "}
                            {outcome.repaired.toLocaleString()} {outcome.note || "repaired"}
                          </div>
                        )}
                      </div>

                      {rule.source !== "inferred" && (
                        <button
                          type="button"
                          onClick={() => void remove(rule)}
                          aria-label="Delete rule"
                          className="shrink-0 rounded-lg p-1.5 text-ink-faint transition-colors hover:bg-rose-wash hover:text-rose"
                        >
                          <IconClose size={14} />
                        </button>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            )}
          </Card>
        </motion.div>

        <motion.div variants={rise} className="space-y-3">
          <Card className="p-5">
            <SectionTitle>How enforcement works</SectionTitle>
            <ol className="space-y-2.5 text-[12px] leading-relaxed text-ink-mute">
              <li>
                <strong className="text-ink">1. Repair.</strong> Fix deterministically where the
                fix is unambiguous — clamp a range, recompute a total, reorder two dates.
              </li>
              <li>
                <strong className="text-ink">2. Reject.</strong> Drop only what cannot be repaired,
                and report the count.
              </li>
            </ol>
            <p className="mt-3 rounded-xl bg-canvas px-3.5 py-2.5 text-[11.5px] leading-relaxed text-ink-mute">
              Nothing loops. Pure rejection sampling is how these engines hang when a rule is
              rarely satisfied.
            </p>
          </Card>

          <Card className="p-5">
            <SectionTitle>Where rules come from</SectionTitle>
            <dl className="space-y-2.5 text-[12px]">
              <div>
                <dt className="font-medium text-ink">Read from your sample</dt>
                <dd className="text-ink-mute">
                  Only rules the data demonstrates without exception. A rule your real data already
                  breaks is not a rule.
                </dd>
              </div>
              <div>
                <dt className="font-medium text-ink">Proposed by AI</dt>
                <dd className="text-ink-mute">
                  Domain logic the sample cannot show — proposals only, never applied automatically.
                </dd>
              </div>
              <div>
                <dt className="font-medium text-ink">Written by you</dt>
                <dd className="text-ink-mute">
                  Added through the API. Yours always win over an inferred rule.
                </dd>
              </div>
            </dl>
          </Card>

          <Card className="p-5">
            <SectionTitle>Counts</SectionTitle>
            <dl className="space-y-1.5 text-[12.5px]">
              {[
                ["Active", rules.filter((r) => r.enabled).length],
                ["Disabled", rules.filter((r) => !r.enabled).length],
                ["From your data", rules.filter((r) => r.source === "inferred").length],
                ["Fired last run", fired.length],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between">
                  <dt className="text-ink-mute">{k}</dt>
                  <dd className="tnum font-semibold text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
