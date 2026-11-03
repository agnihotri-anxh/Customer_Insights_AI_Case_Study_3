"""Data-validation step: check grain and calendar alignment across vendor
file specs on every refresh. Uses GroqBackend (a real LLM) when
GROQ_API_KEY is set, falling back to OfflineBackend otherwise - same
interface either way, so nothing downstream cares which one ran.
"""

import os
from dataclasses import dataclass

from llm_backend import GroqBackend, OfflineBackend


@dataclass
class Flag:
    sources: tuple[str, str]
    reason: str


def default_backend():
    if os.environ.get("GROQ_API_KEY"):
        try:
            return GroqBackend()
        except Exception:
            pass
    return OfflineBackend()


def check_specs(vendor_specs: dict[str, str], backend=None) -> list[Flag]:
    """vendor_specs: {source_name: spec_text}. Returns a Flag for every pair
    of sources whose grain or calendar convention don't match.
    """
    backend = backend or default_backend()
    extracted = [backend.extract(name, text) for name, text in vendor_specs.items()]

    flags = []
    for i, a in enumerate(extracted):
        for b in extracted[i + 1 :]:
            if a.grain != b.grain:
                flags.append(
                    Flag((a.source, b.source), f"grain mismatch: {a.grain} vs {b.grain}")
                )
            if a.calendar_convention != b.calendar_convention:
                flags.append(
                    Flag(
                        (a.source, b.source),
                        f"calendar convention mismatch: "
                        f"{a.calendar_convention} vs {b.calendar_convention}",
                    )
                )
    return flags


if __name__ == "__main__":
    # Exhibit 1, phrased as vendor file specs.
    EXHIBIT_1_SPECS = {
        "TV / media spend": "Weekly, vendor media-buying week (Monday to Sunday)",
        "Digital / email spend": "Monthly, calendar month",
        "Sales data": "Monthly, calendar month",
    }

    backend = default_backend()
    print(f"Using backend: {type(backend).__name__}")

    flags = check_specs(EXHIBIT_1_SPECS, backend=backend)
    if not flags:
        print("No mismatches flagged.")
    else:
        for f in flags:
            print(f"FLAG {f.sources}: {f.reason}")
