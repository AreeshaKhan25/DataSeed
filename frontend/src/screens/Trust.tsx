import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { rise, row, spring } from "../lib/motion";
import { useStore } from "../lib/store";
import { IconAlert, IconCheck, IconShield } from "../components/Icons";
import {
  AnimatedNumber,
  Banner,
  Button,
  Card,
  EmptyState,
  Meter,
  PageTitle,
  SectionTitle,
} from "../components/ui";

type Tone = "grass" | "amber" | "rose";
const tone = (v: number): Tone => (v >= 90 ? "grass" : v >= 70 ? "amber" : "rose");

function ScoreCard({
  label,
  value,
  caption,
  delay,
}: {
  label: string;
  value: number;
  caption: string;
  delay: number;
}) {
  const t = tone(value);
  const colors = { grass: "#1e8e3e", amber: "#b06000", rose: "#c5221f" };
  const size = 76;
  const stroke = 6;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;

  return (
    <motion.div variants={rise}>
      <Card className="flex items-center gap-4 p-5">
        <div className="relative shrink-0" style={{ width: size, height: size }}>
          <svg width={size} height={size} className="-rotate-90">
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#eef1f6" strokeWidth={stroke} />
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={colors[t]}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={c}
              initial={{ strokeDashoffset: c }}
              animate={{ strokeDashoffset: c * (1 - Math.max(0, Math.min(100, value)) / 100) }}
              transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1], delay }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <AnimatedNumber value={value} className="font-serif text-[22px] font-semibold text-ink" />
          </div>
        </div>
        <div className="min-w-0">
          <div className="font-serif text-[15px] font-semibold text-ink">{label}</div>
          <div className="mt-1 text-[11.5px] leading-snug text-ink-mute">{caption}</div>
        </div>
      </Card>
    </motion.div>
  );
}

function UtilityChart({ trtr, tstr, metric }: { trtr: number; tstr: number; metric: string }) {
  const bars = [
    { label: "Trained on real", value: trtr, fill: "#b6c2d2" },
    { label: "Trained on synthetic", value: tstr, fill: "#1f4e79" },
  ];
  const max = Math.max(trtr, tstr, 1);

  return (
    <div>
      <div className="flex h-44 items-end gap-8 border-b border-line px-6 pb-0">
        {bars.map((b, i) => (
          <div key={b.label} className="flex flex-1 flex-col items-center justify-end">
            <span className="tnum mb-2 text-[13px] font-semibold text-ink">{b.value.toFixed(3)}</span>
            <motion.div
              className="w-full max-w-[86px] rounded-t-lg"
              style={{ background: b.fill }}
              initial={{ height: 0 }}
              animate={{ height: `${(b.value / max) * 130}px` }}
              transition={{ ...spring, delay: 0.25 + i * 0.12 }}
            />
          </div>
        ))}
      </div>
      <div className="flex gap-8 px-6 pt-2.5">
        {bars.map((b) => (
          <div key={b.label} className="flex flex-1 items-center justify-center gap-1.5">
            <span className="h-2 w-2 rounded-sm" style={{ background: b.fill }} />
            <span className="text-[11.5px] text-ink-mute">{b.label}</span>
          </div>
        ))}
      </div>
      <div className="mt-1 text-center text-[11px] text-ink-faint">measured in {metric}</div>
    </div>
  );
}

function PrivacyRow({
  label,
  value,
  meter,
  good,
  note,
}: {
  label: string;
  value: string;
  meter: number;
  good: boolean;
  note?: string;
}) {
  return (
    <div className="py-2.5">
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="text-[12.5px] text-ink">{label}</span>
        <span className={`tnum text-[12.5px] font-semibold ${good ? "text-grass" : "text-amber"}`}>
          {value}
        </span>
      </div>
      <Meter value={meter} tone={good ? "grass" : "amber"} height={5} />
      {note && <div className="mt-1 text-[11px] text-ink-mute">{note}</div>}
    </div>
  );
}

