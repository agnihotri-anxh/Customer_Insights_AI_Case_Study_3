# Case 3: The Two Calendars — Solution Document

## 1. Solution Overview

Six months after our MMM recommended shifting 15% of TV budget into digital and email, we noticed weekly totals no longer matched the calendar — tracing back to Exhibit 1: TV spend is reported on a Monday-to-Sunday broadcast week, while digital, email, and sales are reported on calendar months. We built a synthetic dataset with known true channel effects (grounded in a public Google Meridian sample dataset), reproduced the bug by aggregating TV spend two ways — naively, and by apportioning each week's spend across the actual calendar days it covers — and fit a Bayesian marketing-mix model on each version. On our synthetic case, the calendar bug alone didn't flip the reallocation call: naive and corrected aggregation gave statistically indistinguishable results. But even the corrected model missed the true TV contribution, pointing to a second, more serious attribution-reliability problem (channel collinearity with only ~37 months of data) that the calendar fix doesn't solve by itself. Our recommendation is to hold the 15% reallocation story until that deeper uncertainty is addressed, and to keep the validation pipeline we built running automatically on every data refresh, so a vendor calendar/grain mismatch like this one gets caught before it ever reaches a stakeholder presentation again.

## 2. Approach and Methodology

| Step | What we did | Why it was needed |
|---|---|---|
| 1. Source realistic spend data | Pulled Google Meridian's open-source simulated weekly, multi-channel spend dataset and collapsed it from geo-level to a national weekly series | The case allows "adapt a public MMM sample dataset" — using real, published spend shapes (seasonality, scale, correlation) makes the exercise more credible than arbitrary synthetic noise |
| 2. Generate ground-truth sales | Declared known per-channel true effects (contribution share, adstock decay, saturation) and synthesized monthly sales from the base spend | No public dataset publishes "true" channel effects — without a known answer key, there's no way to objectively prove whether a fix recovers the truth better than the bug |
| 3. Reproduce the bug | Built two TV aggregation functions: `naive_monthly()` (dumps a whole broadcast week into its start month) and `correct_monthly()` (splits a week's spend proportionally across the calendar days it spans) | This is Exhibit 1's actual mechanism — the only way to test its impact is to build both versions and compare |
| 4. Fit a Bayesian MMM | Used `pymc-marketing`'s `MMM` class (geometric adstock + logistic saturation) via MCMC, once per aggregation | Gives real posterior credible intervals instead of point estimates — essential since the case explicitly asks for "confidence," not just a number |
| 5. Compare and verdict | Checked whether credible intervals shift between naive/correct, and whether either fit's interval recovers the known true value | Directly answers the case's question #4: does the bug change the call, and how sure are we |
| 6. Validate vendor specs | An LLM-backed checker (`openai/gpt-oss-20b` via Groq) reads short vendor file-spec text and flags grain/calendar mismatches, with a deterministic offline fallback | The case explicitly asks for this ("use an LLM to read vendor file specifications"), and it's the control that prevents this exact bug from recurring silently |
| 7. Report | A static HTML report (chart + verdict + flags) and an 8-slide HTML deck, built from one shared pipeline run | Collaterals the case asks for, aimed at two different audiences (analyst vs. Brand Director) |

## 3. How We Arrived At It

**Alternatives considered and rejected:**
- **Robyn vs. Meridian for the base dataset** — rejected Robyn because its demo dataset lives inside an R package's data files, requiring an R environment; Meridian's sample data is plain Python-readable CSV, fitting a Python-only pipeline with no cross-language step.
- **Fully synthetic generation vs. adapting a public dataset** — rejected doing either alone. A purely synthetic dataset with no real spend shape would be less credible; a purely public dataset has no "true" effects to validate against. We used both together: real spend shape from Meridian, declared true effects layered on top.
- **Hand-rolled MMM vs. a Bayesian library** — our first draft hand-rolled a regression with bootstrap confidence intervals. We revisited this decision mid-design and switched to `pymc-marketing`, a purpose-built Bayesian MMM library, once it became clear that proper credible intervals (not bootstrap approximations) better served the case's "how confident are you" requirement, and that adstock/saturation transforms didn't need reinventing.
- **Claude vs. Groq for the LLM validation step** — originally scoped as a generic "Claude or offline" pluggable interface; switched to Groq's `openai/gpt-oss-20b` once an API key was available, keeping the same pluggable interface so either could be swapped in without touching `spec_check.py`.

**Key assumptions made (in place of a real client to ask):**
- Meridian's 5 generic channels (`Channel0`–`Channel4`) were mapped to TV/Digital/Email by **spend rank** (largest → TV), not by any real semantic label — Meridian doesn't name its channels, and TV is typically the dominant line item in a pharma media mix.
- Geo-level data was collapsed to **national** totals, matching the case's single-brand (not geo-specific) framing.
- A **90% credible interval** was used throughout as the uncertainty threshold.
- Declared true contribution shares (TV 22%, Digital 14%, Email 6% of baseline sales) and adstock/saturation parameters were chosen judgmentally to produce a plausible, TV-dominant media mix — documented as tunable, not derived from any real client data.

**Self-directed "clarification desk" decisions** (made during an iterative design conversation in place of a live client Q&A, each documented at the time in `workflow.md`): use open-source sample data rather than generate from nothing; use a Bayesian library rather than hand-rolled code; simplify the pipeline to one fit call per aggregation rather than separate transform/fit/uncertainty modules; use Groq for the LLM step.

## 4. Data

**Source:** `geo_all_channels.csv` from Google's open-source [Meridian](https://github.com/google/meridian) MMM library — simulated data Meridian ships for its own getting-started tutorial, not real client data.

**Raw structure:** weekly, geo-level (12+ regions), 2021-01-25 to 2024-01-15 (156 weeks ≈ 3 years), 5 generic paid channels with impressions and spend, plus organic media, a promo flag, control variables, a conversions KPI, and population.

**What we built on top of it:** collapsed geos to a national weekly series; ranked channels by spend and assigned the top 3 to TV/Digital/Email roles; declared our own true per-channel effects to synthesize monthly sales (see Section 2).

**Limitations:**
- Channel names are **assigned by spend rank**, not a real semantic match — a different Meridian data pull could, in principle, re-rank channels differently (the loader re-derives the mapping each time rather than hardcoding it).
- This is **simulated data**, not a real pharma client's actual media performance — useful for demonstrating the mechanism and building a reusable pipeline, not for making a real budget call.
- Collapsing geo-level data to national totals **discards regional variation** that a real geo-level MMM would use.
- No real zero-spend weeks were present in the national aggregate (geo-level zeros smoothed out by summation) — a real vendor feed may have genuine gaps this pipeline hasn't been tested against.

## 5. Evaluation

**Tests:** 5 passing `pytest` tests — 3 on aggregation correctness (`test_aggregate.py`: a week straddling a month boundary is handled differently by `naive_monthly` vs. `correct_monthly`, and a week fully inside one month is identical either way) and 2 on the validation step (`test_spec_check.py`: a known mismatched pair is flagged, a matching pair is silent).

**Model diagnostics:** final run shows 1 divergent transition out of 4,000 posterior draws (0.025%) and no rhat/ESS warnings — a clean, trustworthy fit once sampler settings were corrected (see below).

**Results:** naive and corrected contributions were statistically indistinguishable for all three channels (overlapping 90% credible intervals), and the "digital+email vs. TV efficiency edge" moved by only ~2% between the two aggregations. However, the corrected fit's credible interval for TV (826K–13.2M) did **not** contain the known true value (16.28M) — Digital and Email's true values did fall inside their intervals. Full numbers are in `docs/findings.md`.

**Uncertainty:** credible intervals were wide across the board, reflecting real estimation difficulty from channel collinearity and a short (~37-month) series — this is itself an honest finding, not a defect to paper over.

**How mid-session updates changed the solution** (four concrete pivots, each one changing the actual answer, not just the presentation):
1. **Ground-truth generator bug found and fixed.** The first version of the synthetic sales generator centered the saturation curve too low relative to actual spend, so simulated channel contributions sat permanently near their ceiling with almost no month-to-month variation — making the signal statistically unidentifiable before any model was even fit. Fixed by centering each channel's saturation point on its own mean adstocked spend.
2. **Sampler configuration bug found and fixed.** Tuning parameters (`tune`, `target_accept`) were first passed via a `sample_kwargs` dict, which `pymc-marketing`'s own documentation says is only honored for variational inference, not MCMC — so they were silently ignored, producing ~200+ divergences and untrustworthy posteriors. Fixed by passing them as direct keyword arguments to `.fit()`, which brought divergences down to 1 in 4,000.
3. **Switch to a Bayesian library mid-design**, changing the uncertainty quantification from bootstrap resampling to proper posterior credible intervals (Section 3).
4. **Added a ground-truth recovery check to the verdict logic after reviewing the first full run.** The original verdict logic only compared naive vs. corrected aggregation to each other; once we saw that both agreed with each other but *both* missed the ground truth, we added an explicit check against the known true value, which changed the final confidence rating from "MODERATE" to "LOW" — a materially different conclusion than the first pass would have reported.

## 6. Tech Stack

| Component | Choice | Version |
|---|---|---|
| Language | Python | 3.14.2 |
| Data wrangling | pandas, numpy | — |
| Bayesian MMM | pymc-marketing (PyMC, PyTensor, ArviZ) | pymc-marketing 1.3.0, pymc 6.3.2, pytensor 3.3.7, arviz 1.3.0 |
| Charting | matplotlib | 3.11.2 |
| Testing | pytest | — |
| LLM provider | Groq (hosted inference) | — |
| LLM model | `openai/gpt-oss-20b` | OpenAI's open-weight model, served via Groq, `reasoning_effort="low"`, structured JSON-schema output |
| Secrets | python-dotenv, local `.env` (gitignored) | — |
| Base data | Google Meridian open-source sample dataset | `geo_all_channels.csv` |

No database, no web server, no R — a self-contained, runnable Python project.

## 7. Use of LLM

**Where an LLM is used:** exactly one place — `validate/spec_check.py` / `llm_backend.py`'s `GroqBackend`, reading short vendor file-specification text (e.g., "Weekly, vendor media-buying week (Monday to Sunday)") and extracting two fields: `grain` and `calendar_convention`.

**Where it is deliberately *not* used:** data generation, aggregation, the MMM fit itself, the comparison/verdict logic, and chart/report rendering are all plain code and statistics. This was a deliberate choice, not an oversight: a quantitative business recommendation (whether a 15% budget shift holds) needs to be deterministic, reproducible, and auditable run-to-run — properties an LLM call doesn't reliably provide, and doesn't need to, since these steps are well-defined computations, not language understanding tasks.

**How it's grounded:** the model's output is constrained to a strict JSON schema with enumerated values only (`grain`: daily/weekly/monthly/unknown; `calendar_convention`: broadcast_week/calendar_month/calendar_day/unknown) — it cannot return free text, so there's nothing to parse loosely or hallucinate outside the defined categories.

**How it's evaluated:** `tests/test_spec_check.py` checks the model (or the offline fallback) correctly flags a known mismatched pair (Exhibit 1's TV vs. digital/email) and stays silent on a matching pair — a small but direct test of the exact failure mode this case is about.

