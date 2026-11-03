"""Render a single static HTML report: a before/after channel-contribution
chart (naive vs. corrected vs. ground truth, with credible intervals), the
plain-language verdict from compare.py, and the vendor-spec validation flags
from spec_check.py.
"""

import base64
import io
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "validate"))

from compare import ROLE_LABELS, compare_runs  # noqa: E402
from load_base import pull_meridian_sample  # noqa: E402
from model import CHANNEL_COLUMNS  # noqa: E402
from spec_check import check_specs, default_backend  # noqa: E402
from synth_sales import generate_true_sales  # noqa: E402

# Exhibit 1, phrased as vendor file specs - the same input spec_check.py's
# own __main__ block uses, kept here too so the report is self-contained.
EXHIBIT_1_SPECS = {
    "TV / media spend": "Weekly, vendor media-buying week (Monday to Sunday)",
    "Digital / email spend": "Monthly, calendar month",
    "Sales data": "Monthly, calendar month",
}


def _chart_png_base64(result: dict) -> str:
    labels = [ROLE_LABELS[c] for c in CHANNEL_COLUMNS]

    def err_bars(fit_key: str):
        means = [result[fit_key][c]["mean"] for c in CHANNEL_COLUMNS]
        lo = [means[i] - result[fit_key][c]["low"] for i, c in enumerate(CHANNEL_COLUMNS)]
        hi = [result[fit_key][c]["high"] - means[i] for i, c in enumerate(CHANNEL_COLUMNS)]
        return means, [lo, hi]

    naive_means, naive_err = err_bars("naive_fit")
    correct_means, correct_err = err_bars("correct_fit")
    truth = [result["ground_truth"][c] for c in CHANNEL_COLUMNS]

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width, naive_means, width, yerr=naive_err, capsize=4, label="Naive aggregation")
    ax.bar(x, correct_means, width, yerr=correct_err, capsize=4, label="Corrected aggregation")
    ax.bar(x + width, truth, width, label="Ground truth", color="gray", alpha=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Total contribution to sales (period total)")
    ax.set_title(
        "Channel Contributions: Naive vs. Corrected vs. Ground Truth\n"
        "(error bars = 90% credible interval)"
    )
    ax.legend()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _flags_html(flags: list) -> str:
    if not flags:
        return "<p>No mismatches flagged.</p>"
    items = "".join(f"<li>{f.sources[0]} vs. {f.sources[1]}: {f.reason}</li>" for f in flags)
    return f"<ul>{items}</ul>"


def build_report(result: dict, flags: list, backend_name: str, output_path: Path) -> None:
    chart_b64 = _chart_png_base64(result)
    v = result["verdict"]
    confidence_color = {"LOW": "#c0392b", "MODERATE": "#f39c12", "HIGH": "#27ae60"}.get(
        v["confidence"], "#888"
    )

    rows = ""
    for c in CHANNEL_COLUMNS:
        label = ROLE_LABELS[c]
        n, k, t = result["naive_fit"][c], result["correct_fit"][c], result["ground_truth"][c]
        rows += (
            f"<tr><td>{label}</td>"
            f"<td>{n['mean']:,.0f} [{n['low']:,.0f}, {n['high']:,.0f}]</td>"
            f"<td>{k['mean']:,.0f} [{k['low']:,.0f}, {k['high']:,.0f}]</td>"
            f"<td>{t:,.0f}</td></tr>"
        )

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Case 3: The Two Calendars - Findings</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px;
          margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; line-height: 1.5; }}
  h1, h2 {{ color: #111; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: #f5f5f5; }}
  .verdict {{ padding: 1rem; border-left: 4px solid {confidence_color}; background: #fafafa; }}
  .confidence {{ font-weight: bold; }}
  img {{ max-width: 100%; }}
  .flags {{ background: #fff8e1; padding: 1rem; border-left: 4px solid #f39c12; }}
</style>
</head>
<body>
<h1>Case 3: The Two Calendars &mdash; Solutioning Report</h1>
<p>Does the calendar-mismatch bug change the 15% TV-to-digital/email reallocation, and how confident are we?</p>

<h2>Channel Contributions</h2>
<img src="data:image/png;base64,{chart_b64}" alt="Channel contributions chart: naive vs corrected vs ground truth">

<table>
<tr><th>Channel</th><th>Naive (90% CI)</th><th>Corrected (90% CI)</th><th>Ground truth</th></tr>
{rows}
</table>

<h2>Verdict</h2>
<div class="verdict">
<p>{v["headline"]}</p>
<p class="confidence">Confidence: {v["confidence"]}</p>
<p>Naive digital+email-vs-TV efficiency edge: {v["naive_digital_email_vs_tv_edge"]:.3f}</p>
<p>Corrected digital+email-vs-TV efficiency edge: {v["correct_digital_email_vs_tv_edge"]:.3f}</p>
<p>Edge inflated by the naive aggregation: {v["edge_inflated_by_naive_pct"]:.1f}%</p>
</div>

<h2>Vendor Spec Validation (backend: {backend_name})</h2>
<div class="flags">
{_flags_html(flags)}
</div>

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

    output_path = Path(__file__).resolve().parent / "report.html"
    build_report(result, flags, type(backend).__name__, output_path)
    print(f"Report written to {output_path}")
