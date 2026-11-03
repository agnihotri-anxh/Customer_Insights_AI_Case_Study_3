# Case 3 Solutioning Task — Implementation Plan

Builds on `workflow.md`. This is the concrete file layout, tech stack, and what each piece does.

## Tech Stack

| Tool | Role | Why this one |
|---|---|---|
| **Python 3.11** | Whole pipeline | Everything in the stack (pymc-marketing, Meridian's sample data, pandas) is Python-native; no reason to mix languages. |
| **pandas / numpy** | Data wrangling, the two TV aggregation paths | Standard, zero-friction for weekly→monthly resampling and date-overlap math. |
| **pymc-marketing** | The Bayesian MMM itself (adstock + saturation + fit) | Ships adstock/saturation transforms and a Bayesian regression built specifically for marketing mix modeling — we configure it rather than write our own transforms, regression, and uncertainty code. Its posterior gives proper credible intervals for channel contributions out of the box. |
| **Google Meridian sample dataset** (data only, not its modeling engine) | Realistic base weekly multi-channel spend series | Python-native/pip-friendly to read as a dataframe; avoids pulling in Meridian's own TensorFlow Probability + JAX modeling stack, which we don't need since `pymc-marketing` is doing the fitting. |
| **Anthropic Claude API (optional) behind a small interface, with an offline rule-based default** | The vendor-spec validator in step 6 | Satisfies "use an LLM to read vendor file specifications" while keeping the deliverable runnable with zero setup/cost; swap in a real key when available. |
| **matplotlib / plotly → static HTML** | `report.html` before/after chart | Lightweight, no server needed, opens in any browser — matches the "HTML before-and-after view" collateral directly. |
| **pytest** | `tests/` | Standard, works well with pandas/numpy fixtures. |

No database, no web server, no R — this is a self-contained, runnable Python project.

## File Layout

```
case3_solution/
  data/
    load_base.py        # pull_meridian_sample() -> pd.DataFrame (weekly, multi-channel spend)
    synth_sales.py       # generate_true_sales(spend_df, true_effects) -> pd.Series (monthly, ground truth)
  aggregate.py            # naive_monthly(weekly_tv) / correct_monthly(weekly_tv) -> pd.Series (monthly TV spend)
  model.py                # fit_mmm(monthly_df) -> contributions dict {channel: (mean, lo, hi)}
  compare.py              # compare_runs(naive_result, correct_result, ground_truth) -> verdict dict
  validate/
    spec_check.py         # check_specs(vendor_specs: list[str]) -> list[Flag]; pluggable LLM backend
    llm_backend.py         # OfflineBackend (default) + ClaudeBackend (optional, needs ANTHROPIC_API_KEY)
  report/
    build_report.py       # renders report.html from compare.py + spec_check.py output
    build_slides.py        # optional, ≤8-slide HTML deck, built last
  tests/
    test_aggregate.py      # naive vs. correct aggregation against hand-checked small examples
    test_model.py           # fit_mmm recovers known effects within credible interval on clean synthetic data
    test_spec_check.py      # offline backend flags a deliberately mismatched grain/calendar spec
  run.py                   # orchestrates steps 1–6 end to end, writes report.html
  requirements.txt
```

## Module Details

**`data/load_base.py`**
`pull_meridian_sample()` reads Meridian's published sample dataset (weekly, ≥2 years, multiple channels) and returns a tidy `DataFrame` with at least a TV-like weekly channel. If the exact public file isn't reachable at build time, this function is the single point to swap in a locally-saved copy — nothing downstream changes.

**`data/synth_sales.py`**
`generate_true_sales(spend_df, true_effects)` applies our own declared adstock decay + saturation curve per channel to the Meridian spend series and sums with noise to produce monthly sales. `true_effects` is a plain dict of parameters we choose and document (e.g. `{"tv": 0.25, "digital": 0.15, "email": 0.08}` as the true contribution shares) — this is the ground truth everything else gets checked against.

**`aggregate.py`**
Two pure functions, same input/output shape, so `model.py` doesn't care which one fed it:
- `naive_monthly(weekly_tv)`: groups each week by the month its **start date** falls in.
- `correct_monthly(weekly_tv)`: splits each week's spend across the calendar days it actually spans, weighted by day-count in each month.

**`model.py`**
`fit_mmm(monthly_df)` configures a `pymc-marketing` `MMM` model (adstock + saturation priors), samples the posterior, and returns each channel's contribution as a `(mean, low, high)` credible interval. Called once on the naive dataset, once on the corrected dataset.

**`compare.py`**
`compare_runs(naive, correct, ground_truth)` lines up all three contribution sets, checks whether the naive run's credible interval for digital/email overlaps the corrected run's (the actual test of "does the bug change the answer"), and returns a plain verdict string plus the numbers behind it — this is what `report.html` and the slide deck quote directly.

**`validate/spec_check.py` + `llm_backend.py`**
`check_specs(vendor_specs)` takes a list of short vendor file-spec text blurbs (like Exhibit 1's rows, phrased as text), asks the active backend to extract `{source, grain, calendar_convention}` per entry, and flags any pair of sources whose grain/calendar don't match. `OfflineBackend` does this with simple keyword rules (works with no setup); `ClaudeBackend` does the same by calling the Claude API when `ANTHROPIC_API_KEY` is set — same interface, swappable at runtime via one config flag.

**`report/build_report.py`**
Renders a single static `report.html`: a bar chart of naive vs. corrected vs. ground-truth channel contributions with error bars (credible intervals), the plain-language verdict from `compare.py`, and the list of flags from `spec_check.py`.

## Test Plan

- **`test_aggregate.py`** — hand-construct a few weeks that straddle a month boundary, assert `naive_monthly` dumps the whole week into one month while `correct_monthly` splits it proportionally to the day.
- **`test_model.py`** — feed `fit_mmm` a small dataset generated directly from known `true_effects` with low noise, assert the returned credible intervals contain the true value (sanity-checks the model wiring, not full convergence).
- **`test_spec_check.py`** — give the offline backend one deliberately mismatched pair of specs (weekly vs. monthly, like Exhibit 1) and assert it's flagged; give it two matching specs and assert it's silent.

## Build Order

1. `data/load_base.py` + `data/synth_sales.py` (need real numbers before anything else makes sense)
2. `aggregate.py` + its tests
3. `model.py` + its tests (this is the slowest piece to get right — Bayesian sampler tuning)
4. `compare.py`
5. `validate/spec_check.py` + `llm_backend.py` + its tests
6. `report/build_report.py`
7. `run.py` to wire it all together
8. `report/build_slides.py` (optional, last)

## Open Items (implementer's call unless you object)
- `pymc-marketing` sampler settings: default to NUTS, 1,000 draws, 2 chains, 90% credible interval.
- Exact `true_effects` values will be chosen so the naive run's output qualitatively echoes Exhibit 2 (TV strong, email over-credited) — exact numbers tuned during step 1 of the build.
