import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validate"))

from llm_backend import OfflineBackend
from spec_check import check_specs


def test_flags_mismatched_grain_and_calendar():
    specs = {
        "TV / media spend": "Weekly, vendor media-buying week (Monday to Sunday)",
        "Digital / email spend": "Monthly, calendar month",
    }

    flags = check_specs(specs, backend=OfflineBackend())
    reasons = [f.reason for f in flags]

    assert any("grain mismatch" in r for r in reasons)
    assert any("calendar convention mismatch" in r for r in reasons)


def test_silent_when_specs_match():
    specs = {
        "Digital spend": "Monthly, calendar month",
        "Email spend": "Monthly, calendar month",
    }

    flags = check_specs(specs, backend=OfflineBackend())

    assert flags == []
