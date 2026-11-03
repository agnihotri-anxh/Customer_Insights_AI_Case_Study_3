# Case 3 Solutioning Task — Workflow & Architecture

This documents the build plan for the actual "solutioning task" in `case-study.md`: proving whether the calendar-mismatch bug changes the 15% TV→digital/email reallocation, and building a pipeline that prevents it recurring.

## Pipeline / Flow (simplified)

```
1. data/load_base.py    → pull Google Meridian's open-source sample dataset (weekly,
                           multi-channel spend) as a realistic base spend series
2. data/synth_sales.py  → using that base spend, synthesize ~2yrs of monthly sales from
                           DECLARED true per-channel effects (adstock + saturation),
                           so we have a ground truth to check the model against later
3. aggregate.py         → naive_monthly(): buckets each Mon–Sun TV week into whichever
                             month it starts in
                           correct_monthly(): splits a week's spend across the actual
                             calendar days it covers, pro-rated into each month touched
4. model.py             → wraps a Bayesian MMM library (adstock + saturation built in)
                           fit() on the naive dataset and the corrected dataset →
                           posterior channel-contribution estimates + credible intervals
5. compare.py           → naive vs. corrected contributions vs. the KNOWN ground truth
                           from step 2 → states whether the 15% TV→digital/email call
                           still holds, and how confident we are
6. validate/spec_check.py → feeds vendor file specs (text) to an LLM-backed checker
                             (pluggable: offline default + real-API option), extracts
                             grain + calendar convention per source, flags mismatches
                       → report.html (before/after chart) + optional ≤8-slide deck
```

This drops the separate hand-rolled `mmm/transform.py` / `mmm/fit.py` / `uncertainty.py` modules from the earlier draft — a Bayesian MMM library now owns adstock, saturation, and uncertainty estimation in one place (`model.py`), so there's one fit call per aggregation instead of three custom pieces to maintain.

## Key Decisions

### 1. MMM implementation — Bayesian library, not hand-rolled
We fit the model with **`pymc-marketing`** (PyMC-based Bayesian MMM library) instead of writing our own regression + bootstrap code.
**Why:** it ships adstock and saturation transforms as ready-made components built exactly for this use case, and its Bayesian posterior gives proper credible intervals "for free" instead of us implementing bootstrap resampling by hand. It's Python-native and lighter to install than Meridian's own modeling stack (TensorFlow Probability + JAX), so we get Bayesian rigor without inheriting Meridian's heaviest dependencies.
**Why not use Meridian's own model too, since we're already using its data:** Meridian's dataset is just a CSV/dataframe we read — using it doesn't require installing Meridian's modeling engine. Keeping the data source and the modeling library decoupled means we only carry one heavy dependency (`pymc-marketing`), not two.

### 2. LLM validation step — pluggable interface
The vendor-spec checker calls an LLM through a small interface with a working offline/deterministic default, swappable for a real API call (e.g. Claude) when a key is available.
**Why:** keeps the deliverable runnable out of the box with no API key or cost, while still demonstrating the real mechanism the case asks for ("use an LLM to read vendor file specifications").

### 3. Data source — Google Meridian's open-source sample dataset
We use Meridian's bundled sample dataset as the base weekly channel-spend series, rather than Robyn's `dt_simulated_weekly` or a fully from-scratch generator.
**Why Meridian over Robyn:** Meridian is Python-native (its sample data is plain dataframes/CSV), so it drops straight into our Python pipeline. Robyn is R-native — its demo dataset lives inside an R package's data files, which would require either an R environment or hunting down a mirrored CSV just to read it. Since our whole pipeline is Python, Meridian removes an unnecessary cross-language step.
**Why not skip public data entirely:** using a real, published MMM sample dataset makes the TV/digital/email spend shapes (seasonality, scale, correlation) realistic rather than arbitrary noise — closer to what an actual client's data looks like, which matters for a credible before/after story.
**The hybrid part:** Meridian's dataset gives us realistic *spend* series, but no public dataset publishes the "true" channel effects — those are themselves estimated, not ground truth. So we keep Meridian's spend data as-is, and layer our own **declared, known** per-channel true effects on top to synthesize the *sales* response (step 2 above). That's what lets us later prove, objectively, that the corrected calendar aggregation recovers the true effect better than the naive one — a real dataset alone couldn't give us that proof.

### 4. Why TV stays weekly, digital/email go monthly
This mirrors Exhibit 1 exactly: Meridian's base data is weekly for all channels, so we keep TV at native weekly grain (to run both aggregation treatments on) and deliberately downsample digital/email to monthly ourselves — reproducing the real-world asymmetry described in the case rather than inventing an artificial one.

## Requirements Coverage Check

Cross-checked against `case-study.md` (Exhibits 1 & 2, the 5-point solutioning task, and the collaterals) and `explanation.md`:

| Case requirement | Covered by |
|---|---|
| Synthetic weekly TV / monthly digital / monthly email / monthly sales, ≥2yrs, known true effect per channel — *or* adapt a public MMM sample dataset | Both at once: step 1 adapts Meridian's public data, step 2 synthesizes sales from our own declared true effects — satisfies the "known ground truth" requirement that a pure public dataset can't. |
| Reproduce the error: naive vs. correct TV week→month aggregation | `aggregate.py` — `naive_monthly()` / `correct_monthly()` |
| Fit a simple MMM (adstock + saturation) on both, compare with uncertainty intervals | `model.py` via `pymc-marketing`, run once per aggregation, posterior credible intervals |
| State whether the 15% reallocation still holds, and confidence | `compare.py` — checks naive vs. corrected vs. ground truth |
| Data-validation step checking grain/calendar alignment, LLM-read vendor specs | `validate/spec_check.py`, pluggable LLM interface |
| Exhibit 1 (TV=weekly broadcast week, digital/email=calendar month) | Reflected directly in step 3's two aggregation functions and in how step 1 sources TV vs. digital/email grain |
| Exhibit 2 (TV 22% / Digital 19% / Email 11% "high efficiency") | Target calibration check in `compare.py`: tune declared true effects/noise so the *naive* aggregation's output qualitatively resembles Exhibit 2's pattern (email over-credited), tying the synthetic run back to the case narrative |
| Collaterals: runnable code, data generator, validation tests, HTML before/after view, optional ≤8-slide deck | `tests/` + `report/build_report.py`; slide deck last, optional |

Nothing in the case is currently uncovered.

## Open / Left to Implementation
- Exact Meridian sample dataset variant/channels to pull (confirmed once we start pulling it in).
- `pymc-marketing` sampler settings (draws/chains, credible interval width — default 90%) — implementer's call unless you want a different confidence level.
- Slide deck is optional per the case; build it last, after the core pipeline and report are working.

## Next Step
See `implementation-plan.md` for the concrete tech stack, module layout, function signatures, and test plan.
