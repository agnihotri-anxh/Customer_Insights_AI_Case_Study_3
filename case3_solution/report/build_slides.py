"""Render an 8-slide, self-contained HTML deck summarizing the case, the
approach, and the findings - for the Brand Director, not the engineering
team. Reuses a pre-computed `result` dict (from compare.compare_runs) rather
than re-fitting the MMM, so this can run right after build_report.py without
paying for a second ~3-minute MCMC fit.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "validate"))

from compare import ROLE_LABELS, compare_runs  # noqa: E402
from load_base import pull_meridian_sample  # noqa: E402
from model import CHANNEL_COLUMNS  # noqa: E402
from spec_check import check_specs, default_backend  # noqa: E402
from synth_sales import generate_true_sales  # noqa: E402

from build_report import EXHIBIT_1_SPECS  # noqa: E402

SLIDE_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, Segoe UI, sans-serif; background: #1a1a1a; }
  .deck { width: 100%; height: 100vh; overflow: hidden; position: relative; }
  .slide {
    position: absolute; inset: 0; display: none; flex-direction: column;
    justify-content: center; padding: 4rem 6rem; background: #fff; color: #1a1a1a;
  }
  .slide.active { display: flex; }
  .slide h1 { font-size: 2.4rem; margin: 0 0 1rem; color: #111; }
  .slide h2 { font-size: 1.8rem; margin: 0 0 1.5rem; color: #111; }
  .slide p, .slide li { font-size: 1.15rem; line-height: 1.6; }
  .slide .kicker { color: #888; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; }
  .slide table { border-collapse: collapse; width: 100%; margin-top: 1rem; font-size: 1rem; }
  .slide th, .slide td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }
  .slide th { background: #f5f5f5; }
  .badge { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 999px; color: #fff; font-weight: bold; }
  .nav { position: fixed; bottom: 1.5rem; right: 1.5rem; display: flex; gap: 0.5rem; z-index: 10; }
  .nav button {
    padding: 0.5rem 1rem; border: none; border-radius: 6px; background: #333; color: #fff;
    cursor: pointer; font-size: 1rem;
  }
  .nav button:hover { background: #555; }
  .counter { position: fixed; bottom: 1.8rem; left: 1.5rem; color: #aaa; font-size: 0.9rem; }
"""

SLIDE_JS = """
  let current = 0;
  const slides = document.querySelectorAll('.slide');
  const counter = document.getElementById('counter');
  function show(i) {
    current = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((s, idx) => s.classList.toggle('active', idx === current));
    counter.textContent = (current + 1) + ' / ' + slides.length;
  }
  document.getElementById('prev').onclick = () => show(current - 1);
  document.getElementById('next').onclick = () => show(current + 1);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === ' ') show(current + 1);
    if (e.key === 'ArrowLeft') show(current - 1);
  });
  show(0);
"""


def _confidence_badge(confidence: str) -> str:
    color = {"LOW": "#c0392b", "MODERATE": "#f39c12", "HIGH": "#27ae60"}.get(confidence, "#888")
    return f'<span class="badge" style="background:{color}">{confidence} CONFIDENCE</span>'


def _contributions_table(result: dict) -> str:
    rows = ""
    for c in CHANNEL_COLUMNS:
        label = ROLE_LABELS[c]
        n, k, t = result["naive_fit"][c], result["correct_fit"][c], result["ground_truth"][c]
        rows += (
            f"<tr><td>{label}</td>"
            f"<td>{n['mean']:,.0f}</td>"
            f"<td>{k['mean']:,.0f}</td>"
            f"<td>{t:,.0f}</td></tr>"
        )
    return (
        "<table><tr><th>Channel</th><th>Naive</th><th>Corrected</th><th>Ground truth</th></tr>"
        f"{rows}</table>"
    )


def _flags_list(flags: list) -> str:
    if not flags:
        return "<p>No mismatches flagged.</p>"
    return "<ul>" + "".join(f"<li>{f.sources[0]} vs. {f.sources[1]}: {f.reason}</li>" for f in flags) + "</ul>"


