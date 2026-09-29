# HackDataV2, Synthetic Data Platform: Decoded Brief

## What the deck actually asks for
A platform that generates **realistic, privacy-safe synthetic data on demand** in three shapes:

| Shape | What it means | Hard requirement from deck |
|---|---|---|
| **Tabular** | One flat table (CSV/JSON) | Statistically faithful distributions; configurable row count, seed, null/outlier rate; column-level masking/hashing/noise |
| **Relational** | Many tables joined by keys | Referential integrity auto-maintained; configurable 1:1, 1:N, N:N; cross-table consistency (order totals reconcile with line items) |
| **Documents** | Invoices, bank statements | Line items + tax that reconcile; per-region templates; running balances; query-style generation ("last 90 days, balance over $500"); bulk output |

Plus an **AI layer across all three**: schema understanding, realistic content synthesis, edge-case injection.
Plus **one workspace UI**: live preview canvas (left) + config panel (right) + export.

## Theme.txt decoded, and one correction
> "2 ways to produce synthetic data: TSTR approach / Relational multi-relationship table build"

**TSTR is not a generation method, it is the evaluation protocol.**
TSTR = **Train on Synthetic, Test on Real**. You train an ML model on your generated data,
evaluate it on held-out *real* data, and compare against the same model trained on real data (TRTR).
If `TSTR_score / TRTR_score ≈ 1.0`, your synthetic data is provably as useful as the real thing.

So the two tracks are really:
1. **Track A, Single-table generation, proven by TSTR.** Generate one table, then *prove* its quality
   with a TSTR utility score. This is the "is it actually good?" track.
2. **Track B, Relational multi-table build.** Generate a whole connected schema with FK integrity.
   This is the "is it actually a system?" track.

Say this out loud to the judges. Knowing that TSTR is a *measurement*, and then shipping it as a
visible score in the UI, is the single cheapest way to look like you know the field.

## The judging criteria (deck page 11) and what "100%" requires
| Criterion | Minimum to pass | What actually scores 100% |
|---|---|---|
| **System design** | It works | One schema-aware pipeline that all three engines share; visible DAG; deterministic + reproducible by seed |
| **Features** | Tabular + relational + docs | All three **plus** a validation/trust layer and real export formats (CSV/JSON/Parquet/SQL dump/PDF) |
| **UI** | Pages exist | One workspace, live streaming preview, editable ER graph, no-code, zero raw stack traces |
| **AI** | "We call an LLM" | 4 scoped AI jobs with schema-validated output and deterministic fallbacks, AI improves it, never breaks it |
| **Problem approach** | Slides | A **Trust Report**: fidelity + utility (TSTR) + privacy (DCR) + integrity, with export gated on green |

**The winning move:** everyone will build a generator. Almost nobody will build the **proof**.
The Trust Report is the differentiator. Build it early, not last.
