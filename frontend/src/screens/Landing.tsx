import { motion } from "framer-motion";
import { useState } from "react";
import { useStore } from "../lib/store";
import { rise } from "../lib/motion";
import type { ScreenId } from "../lib/nav";

export function Landing() {
  const { go, triggerIntro } = useStore();
  const [email, setEmail] = useState("");

  const handleStart = (target: ScreenId = "workspace") => {
    triggerIntro(target);
  };

  return (
    <div className="bg-background text-on-surface antialiased font-sans text-body-default min-h-screen selection:bg-secondary-container selection:text-primary -mx-4 sm:-mx-6 -mt-6">
      {/* ================= NAVBAR ================= */}
      <header className="sticky top-0 z-50 bg-surface-container-lowest/90 backdrop-blur-md border-b border-outline-variant/30 transition-all">
        <div className="h-16 flex items-center justify-between px-6 max-w-7xl mx-auto w-full">
          {/* Left: Brand Logo */}
          {/* The brand lockup carries its own wordmark, so no text beside it. */}
          <div className="flex items-center cursor-pointer group" onClick={() => handleStart("projects")}>
            <img
              src="/dataseed-logo.png"
              alt="DataSeed"
              className="h-9 w-auto shrink-0 select-none transition-transform duration-150 group-hover:scale-105"
              draggable={false}
            />
          </div>

          {/* Center navigation links */}
          <nav className="hidden md:flex items-center gap-6">
            <a href="#home" className="text-[13px] text-primary font-semibold hover:text-primary-container transition-colors">
              Home
            </a>
            <a href="#features" className="text-[13px] text-secondary font-medium hover:text-primary transition-colors">
              Features
            </a>
            <a href="#how-it-works" className="text-[13px] text-secondary font-medium hover:text-primary transition-colors">
              How it works
            </a>
            <button type="button" onClick={() => go("documents")} className="text-[13px] text-secondary font-medium hover:text-primary transition-colors">
              Docs
            </button>
          </nav>

          {/* Right actions */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => handleStart("projects")}
              className="text-[13px] font-semibold text-primary-container px-4 py-2 rounded-full border border-primary-container/40 hover:bg-secondary-container hover:border-primary-container transition-all duration-150"
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => handleStart("workspace")}
              className="text-[13px] font-semibold text-on-primary bg-primary-container hover:bg-primary px-6 py-2 rounded-full transition-all duration-150 active:scale-95 shadow-sm"
            >
              Try free
            </button>
          </div>
        </div>
      </header>

      {/* ================= HERO SECTION ================= */}
      <section className="pt-8 pb-16 px-6 max-w-7xl mx-auto w-full" id="home">
        <motion.div
          variants={rise}
          initial="hidden"
          animate="show"
          className="relative overflow-hidden rounded-[24px] border border-outline-variant/50 bg-gradient-to-br from-[#FFF3DF]/60 via-[#E9DFFF]/50 to-background p-6 md:p-12 bento-shadow"
        >
          {/* Ambient light decorative elements */}
          <div className="absolute -top-32 -right-24 w-96 h-96 bg-primary-fixed/40 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-20 w-80 h-80 bg-tertiary-fixed/30 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            {/* Left Column */}
            <div className="lg:col-span-6 space-y-6">
              {/* AI Badge */}
              <div className="inline-flex items-center gap-1.5 bg-[#FFD666] text-[#1B1740] text-[11px] uppercase tracking-wider font-bold px-3 py-1 rounded-full shadow-xs">
                <span>✦</span>
                <span>AI-powered</span>
              </div>

              {/* Headline */}
              <h1 className="text-[36px] sm:text-[48px] lg:text-[56px] font-bold text-on-surface leading-tight tracking-tight">
                Real-looking data.{" "}
                <span className="bg-primary-container text-on-primary px-3.5 py-0.5 rounded-full inline-block shadow-sm">
                  Zero
                </span>{" "}
                real records.
              </h1>

              {/* Subtext */}
              <p className="text-[15px] sm:text-[16px] text-secondary max-w-xl leading-relaxed">
                Generate privacy-safe tabular, relational and document data on demand — no code required.
              </p>

              {/* Email signup form */}
              <form
                className="flex flex-col sm:flex-row gap-2.5 max-w-lg pt-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleStart("workspace");
                }}
              >
                <div className="relative flex-1">
                  <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-outline text-[20px]">
                    mail
                  </span>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter your work email..."
                    className="w-full h-11 pl-10 pr-4 rounded-xl bg-surface-container-lowest border border-outline-variant/60 text-on-surface placeholder:text-outline text-[13px] focus:border-primary-container focus:ring-2 focus:ring-primary-fixed focus:outline-none transition-all shadow-xs"
                  />
                </div>
                <button
                  type="submit"
                  className="h-11 px-6 rounded-full bg-primary-container text-on-primary font-semibold text-[13px] hover:bg-primary transition-all duration-150 active:scale-95 shadow-sm flex items-center justify-center gap-2 whitespace-nowrap"
                >
                  <span>Get started</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </form>

              {/* Trust checklist */}
              <div className="flex flex-wrap items-center gap-6 pt-2 text-secondary text-[13px] font-semibold">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-secondary-container text-primary flex items-center justify-center">
                    <span className="material-symbols-outlined text-[14px] font-bold">check</span>
                  </span>
                  <span>No real data needed</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-secondary-container text-primary flex items-center justify-center">
                    <span className="material-symbols-outlined text-[14px] font-bold">check</span>
                  </span>
                  <span>Export in seconds</span>
                </div>
              </div>
            </div>

            {/* Right Column: App Mockup */}
            <div className="lg:col-span-6 relative flex justify-center items-center py-6">
              <div className="w-full max-w-lg bg-surface-container-lowest border border-outline-variant/70 rounded-2xl shadow-xl overflow-hidden transform md:rotate-1 hover:rotate-0 transition-transform duration-300">
                {/* Window header */}
                <div className="h-8 bg-surface-container-low border-b border-outline-variant/40 px-3 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-outline-variant" />
                    <div className="w-2.5 h-2.5 rounded-full bg-outline-variant" />
                    <div className="w-2.5 h-2.5 rounded-full bg-outline-variant" />
                  </div>
                  <div className="text-[11px] font-mono text-outline bg-surface-container-lowest px-2 py-0.5 rounded border border-outline-variant/30">
                    dataseed.internal/workspace/v2
                  </div>
                  <div className="w-8" />
                </div>

                {/* Workspace Screen Preview */}
                <div className="p-4 bg-surface space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-outline-variant/30">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-secondary-container text-primary flex items-center justify-center">
                        <span className="material-symbols-outlined text-[16px]">schema</span>
                      </div>
                      <div>
                        <div className="text-[13px] font-bold text-on-surface">production_replica_v4</div>
                        <div className="text-[10px] text-outline font-sans">Synthesizing 5 relational tables</div>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-[#E5F7ED] text-[#1E7E4E] text-[11px] font-semibold flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#22A06B]" /> Validated
                    </span>
                  </div>

                  {/* Micro data table in screen */}
                  <div className="rounded-xl border border-outline-variant/40 bg-surface-container-lowest overflow-hidden text-[11px]">
                    <div className="grid grid-cols-4 bg-surface-container-low p-2 font-mono text-secondary font-medium border-b border-outline-variant/30">
                      <span>ID</span>
                      <span>RECORD_TYPE</span>
                      <span>STATUS</span>
                      <span className="text-right">DISTRIBUTION</span>
                    </div>
                    <div className="p-2 space-y-1.5 font-mono text-on-surface-variant">
                      <div className="grid grid-cols-4 items-center">
                        <span className="text-primary font-semibold">SYN-8819</span>
                        <span>cust_profile</span>
                        <span className="text-[#22A06B]">synthesized</span>
                        <span className="text-right text-outline">Gaussian</span>
                      </div>
                      <div className="grid grid-cols-4 items-center">
                        <span className="text-primary font-semibold">SYN-8820</span>
                        <span>txn_ledger</span>
                        <span className="text-[#22A06B]">synthesized</span>
                        <span className="text-right text-outline">Multivariate</span>
                      </div>
                      <div className="grid grid-cols-4 items-center">
                        <span className="text-primary font-semibold">SYN-8821</span>
                        <span>claim_event</span>
                        <span className="text-[#755B00]">sampling</span>
                        <span className="text-right text-outline">Poisson</span>
                      </div>
                    </div>
                  </div>

                  {/* Interactive generation progress bar */}
                  <div className="p-2.5 rounded-xl bg-surface-container-low border border-outline-variant/30 flex items-center justify-between text-xs">
                    <span className="text-secondary font-medium">Pipeline throughput</span>
                    <span className="font-mono font-semibold text-primary">48,200 rows/sec</span>
                  </div>
                </div>
              </div>

              {/* Overlapping Floating Card 1: Row count metric */}
              <div className="absolute -top-4 -left-4 md:-left-6 bg-surface-container-lowest/95 backdrop-blur-md border border-outline-variant/60 rounded-2xl p-3.5 shadow-xl flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-secondary-container text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">analytics</span>
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-secondary">Rows generated</div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[16px] font-bold text-on-surface">2.4M</span>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[#E5F7ED] text-[#1E7E4E]">+12%</span>
                  </div>
                </div>
              </div>

              {/* Overlapping Floating Card 2: Mini Bar chart card */}
              <div className="absolute -bottom-6 -left-2 md:left-4 bg-surface-container-lowest/95 backdrop-blur-md border border-outline-variant/60 rounded-2xl p-3 shadow-xl w-44">
                <div className="text-[10px] font-semibold text-secondary mb-1 flex items-center justify-between">
                  <span>Entropy parity</span>
                  <span className="text-[9px] font-mono text-primary font-bold">0.994</span>
                </div>
                <div className="h-10 flex items-end gap-1.5 pt-1">
                  <div className="flex-1 bg-primary-fixed rounded-t-sm h-4" />
                  <div className="flex-1 bg-secondary-container rounded-t-sm h-7" />
                  <div className="flex-1 bg-primary-container rounded-t-sm h-10" />
                  <div className="flex-1 bg-primary-container/80 rounded-t-sm h-8" />
                  <div className="flex-1 bg-primary-fixed rounded-t-sm h-6" />
                  <div className="flex-1 bg-primary rounded-t-sm h-9" />
                </div>
              </div>

              {/* Overlapping Floating Card 3: Donut fidelity card */}
              <div className="absolute -bottom-4 -right-2 md:-right-4 bg-surface-container-lowest/95 backdrop-blur-md border border-outline-variant/60 rounded-2xl p-3 shadow-xl flex items-center gap-3">
                <div className="relative w-10 h-10 flex items-center justify-center">
                  <svg className="w-10 h-10 transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-surface-container-high"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3.5"
                    />
                    <path
                      className="text-primary-container"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="currentColor"
                      strokeDasharray="96.4, 100"
                      strokeLinecap="round"
                      strokeWidth="3.5"
                    />
                  </svg>
                  <span className="material-symbols-outlined absolute text-[14px] text-primary">verified</span>
                </div>
                <div>
                  <div className="text-[10px] font-semibold text-secondary">Fidelity score</div>
                  <div className="text-[15px] font-bold text-on-surface">96.4%</div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ================= SECTION 2: THE PROBLEM ================= */}
      <section className="py-14 px-6 max-w-7xl mx-auto w-full">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <span className="text-[12px] text-primary uppercase tracking-wider font-semibold">Overcome Legacy Friction</span>
          <h2 className="text-[28px] sm:text-[32px] font-bold text-on-surface mt-1">The bottlenecks in modern data testing</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow hover:-translate-y-1 transition-transform duration-200 flex flex-col">
            <div className="w-12 h-12 rounded-2xl bg-secondary-container text-primary flex items-center justify-center mb-5">
              <span className="material-symbols-outlined text-[24px]">lock</span>
            </div>
            <h3 className="text-[18px] font-bold text-on-surface mb-2">Privacy & compliance</h3>
            <p className="text-[15px] text-secondary leading-relaxed">
              GDPR, HIPAA, and CCPA make production data sharing high-risk and legally fraught.
            </p>
          </div>
          {/* Card 2 */}
          <div className="bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow hover:-translate-y-1 transition-transform duration-200 flex flex-col">
            <div className="w-12 h-12 rounded-2xl bg-secondary-container text-primary flex items-center justify-center mb-5">
              <span className="material-symbols-outlined text-[24px]">database</span>
            </div>
            <h3 className="text-[18px] font-bold text-on-surface mb-2">Limited, messy datasets</h3>
            <p className="text-[15px] text-secondary leading-relaxed">
              Staging environments starve on incomplete, skewed, or unrepresentative sample data.
            </p>
          </div>
          {/* Card 3 */}
          <div className="bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow hover:-translate-y-1 transition-transform duration-200 flex flex-col">
            <div className="w-12 h-12 rounded-2xl bg-secondary-container text-primary flex items-center justify-center mb-5">
              <span className="material-symbols-outlined text-[24px]">hourglass_empty</span>
            </div>
            <h3 className="text-[18px] font-bold text-on-surface mb-2">Slow procurement cycles</h3>
            <p className="text-[15px] text-secondary leading-relaxed">
              Engineering and QA teams wait weeks for data approvals and sanitized dumps.
            </p>
          </div>
        </div>
      </section>

      {/* ================= SECTION 3: HOW IT WORKS IN FOUR STEPS ================= */}
      <section className="py-14 px-6 max-w-7xl mx-auto w-full" id="how-it-works">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-[12px] text-primary uppercase tracking-wider font-semibold">Workflow Engine</span>
          <h2 className="text-[28px] sm:text-[32px] font-bold text-on-surface mt-1">How it works in four steps</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 relative">
          {/* Step 1 */}
          <div className="bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col relative group">
            <div className="flex items-center justify-between mb-4">
              <span className="w-8 h-8 rounded-full bg-surface-container text-primary font-mono font-bold text-xs flex items-center justify-center border border-outline-variant/40">
                01
              </span>
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
                upload_file
              </span>
            </div>
            <h3 className="text-[16px] font-bold text-on-surface mb-2">Ingest schema</h3>
            <p className="text-[13px] text-secondary leading-relaxed">
              Upload DDL, JSON schema, or connect via read-only replica.
            </p>
          </div>
          {/* Step 2 */}
          <div className="bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col relative group">
            <div className="flex items-center justify-between mb-4">
              <span className="w-8 h-8 rounded-full bg-surface-container text-primary font-mono font-bold text-xs flex items-center justify-center border border-outline-variant/40">
                02
              </span>
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
                alt_route
              </span>
            </div>
            <h3 className="text-[16px] font-bold text-on-surface mb-2">Model relationships</h3>
            <p className="text-[13px] text-secondary leading-relaxed">
              Automatically map foreign keys, cardinality, and constraints.
            </p>
          </div>
          {/* Step 3: Special Lavender Card */}
          <div className="rounded-[20px] border border-primary-fixed bg-gradient-to-br from-[#E9DFFF] to-[#F8D9F0] p-6 bento-shadow flex flex-col relative group overflow-hidden">
            <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-primary-container/10 rounded-full blur-xl pointer-events-none" />
            <div className="flex items-center justify-between mb-4 relative z-10">
              <span className="w-8 h-8 rounded-full bg-primary-container text-on-primary font-mono font-bold text-xs flex items-center justify-center shadow-xs">
                03
              </span>
              <div className="flex items-center gap-1 bg-[#FFD666] text-[#1B1740] text-[10px] font-extrabold px-2 py-0.5 rounded-full">
                <span>✦</span> AI
              </div>
            </div>
            <h3 className="text-[16px] font-bold text-on-surface mb-2 relative z-10">Generate with AI</h3>
            <p className="text-[13px] text-on-surface-variant font-medium leading-relaxed relative z-10">
              Neural generators synthesize deep multivariate distributions.
            </p>
          </div>
          {/* Step 4 */}
          <div className="bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col relative group">
            <div className="flex items-center justify-between mb-4">
              <span className="w-8 h-8 rounded-full bg-surface-container text-primary font-mono font-bold text-xs flex items-center justify-center border border-outline-variant/40">
                04
              </span>
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
                cloud_download
              </span>
            </div>
            <h3 className="text-[16px] font-bold text-on-surface mb-2">Validate & export</h3>
            <p className="text-[13px] text-secondary leading-relaxed">
              Check statistical fidelity benchmarks and export instantly to CSV, Parquet, or SQL.
            </p>
          </div>
        </div>
      </section>

      {/* ================= SECTION 4: EVERYTHING YOU NEED BENTO GRID ================= */}
      <section className="py-14 px-6 max-w-7xl mx-auto w-full" id="features">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-[12px] text-primary uppercase tracking-wider font-semibold">Full Synthesis Suite</span>
          <h2 className="text-[28px] sm:text-[32px] font-bold text-on-surface mt-1">Everything you need</h2>
        </div>
        {/* Asymmetric Bento Grid (12 cols) */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* 1. Tabular Data Card (Col 7) */}
          <div className="md:col-span-7 bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-secondary-container text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">table_chart</span>
                </div>
                <div>
                  <h3 className="text-[18px] font-bold text-on-surface">Tabular Data</h3>
                  <p className="text-xs text-secondary font-semibold">High-density multivariate synthesis</p>
                </div>
              </div>
              <p className="text-[13px] text-secondary mb-4">
                Generates compliant tabular datasets with correlated attributes, edge cases, and zero leakage.
              </p>
            </div>
            {/* Realistic Mock Table */}
            <div className="rounded-xl border border-outline-variant/40 overflow-hidden bg-surface">
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-[11px]">
                  <thead className="bg-surface-container-low border-b border-outline-variant/30 text-secondary">
                    <tr>
                      <th className="py-2 px-3">Customer_ID</th>
                      <th className="py-2 px-3">Name</th>
                      <th className="py-2 px-3">Email</th>
                      <th className="py-2 px-3 text-right">Balance</th>
                      <th className="py-2 px-3">Country</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/20 text-on-surface-variant">
                    <tr className="hover:bg-surface-container-lowest/80 transition-colors">
                      <td className="py-2 px-3 text-primary font-semibold">CUST-1049</td>
                      <td className="py-2 px-3">Elena Rostova</td>
                      <td className="py-2 px-3 text-secondary">elena.r@synmail.io</td>
                      <td className="py-2 px-3 text-right font-medium">$14,290.40</td>
                      <td className="py-2 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-surface-container text-on-surface text-[10px]">
                          DE
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-container-lowest/80 transition-colors">
                      <td className="py-2 px-3 text-primary font-semibold">CUST-1050</td>
                      <td className="py-2 px-3">Marcus Thorne</td>
                      <td className="py-2 px-3 text-secondary">m.thorne@testlab.dev</td>
                      <td className="py-2 px-3 text-right font-medium">$8,450.00</td>
                      <td className="py-2 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-surface-container text-on-surface text-[10px]">
                          US
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-container-lowest/80 transition-colors">
                      <td className="py-2 px-3 text-primary font-semibold">CUST-1051</td>
                      <td className="py-2 px-3">Amina Yusuf</td>
                      <td className="py-2 px-3 text-secondary">amina.y@synthbox.org</td>
                      <td className="py-2 px-3 text-right font-medium">$22,110.85</td>
                      <td className="py-2 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-surface-container text-on-surface text-[10px]">
                          GB
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* 2. Relational Card (Col 5) */}
          <div className="md:col-span-5 bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-secondary-container text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">hub</span>
                </div>
                <div>
                  <h3 className="text-[18px] font-bold text-on-surface">Relational Architecture</h3>
                  <p className="text-xs text-secondary font-semibold">Strict Foreign-Key Integrity</p>
                </div>
              </div>
              <p className="text-[13px] text-secondary mb-4">
                Preserves 1:1, 1:N, and N:M constraints automatically across cascading databases.
              </p>
            </div>
            {/* 3-Table diagram */}
            <div className="flex flex-col gap-2.5 bg-surface p-3 rounded-xl border border-outline-variant/40">
              <div className="flex items-center justify-between bg-surface-container-lowest p-2 rounded-lg border border-outline-variant/30 text-xs">
                <span className="font-mono font-semibold text-primary">Customers (PK: id)</span>
                <span className="text-[10px] bg-secondary-container text-primary px-2 py-0.5 rounded-full font-medium">
                  1 : N
                </span>
              </div>
              <div className="flex justify-center text-outline">
                <span className="material-symbols-outlined text-[16px]">arrow_downward</span>
              </div>
              <div className="flex items-center justify-between bg-surface-container-lowest p-2 rounded-lg border border-outline-variant/30 text-xs">
                <span className="font-mono font-semibold text-primary">Orders (FK: cust_id)</span>
                <span className="text-[10px] bg-secondary-container text-primary px-2 py-0.5 rounded-full font-medium">
                  1 : N
                </span>
              </div>
              <div className="flex justify-center text-outline">
                <span className="material-symbols-outlined text-[16px]">arrow_downward</span>
              </div>
              <div className="flex items-center justify-between bg-surface-container-lowest p-2 rounded-lg border border-outline-variant/30 text-xs">
                <span className="font-mono font-semibold text-primary">Order_Items (FK: ord_id)</span>
                <span className="text-[10px] text-outline font-mono">Cascade sync</span>
              </div>
            </div>
          </div>

          {/* 3. Documents Card (Col 4) */}
          <div className="md:col-span-4 bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-secondary-container text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">description</span>
                </div>
                <div>
                  <h3 className="text-[18px] font-bold text-on-surface">Unstructured Docs</h3>
                  <p className="text-xs text-secondary font-semibold">Realistic OCR & PDF generation</p>
                </div>
              </div>
              <p className="text-[13px] text-secondary mb-4">
                Generate synthetic billing statements, legal invoices, and clinical discharge summaries.
              </p>
            </div>
            {/* Invoice preview */}
            <div className="bg-surface rounded-xl p-3 border border-outline-variant/40 space-y-2 text-[11px]">
              <div className="flex justify-between items-center pb-1.5 border-b border-outline-variant/30">
                <div className="font-bold text-on-surface">INVOICE #SYN-9022</div>
                <div className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-primary-container text-on-primary font-bold">
                  SYNTHETIC SEAL
                </div>
              </div>
              <div className="space-y-1 text-secondary">
                <div className="flex justify-between"><span>Enterprise Engine (Monthly)</span><span>$1,400.00</span></div>
                <div className="flex justify-between"><span>Differential Privacy Addon</span><span>$250.00</span></div>
              </div>
              <div className="pt-1.5 border-t border-outline-variant/30 flex justify-between font-bold text-on-surface">
                <span>Subtotal</span>
                <span className="text-primary">$1,650.00</span>
              </div>
            </div>
          </div>

          {/* 4. AI Layer Card (Col 4) */}
          <div className="md:col-span-4 bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-secondary-container text-primary flex items-center justify-center">
                    <span className="material-symbols-outlined text-[20px]">auto_awesome</span>
                  </div>
                  <h3 className="text-[18px] font-bold text-on-surface">AI Synthesis Layer</h3>
                </div>
                <span className="bg-[#FFD666] text-[#1B1740] text-[10px] uppercase font-extrabold px-2 py-0.5 rounded-full inline-flex items-center gap-1">
                  ✦ AI
                </span>
              </div>
              <p className="text-[13px] text-secondary mb-4">
                Deep generative models that reason over complex business logic without exposing raw seed records.
              </p>
            </div>
            <ul className="space-y-2.5 text-xs text-on-surface-variant font-semibold">
              <li className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-secondary-container text-primary flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-[13px]">check</span>
                </span>
                <span>Schema understanding & constraint preservation</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-secondary-container text-primary flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-[13px]">check</span>
                </span>
                <span>Realistic contextual content generation</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-secondary-container text-primary flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-[13px]">check</span>
                </span>
                <span>Edge-case injection for stress testing</span>
              </li>
            </ul>
          </div>

          {/* 5. Privacy Controls Card (Col 4) */}
          <div className="md:col-span-4 bg-surface-container-lowest rounded-[20px] border border-outline-variant/60 p-6 bento-shadow flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-secondary-container text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-[20px]">security</span>
                </div>
                <div>
                  <h3 className="text-[18px] font-bold text-on-surface">Privacy Controls</h3>
                  <p className="text-xs text-secondary font-semibold">Mathematical anonymity guarantees</p>
                </div>
              </div>
              <p className="text-[13px] text-secondary mb-4">
                Configurable epsilon noise dials and irreversible zero-knowledge data transformations.
              </p>
            </div>
            <div className="flex flex-col gap-2 text-xs font-semibold">
              <div className="flex items-center justify-between p-2 rounded-xl bg-surface border border-outline-variant/40">
                <span className="text-on-surface">Differential noise (ε=0.5)</span>
                <span className="px-2 py-0.5 rounded-full bg-primary-container text-on-primary text-[10px] font-semibold">
                  Active
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-surface border border-outline-variant/40">
                <span className="text-on-surface">Cryptographic hashing</span>
                <span className="px-2 py-0.5 rounded-full bg-secondary-container text-primary text-[10px] font-semibold">
                  SHA-256
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-surface border border-outline-variant/40">
                <span className="text-on-surface">k-Anonymity masking</span>
                <span className="px-2 py-0.5 rounded-full bg-surface-container text-secondary text-[10px] font-semibold">
                  k = 5
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= SECTION 5: FULL-WIDTH VIOLET GRADIENT CTA BAND ================= */}
      <section className="py-16 px-6 max-w-7xl mx-auto w-full">
        <div className="rounded-3xl bg-gradient-to-r from-primary-container to-[#472EA6] text-on-primary p-8 md:p-14 text-center relative overflow-hidden shadow-xl">
          {/* Ambient light decorative rings */}
          <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-white/10 blur-2xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-black/10 blur-2xl pointer-events-none" />
          <div className="relative z-10 max-w-2xl mx-auto space-y-4">
            <h2 className="text-[32px] md:text-[44px] md:leading-[52px] font-bold text-white tracking-tight">
              Ship data, not delays.
            </h2>
            <p className="text-on-primary-container max-w-lg mx-auto text-base leading-relaxed">
              Spin up millions of realistic, compliant rows in under 60 seconds.
            </p>
            <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => handleStart("workspace")}
                className="h-12 px-8 rounded-full bg-white text-primary-container font-semibold text-[14px] hover:bg-surface-bright transition-all duration-150 active:scale-95 shadow-md flex items-center justify-center gap-2"
              >
                <span>Start generating</span>
                <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
              </button>
              <button
                type="button"
                onClick={() => go("documents")}
                className="h-12 px-6 rounded-full text-white hover:bg-white/10 font-semibold text-[14px] transition-all duration-150 flex items-center justify-center"
              >
                Explore Documentation
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ================= FOOTER ================= */}
      <footer className="bg-surface-container-lowest border-t border-outline-variant/40 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
            {/* Brand column */}
            <div className="col-span-2 space-y-3">
              <div className="flex items-center cursor-pointer" onClick={() => handleStart("landing")}>
                <img
                  src="/dataseed-logo.png"
                  alt="DataSeed"
                  className="h-8 w-auto shrink-0 select-none"
                  draggable={false}
                />
              </div>
              <p className="text-secondary text-[13px] max-w-sm">
                Enterprise engine for generating statistical-fidelity synthetic datasets without legal or regulatory friction.
              </p>
            </div>
            {/* Col 1: Product */}
            <div className="space-y-3">
              <div className="text-[12px] text-on-surface font-bold uppercase tracking-wider">Product</div>
              <ul className="space-y-2 text-[13px] text-secondary">
                <li><button type="button" onClick={() => handleStart("workspace")} className="hover:text-primary transition-colors">Tabular Synthesizer</button></li>
                <li><button type="button" onClick={() => handleStart("relationships")} className="hover:text-primary transition-colors">Relational Linker</button></li>
                <li><button type="button" onClick={() => go("documents")} className="hover:text-primary transition-colors">Document Simulator</button></li>
                <li><button type="button" onClick={() => go("rules")} className="hover:text-primary transition-colors">Differential Privacy</button></li>
              </ul>
            </div>
            {/* Col 2: Solutions */}
            <div className="space-y-3">
              <div className="text-[12px] text-on-surface font-bold uppercase tracking-wider">Solutions</div>
              <ul className="space-y-2 text-[13px] text-secondary">
                <li><button type="button" onClick={() => handleStart("workspace")} className="hover:text-primary transition-colors">FinTech Testing</button></li>
                <li><button type="button" onClick={() => handleStart("workspace")} className="hover:text-primary transition-colors">Healthcare HIPAA</button></li>
                <li><button type="button" onClick={() => handleStart("workspace")} className="hover:text-primary transition-colors">AI Model Pretraining</button></li>
                <li><button type="button" onClick={() => handleStart("workspace")} className="hover:text-primary transition-colors">Staging Environments</button></li>
              </ul>
            </div>
            {/* Col 3: Developers */}
            <div className="space-y-3">
              <div className="text-[12px] text-on-surface font-bold uppercase tracking-wider">Developers</div>
              <ul className="space-y-2 text-[13px] text-secondary">
                <li><button type="button" onClick={() => go("documents")} className="hover:text-primary transition-colors">API Docs</button></li>
                <li><button type="button" onClick={() => go("settings")} className="hover:text-primary transition-colors">CLI Tool</button></li>
                <li><button type="button" onClick={() => go("documents")} className="hover:text-primary transition-colors">Python SDK</button></li>
                <li><button type="button" onClick={() => go("trust")} className="hover:text-primary transition-colors">Security Architecture</button></li>
              </ul>
            </div>
          </div>
          {/* Bottom separation */}
          <div className="pt-6 border-t border-outline-variant/30 flex flex-col md:flex-row justify-between items-center gap-4 text-secondary text-[13px]">
            <p>© 2026 DataSeed AI Inc. All rights reserved.</p>
            <div className="flex items-center gap-6">
              <button type="button" onClick={() => go("trust")} className="hover:text-primary transition-colors">Privacy Policy</button>
              <button type="button" onClick={() => go("trust")} className="hover:text-primary transition-colors">Terms of Service</button>
              <button type="button" onClick={() => go("trust")} className="hover:text-primary transition-colors">Security</button>
              <button type="button" onClick={() => handleStart("workspace")} className="hover:text-primary transition-colors">Status</button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