def build_slides(result: dict, flags: list, backend_name: str, output_path: Path) -> None:
    v = result["verdict"]

    slides = [
        f"""
        <div class="kicker">Case 3</div>
        <h1>The Two Calendars</h1>
        <p>Does a TV-vs-digital calendar mismatch change a 15% budget reallocation call,
        and can we trust the answer?</p>
        """,
        """
        <div class="kicker">The situation</div>
        <h2>A data-backed recommendation, already acted on</h2>
        <p>An MMM recommended moving 15% of TV spend into digital and email. The client
        implemented it. Three weeks into the quarterly refresh, weekly totals stopped
        lining up with the calendar &mdash; and Q3 results are due to the Brand Director
        in 10 days, with this shift as the headline.</p>
        """,
        """
        <div class="kicker">The bug</div>
        <h2>Two data sources, two calendars</h2>
        <p>TV spend is reported on a <b>broadcast week</b> (Monday&ndash;Sunday, 4&ndash;5
        week quarters). Digital, email, and sales are reported on <b>calendar months</b>.
        Near every month boundary, TV spend can land in the wrong period relative to the
        other channels &mdash; distorting which channel gets credit for a sale.</p>
        """,
        """
        <div class="kicker">Our approach</div>
        <h2>Build the actual check, don't just diagnose it</h2>
        <ul>
          <li>Synthetic ~3-year dataset built on a real public MMM sample (Google Meridian),
              with <b>known</b> true per-channel effects as ground truth</li>
          <li>Two TV aggregations: naive (whole week into one month) vs. corrected
              (spend split proportionally across the days it spans)</li>
          <li>A Bayesian MMM (adstock + saturation, pymc-marketing) fit once per
              aggregation, with credible intervals &mdash; not just point estimates</li>
          <li>An LLM-backed check that reads vendor file specs and flags grain/calendar
              mismatches automatically, every refresh</li>
        </ul>
        """,
        f"""
        <div class="kicker">Results</div>
        <h2>Channel contributions (period total)</h2>
        {_contributions_table(result)}
        """,
        f"""
        <div class="kicker">Verdict</div>
        <h2>{_confidence_badge(v["confidence"])}</h2>
        <p>{v["headline"]}</p>
        """,
        f"""
        <div class="kicker">Validation</div>
        <h2>Vendor spec check (backend: {backend_name})</h2>
        {_flags_list(flags)}
        <p>This check now runs automatically on every data refresh &mdash; the exact
        mismatch that caused this case gets caught before it reaches a model again.</p>
        """,
        """
        <div class="kicker">Recommendation</div>
        <h2>What we'd tell the Brand Director</h2>
        <ul>
          <li>Hold the 15% reallocation story until attribution uncertainty is addressed
              &mdash; the calendar fix alone isn't enough to call this number solid</li>
          <li>More months of data, or a model structure less sensitive to channel
              collinearity, before re-presenting this as data-backed</li>
          <li>The validation pipeline now runs on every refresh going forward</li>
        </ul>
        """,
    ]

    slide_html = "".join(f'<div class="slide">{s}</div>' for s in slides)

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Case 3: The Two Calendars - Slides</title>
<style>{SLIDE_CSS}</style>
</head>
<body>
<div class="deck">
{slide_html}
</div>
<div class="nav">
  <button id="prev">&larr; Prev</button>
  <button id="next">Next &rarr;</button>
</div>
<div class="counter" id="counter"></div>
<script>{SLIDE_JS}</script>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    base = pull_meridian_sample()
    synthetic = generate_true_sales(base)

    print("Fitting MMM on naive and corrected aggregations (this takes a couple minutes)...")
    result = compare_runs(base, synthetic)

    backend = default_backend()
    flags = check_specs(EXHIBIT_1_SPECS, backend=backend)

    output_path = Path(__file__).resolve().parent / "slides.html"
    build_slides(result, flags, type(backend).__name__, output_path)
    print(f"Slides written to {output_path}")
