# Case 3: The Two Calendars

An FDE-associate case study: an MMM recommended shifting 15% of TV budget into digital and email. Weekly totals then stopped matching the calendar — traced to TV spend being reported on a Monday–Sunday broadcast week while digital, email, and sales are reported on calendar months. This repo builds the actual check: does that calendar bug change the reallocation call, and how confident are we either way?

**Verdict:** on this run, the calendar bug alone does **not** flip the recommendation — but the corrected model still misses the known true TV contribution, pointing to a second, independent reliability problem (channel collinearity / limited data). Overall confidence: **LOW**. Full writeup in [`case3_solution/docs/solution.md`](case3_solution/docs/solution.md).

## Quick Start

```bash
cd case3_solution
pip install -r requirements.txt
python -m pytest tests/        # 5 tests, a few seconds
python run.py                  # full pipeline, ~3-4 minutes (two Bayesian MMM fits)
```

Then open `case3_solution/report/report.html` (findings) and `case3_solution/report/slides.html` (8-slide summary, arrow keys to navigate) in a browser.

Optional: add a `GROQ_API_KEY` to `case3_solution/.env` to run the vendor-spec validation step against a real LLM (`openai/gpt-oss-20b` via Groq); without it, a deterministic offline backend is used instead — same interface either way.

## Project Structure

```
case3_solution/
  data/            synthetic data generator + public base dataset loader
  aggregate.py     naive vs. correct TV week->month aggregation (the bug and the fix)
  model.py         Bayesian MMM (adstock + saturation) via pymc-marketing
  compare.py       naive vs. corrected vs. ground-truth comparison and verdict
  validate/        LLM-backed (+ offline fallback) vendor file-spec validation
  report/          HTML report + 8-slide deck generators and their output
  tests/           pytest suite
  run.py           runs the full pipeline end to end
  docs/            case study, methodology, dataset notes, findings, full solution doc
```

## Documentation

| Doc | Contents |
|---|---|
| [`docs/case-study.md`](case3_solution/docs/case-study.md) | The case prompt as given (Exhibits 1 & 2, the solutioning task) |
| [`docs/explanation.md`](case3_solution/docs/explanation.md) | Plain-language walkthrough of the root cause and business impact |
| [`docs/dataset.md`](case3_solution/docs/dataset.md) | Base dataset (Google Meridian sample data) and its limitations |
| [`docs/workflow.md`](case3_solution/docs/workflow.md) | Architecture, pipeline, and key design decisions with reasoning |
| [`docs/implementation-plan.md`](case3_solution/docs/implementation-plan.md) | Tech stack, file layout, module details, test plan |
| [`docs/findings.md`](case3_solution/docs/findings.md) | Actual results from running the pipeline |
| [`docs/solution.md`](case3_solution/docs/solution.md) | Full solution document: overview, methodology, alternatives considered, evaluation, LLM usage, limitations, submission index |

## Tech Stack

Python 3.11+ · pandas / numpy · `pymc-marketing` (Bayesian MMM) · matplotlib · pytest · Groq (`openai/gpt-oss-20b`) for the LLM validation step · base data from [Google Meridian](https://github.com/google/meridian)'s open-source sample dataset.