export function Trust() {
  const { report, project, setReport, go, run } = useStore();
  const [busy, setBusy] = useState(false);

  // Fetch the report ourselves if the store does not have one yet. Landing here
  // while a generation is still finishing would otherwise show an empty state
  // that only clears by navigating away and back.
  useEffect(() => {
    if (report || !project?.has_output) return;
    let cancelled = false;
    void (async () => {
      try {
        const fetched = await api.report(project.id);
        if (!cancelled) setReport(fetched);
      } catch {
        /* no report yet is a normal state; the empty state explains it */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [report, project, setReport]);

  if (!project) {
    return (
      <EmptyState
        title="No project open"
        body="Open a project to see its validation results."
        action={<Button variant="primary" onClick={() => go("projects")}>Go to projects</Button>}
      />
    );
  }

  if (!report || !report.available) {
    return (
      <EmptyState
        title="No trust report yet"
        body={
          report?.reason ??
          "Generate a dataset and the platform will measure its fidelity, utility and privacy against your real data."
        }
        action={
          <div className="flex gap-2">
            <Button variant="primary" onClick={() => go("workspace")}>
              Generate a dataset
            </Button>
            <Button
              loading={busy}
              onClick={async () => {
                setBusy(true);
                const r = await run(() => api.validate(project.id));
                if (r) setReport(r);
                setBusy(false);
              }}
            >
              Validate now
            </Button>
          </div>
        }
      />
    );
  }

  const { integrity, fidelity, utility, privacy, detection, gates } = report;
  const failed = Object.entries(gates).filter(([, ok]) => !ok);

  return (
    <div className="space-y-5">
      <motion.div variants={rise} className="flex flex-wrap items-end justify-between gap-4">
        <PageTitle
          sub={`${report.rows_evaluated.toLocaleString()} training rows · ${report.holdout_rows.toLocaleString()} held-out real rows the generator never saw${
            report.conditioned_on ? ` · conditioned on ${report.conditioned_on}` : ""
          }`}
        >
          Trust report
        </PageTitle>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="label uppercase">Overall</div>
            <AnimatedNumber
              value={report.overall}
              className="font-serif text-[26px] font-semibold leading-none text-ink"
            />
          </div>
          <Button
            variant="primary"
            disabled={!report.export_allowed}
            onClick={() => go("export")}
          >
            Export
          </Button>
        </div>
      </motion.div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ScoreCard
          label="Integrity"
          value={integrity.score}
          caption={`${integrity.total_orphans} orphan keys · ${integrity.total_reconciliation_mismatches} mismatches`}
          delay={0.1}
        />
        <ScoreCard
          label="Fidelity"
          value={fidelity.score}
          caption="Distributions and correlations match the source"
          delay={0.2}
        />
        <ScoreCard
          label="Utility"
          value={utility.available ? utility.score : 0}
          caption={utility.available ? "Trained on synthetic, tested on real" : "Not measurable here"}
          delay={0.3}
        />
        <ScoreCard
          label="Privacy"
          value={privacy.score}
          caption="No record traces back to a real person"
          delay={0.4}
        />
      </div>

      <Banner
        tone={report.export_allowed ? "grass" : "rose"}
        icon={report.export_allowed ? <IconShield size={18} /> : <IconAlert size={18} />}
        title={
          report.export_allowed
            ? "All gates passed — this dataset is cleared for export"
            : `Export blocked: ${failed.map(([k]) => k.replace(/_/g, " ")).join(", ")}`
        }
        body={
          report.export_allowed
            ? "Integrity, privacy and fidelity all met their thresholds."
            : "The platform will not export a dataset that fails its own checks."
        }
        actions={
          <Button size="sm" variant="primary" disabled={!report.export_allowed} onClick={() => go("export")}>
            Export dataset
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <motion.div variants={rise}>
          <Card className="p-5">
            <SectionTitle hint={utility.metric}>Downstream utility — TSTR</SectionTitle>
            {utility.available ? (
              <>
                <UtilityChart
                  trtr={utility.trtr ?? 0}
                  tstr={utility.tstr ?? 0}
                  metric={utility.metric ?? "AUC"}
                />
                <div className="mt-4 space-y-1.5 rounded-xl bg-canvas px-4 py-3">
                  {[
                    ["TRTR — trained on real", utility.trtr],
                    ["TSTR — trained on synthetic", utility.tstr],
                    ["Ratio", utility.ratio],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="flex justify-between text-[12.5px]">
                      <span className="text-ink-mute">{label}</span>
                      <span className="tnum font-semibold text-ink">
                        {typeof value === "number" ? value.toFixed(3) : "—"}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[12px] leading-relaxed text-ink-mute">
                  {utility.explanation}
                </p>
                {utility.independent_check && (
                  <div className="mt-3 rounded-xl border border-line bg-canvas px-4 py-3">
                    <div className="label mb-1.5 uppercase">Independent check</div>
                    <p className="text-[11.5px] leading-relaxed text-ink-mute">
                      The generator was conditioned on{" "}
                      <strong className="text-ink">{report.conditioned_on}</strong>, which is also
                      the strongest target — so that score partly reflects the modelling choice.
                      On{" "}
                      <strong className="text-ink">{utility.independent_check.target}</strong>, a
                      column it was <em>not</em> conditioned on, utility is{" "}
                      <strong className="text-ink">{utility.independent_check.score}</strong>{" "}
                      (TRTR {utility.independent_check.trtr.toFixed(3)} vs TSTR{" "}
                      {utility.independent_check.tstr.toFixed(3)}).
                    </p>
                  </div>
                )}
                {!!utility.excluded_as_leaked?.length && (
                  <p className="mt-2 rounded-lg bg-amber-wash px-3 py-2 text-[11.5px] leading-snug text-amber">
                    Excluded {utility.excluded_as_leaked.join(", ")} as a target — another column
                    determines it outright, so the comparison would prove nothing.
                  </p>
                )}
              </>
            ) : (
              <p className="text-[12.5px] leading-relaxed text-ink-mute">{utility.reason}</p>
            )}
          </Card>
        </motion.div>

        <motion.div variants={rise} className="space-y-4">
          <Card className="p-5">
            <SectionTitle>Privacy</SectionTitle>
            <div className="divide-y divide-line-soft">
              <PrivacyRow
                label="Exact matches with real rows"
                value={String(privacy.exact_matches)}
                meter={privacy.exact_matches === 0 ? 100 : 20}
                good={privacy.exact_matches === 0}
              />
              <PrivacyRow
                label="Distance to closest record"
                value={privacy.dcr?.toFixed(4) ?? "—"}
                meter={
                  privacy.dcr && privacy.dcr_baseline
                    ? Math.min(100, (privacy.dcr / privacy.dcr_baseline) * 70)
                    : 0
                }
                good={!!privacy.dcr && !!privacy.dcr_baseline && privacy.dcr >= privacy.dcr_baseline}
                note={`Real-to-real baseline ${privacy.dcr_baseline?.toFixed(4) ?? "—"} — synthetic rows should sit no closer.`}
              />
              <PrivacyRow
                label="Membership inference"
                value={privacy.membership_auc?.toFixed(3) ?? "—"}
                meter={
                  privacy.membership_auc
                    ? Math.max(0, 100 - Math.abs(privacy.membership_auc - 0.5) * 300)
                    : 0
                }
                good={!!privacy.membership_auc && Math.abs(privacy.membership_auc - 0.5) < 0.1}
                note="0.50 means an attacker cannot tell which records were in the training set."
              />
            </div>
          </Card>

          {detection.available && (
            <Card className="p-5">
              <SectionTitle>Detection</SectionTitle>
              <div className="flex items-baseline gap-3">
                <AnimatedNumber
                  value={detection.auc ?? 0}
                  decimals={2}
                  className="font-serif text-[40px] font-semibold leading-none text-navy"
                />
                <span className="text-[12.5px] text-ink-mute">AUC</span>
              </div>
              <p className="mt-2.5 text-[12px] leading-relaxed text-ink-mute">
                A classifier trained to tell real rows from synthetic ones scores{" "}
                {detection.auc?.toFixed(2)}. <strong className="text-ink">0.50 means it cannot.</strong>
              </p>
            </Card>
          )}
        </motion.div>
      </div>

      <motion.div variants={rise}>
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4">
            <SectionTitle hint={fidelity.note || undefined}>Fidelity by column</SectionTitle>
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-canvas/50">
                {["Column", "Metric", "Distance", "Match"].map((h) => (
                  <th
                    key={h}
                    className="border-b border-line px-5 py-2.5 text-left text-[11px] font-semibold
                               uppercase tracking-[0.05em] text-ink-mute"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fidelity.columns.map((c, i) => (
                <motion.tr
                  key={c.column}
                  custom={i}
                  variants={row}
                  initial="hidden"
                  animate="show"
                  className="border-b border-line-soft last:border-0"
                >
                  <td className="px-5 py-3 text-[13px] font-medium text-ink">{c.column}</td>
                  <td className="px-5 py-3 text-[12.5px] text-ink-mute">{c.metric}</td>
                  <td className="tnum px-5 py-3 text-[12.5px] text-ink">{c.distance.toFixed(4)}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-28">
                        <Meter value={c.match} tone={tone(c.match)} height={5} />
                      </div>
                      <span className="tnum w-12 text-[12.5px] font-semibold text-ink">
                        {c.match.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
          {fidelity.regenerated_columns.length > 0 && (
            <div className="flex items-start gap-2 border-t border-line bg-canvas/50 px-5 py-3">
              <IconCheck size={14} className="mt-0.5 shrink-0 text-grass" />
              <p className="text-[11.5px] leading-snug text-ink-mute">
                <strong className="text-ink">
                  {fidelity.regenerated_columns.join(", ")}
                </strong>{" "}
                are regenerated from scratch and excluded from scoring by design — they are meant to
                differ from the source, which is the privacy guarantee.
              </p>
            </div>
          )}
        </Card>
      </motion.div>
    </div>
  );
}