**Known failures / limitations:**
- Only 2 test cases — no large benchmark of varied real-world vendor-spec phrasings has been run.
- The schema forces a single grain per source; a spec describing mixed grains (e.g., "daily data, reported monthly") would be forced into one bucket.
- No confidence score is returned, just a hard categorical pick — a wrong pick looks identical to a right one in the output.
- This is exactly why a deterministic `OfflineBackend` fallback exists alongside `GroqBackend`: a check whose entire purpose is catching an expensive mistake shouldn't itself become a silent single point of failure if the LLM call errors out or an API key is missing.

## 8. Limitations and Next Steps

**For a real deployment:**
- Replace synthetic data with real client spend/sales — the magnitude of the calendar-bug effect found here is a property of this simulation, not a guaranteed real-world finding.
- Resolve the channel-collinearity / small-sample attribution problem found in Section 5 before trusting point estimates — likely needs more months of history, informative priors, or a model structure less sensitive to correlated media spend.
- Replace manual sampler tuning with automated convergence gating: a refresh whose posterior shows divergences or rhat/ESS warnings should fail the pipeline, not just print a warning.

**Data privacy and security:**
- No patient-level or PII data is involved anywhere in this pipeline — only campaign-level spend/sales aggregates — which keeps HIPAA exposure low, though pharma marketing performance data can still be commercially sensitive and should be handled under normal confidentiality terms.
- The `GROQ_API_KEY` is kept out of version control via `.gitignore` and loaded from a local `.env` file; a real deployment should use a managed secrets store instead of a local file.
- The LLM step sends only short vendor *file-spec descriptions* externally (never spend/sales figures) — before sending any real vendor contract or file-spec text to a third-party API in production, confirm that Groq's data handling terms meet the client's data processing requirements.

