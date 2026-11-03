"""End-to-end entry point: load data, synthesize ground truth, fit naive vs.
corrected MMMs once, validate vendor specs, and write both the HTML report
and the slide deck from that single run.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "validate"))
sys.path.insert(0, str(ROOT / "report"))

from compare import compare_runs  # noqa: E402
from load_base import pull_meridian_sample  # noqa: E402
from spec_check import check_specs, default_backend  # noqa: E402
from synth_sales import generate_true_sales  # noqa: E402

from build_report import EXHIBIT_1_SPECS, build_report  # noqa: E402
from build_slides import build_slides  # noqa: E402


def main() -> None:
    print("1/4 Loading base dataset (Meridian sample)...")
    base = pull_meridian_sample()

    print("2/4 Generating synthetic ground-truth sales...")
    synthetic = generate_true_sales(base)

    print("3/4 Fitting MMM on naive and corrected aggregations (a couple minutes)...")
    result = compare_runs(base, synthetic)

    backend = default_backend()
    flags = check_specs(EXHIBIT_1_SPECS, backend=backend)
    print(f"    Vendor-spec validation backend: {type(backend).__name__}, {len(flags)} flag(s)")

    print("4/4 Writing report.html and slides.html...")
    report_dir = ROOT / "report"
    build_report(result, flags, type(backend).__name__, report_dir / "report.html")
    build_slides(result, flags, type(backend).__name__, report_dir / "slides.html")

    v = result["verdict"]
    print()
    print(f"Verdict: {v['headline']}")
    print(f"Confidence: {v['confidence']}")
    print(f"Report:  {report_dir / 'report.html'}")
    print(f"Slides:  {report_dir / 'slides.html'}")


if __name__ == "__main__":
    main()
