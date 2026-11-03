# Case 3 — Actual Findings (from running the pipeline)

This records what the built pipeline (`case3_solution/`) actually produced, answering the case's question #4: *does the 15% TV-to-digital/email reallocation still hold, and how confident are we?*

## Channel Contributions (total over ~37 months, 90% credible interval)

| Channel | Naive aggregation | Corrected aggregation | Ground truth |
|---|---|---|---|
| TV | 6.31M [0.82M, 14.05M] | 6.27M [0.83M, 13.21M] | 16.28M |
| Digital | 11.01M [3.32M, 19.64M] | 11.45M [4.20M, 20.26M] | 10.36M |
| Email | 10.53M [4.06M, 17.52M] | 10.48M [3.89M, 17.14M] | 4.44M |

## Verdict (two separate findings, not one)

**1. On this synthetic dataset, the calendar bug specifically does *not* flip the reallocation call.** Naive and corrected aggregation produce statistically indistinguishable contributions for all three channels (credible intervals overlap heavily), and the "digital+email vs. TV efficiency edge" barely moves (6.83 naive vs. 6.98 corrected, a ~2% difference). If this were the only check we ran, we'd say the 15% TV→digital/email shift is **robust** to the calendar fix.

**2. But that's not the same as the recommendation being trustworthy.** Even the *corrected* fit's 90% credible interval misses the known true TV contribution (16.28M true vs. a fitted interval topping out at 13.2M) — Digital and Email's true values do fall inside their intervals, but TV's doesn't. That means there's a **second, independent problem**: the model isn't reliably recovering true effects even once the calendar is fixed, most likely because the three channels are correlated with each other in this dataset and there are only ~37 months to separate their effects. The calendar fix alone does not make this attribution trustworthy.

**Overall confidence: LOW.** Not because the calendar bug was the root cause here, but because a second, unresolved reliability issue (channel collinearity / small sample) means the underlying attribution shouldn't be presented as solid even after the calendar fix — the headline recommendation needs more data or a more carefully specified model before it's safe to stand behind at the Q3 presentation.

## Why this result is still useful (even though "the bug" wasn't the dominant effect here)

This is an honest result, not a predetermined one — the code wasn't tuned to produce a specific conclusion. The value of this exercise isn't "prove the calendar bug is always the problem," it's **building the actual check**: a repeatable pipeline that fits both aggregations and reports a verdict with real uncertainty, every quarter, so whichever problem is present (calendar misalignment, collinearity, or both) gets caught before a number reaches the Brand Director. In a different quarter, or with a larger true calendar-boundary effect, this same pipeline could just as easily show the bug *does* flip the call — that's exactly why it needs to run on every refresh, not be a one-time check.

## Caveats

- Based on one synthetic dataset, one random seed, and declared true effects we chose (see `workflow.md`/`implementation-plan.md`) — the *size* of the calendar-bug effect here is a property of this particular simulation, not a universal fact about MMMs.
- 1 divergent sample out of 4,000 draws (0.025%) — negligible, not a sign of an unreliable fit.
- The TV-truth-miss is a known, named limitation (channel collinearity, small sample) rather than an unexplained gap — worth investigating further (e.g. more months of data, or priors/model structure that reduce collinearity sensitivity) before trusting point estimates from this exact model.