**Monitoring for real deployment:**
- The vendor-spec validation step should run automatically on every data refresh and **alert** (e.g., page/email the data team) rather than just print flags to a console.
- Periodically spot-check the LLM backend's extracted fields against ground truth to catch silent drift if the provider changes the underlying model.
- Track model convergence diagnostics (divergence count, rhat, ESS) per refresh as a standing metric, not a one-off check.
- Re-run the naive-vs-corrected comparison every quarter as a standing control, not a one-time investigation — a future quarter's data could show the calendar bug mattering even if this one didn't.

## 9. Submission Index

| File | Purpose | How to run |
|---|---|---|
| `case3_solution/requirements.txt` | Python dependencies | `pip install -r requirements.txt` |
| `case3_solution/.env` *(not committed, gitignored)* | Holds `GROQ_API_KEY` | Create locally; see `.gitignore` |
| `case3_solution/data/load_base.py` | Pulls and reshapes the Meridian base dataset | `python data/load_base.py` (prints an overview) |
| `case3_solution/data/synth_sales.py` | Synthesizes ground-truth monthly sales | `python data/synth_sales.py` |
| `case3_solution/aggregate.py` | Naive vs. correct TV week→month aggregation | imported by other modules; tested in `tests/test_aggregate.py` |
| `case3_solution/model.py` | Bayesian MMM fit (adstock + saturation) via `pymc-marketing` | `python model.py` (standalone smoke test) |
| `case3_solution/compare.py` | Naive vs. corrected vs. ground-truth comparison and verdict | `python compare.py` |
| `case3_solution/validate/llm_backend.py` | `OfflineBackend` / `GroqBackend` for spec extraction | imported by `spec_check.py` |
| `case3_solution/validate/spec_check.py` | Vendor file-spec validation (grain/calendar mismatch flags) | `python validate/spec_check.py` |
| `case3_solution/report/build_report.py` | Builds `report.html` (chart + verdict + flags) | `python report/build_report.py` |
| `case3_solution/report/build_slides.py` | Builds `slides.html` (8-slide deck) | `python report/build_slides.py` |
| `case3_solution/report/report.html` | Generated HTML report (output) | open in any browser |
| `case3_solution/report/slides.html` | Generated 8-slide deck (output); arrow keys/buttons to navigate | open in any browser |
| `case3_solution/run.py` | **Recommended entry point** — runs the full pipeline once and writes both outputs | `python run.py` |
| `case3_solution/tests/test_aggregate.py` | Aggregation correctness tests | `python -m pytest tests/` |
| `case3_solution/tests/test_spec_check.py` | Validation-step tests | `python -m pytest tests/` |
| `case3_solution/docs/case-study.md` | Transcribed case prompt (Exhibits 1 & 2, the solutioning task) | reference only |
| `case3_solution/docs/explanation.md` | Plain-language walkthrough of the root cause and business impact | reference only |
| `case3_solution/docs/dataset.md` | Base dataset documentation and limitations | reference only |
| `case3_solution/docs/workflow.md` | Architecture, pipeline, and key design decisions with reasoning | reference only |
| `case3_solution/docs/implementation-plan.md` | Tech stack, file layout, module details, test plan | reference only |
| `case3_solution/docs/findings.md` | Actual results from running the pipeline | reference only |
| `case3_solution/docs/solution.md` | This document | reference only |

**Quickest path to reproduce everything:**
```
cd case3_solution
pip install -r requirements.txt
python -m pytest tests/        # 5 tests, a few seconds
python run.py                  # full pipeline, ~3-4 minutes (two MCMC fits)
# then open report/report.html and report/slides.html in a browser
```
