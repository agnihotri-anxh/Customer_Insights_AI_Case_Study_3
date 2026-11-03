"""Pluggable backends for reading vendor file specifications.

OfflineBackend works with zero setup (deterministic keyword rules) and is
the default. GroqBackend calls a real LLM (openai/gpt-oss-20b, served by
Groq) via structured JSON-schema output, used automatically when
GROQ_API_KEY is set.
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass
class ExtractedSpec:
    source: str
    grain: str  # "daily" | "weekly" | "monthly" | "unknown"
    calendar_convention: str  # "broadcast_week" | "calendar_month" | "calendar_day" | "unknown"


class OfflineBackend:
    """Deterministic keyword-based extraction - no network, no API key."""

    GRAIN_PATTERNS = [
        ("weekly", re.compile(r"\bweek(ly)?\b", re.IGNORECASE)),
        ("monthly", re.compile(r"\bmonth(ly)?\b", re.IGNORECASE)),
        ("daily", re.compile(r"\bdaily\b", re.IGNORECASE)),
    ]
    CALENDAR_PATTERNS = [
        (
            "broadcast_week",
            re.compile(r"monday to sunday|broadcast|media.buying week", re.IGNORECASE),
        ),
        ("calendar_month", re.compile(r"calendar month", re.IGNORECASE)),
    ]

    def extract(self, source_name: str, spec_text: str) -> ExtractedSpec:
        grain = next((g for g, pat in self.GRAIN_PATTERNS if pat.search(spec_text)), "unknown")
        convention = next(
            (c for c, pat in self.CALENDAR_PATTERNS if pat.search(spec_text)), "unknown"
        )
        return ExtractedSpec(source=source_name, grain=grain, calendar_convention=convention)


class GroqBackend:
    """Real LLM extraction via Groq's API (openai/gpt-oss-20b), using
    structured JSON-schema output so the response always matches our schema
    regardless of how the spec text is phrased.
    """

    MODEL = "openai/gpt-oss-20b"

    SCHEMA = {
        "type": "object",
        "properties": {
            "grain": {"type": "string", "enum": ["daily", "weekly", "monthly", "unknown"]},
            "calendar_convention": {
                "type": "string",
                "enum": ["broadcast_week", "calendar_month", "calendar_day", "unknown"],
            },
        },
        "required": ["grain", "calendar_convention"],
        "additionalProperties": False,
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set; use OfflineBackend instead.")
        from groq import Groq  # imported lazily so OfflineBackend needs no dependency

        self._client = Groq(api_key=self.api_key)

    def extract(self, source_name: str, spec_text: str) -> ExtractedSpec:
        response = self._client.chat.completions.create(
            model=self.MODEL,
            reasoning_effort="low",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract the reporting grain and calendar convention from a "
                        "vendor data file specification. Respond only with the "
                        "requested JSON fields."
                    ),
                },
                {"role": "user", "content": spec_text},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "vendor_spec", "schema": self.SCHEMA, "strict": True},
            },
        )
        parsed = json.loads(response.choices[0].message.content)
        return ExtractedSpec(
            source=source_name,
            grain=parsed["grain"],
            calendar_convention=parsed["calendar_convention"],
        )
