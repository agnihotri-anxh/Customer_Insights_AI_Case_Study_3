"""Compare MMM fits on naive vs. correctly aggregated TV spend, against the
known ground truth, to answer the case's core question: does the calendar
bug change the 15% TV-to-digital/email reallocation call, and how confident
are we either way?
"""

import sys
from pathlib import Path

import pandas as pd

from aggregate import correct_monthly, naive_monthly
from model import CHANNEL_COLUMNS, fit_mmm

sys.path.insert(0, str(Path(__file__).resolve().parent / "data"))

ROLE_LABELS = {"tv_spend": "TV", "digital_spend": "Digital", "email_spend": "Email"}


def build_dataset(weekly_base: pd.DataFrame, synthetic: pd.DataFrame, tv_aggregator) -> pd.DataFrame:
    """Same months, same digital/email/sales as the ground-truth run - only
    the TV column changes, built via the given aggregation method.
    """
    tv_monthly = tv_aggregator(weekly_base, value_col="tv_spend")
    months = pd.PeriodIndex(synthetic["month"], freq="M")
    df = synthetic.copy()
    df["tv_spend"] = tv_monthly.reindex(months).values
    return df.dropna(subset=["tv_spend"]).reset_index(drop=True)


def _efficiency(fit: dict, df: pd.DataFrame) -> dict:
    """Fitted mean contribution per dollar spent, per channel - mirrors
    Exhibit 2's "efficiency" framing.
    """
    return {c: fit[c]["mean"] / df[c].sum() for c in CHANNEL_COLUMNS}


def _overlaps(a: dict, b: dict) -> bool:
    return a["low"] <= b["high"] and b["low"] <= a["high"]


def _build_verdict(
    naive_fit: dict, correct_fit: dict, naive_eff: dict, correct_eff: dict, true_totals: dict
) -> dict:
    # Did any channel's credible interval move enough that naive and correct
    # no longer overlap? That's the direct test of "does the bug change the
    # answer."
    shifted = {c: not _overlaps(naive_fit[c], correct_fit[c]) for c in CHANNEL_COLUMNS}

    # Did naive aggregation make digital/email look relatively MORE efficient
    # than TV, vs. the corrected aggregation? That's the mechanism that would
    # have inflated the original reallocation case (and echoes Exhibit 2's
    # "high efficiency" flag on email).
    def relative_edge(eff: dict) -> float:
        return (eff["digital_spend"] + eff["email_spend"]) / eff["tv_spend"]

    naive_edge = relative_edge(naive_eff)
    correct_edge = relative_edge(correct_eff)
    edge_inflated_pct = (naive_edge - correct_edge) / correct_edge * 100

    any_shifted = any(shifted.values())

    if any_shifted or abs(edge_inflated_pct) > 10:
        headline = (
            "The calendar bug DOES change the picture: correcting TV's calendar "
            "alignment moves at least one channel's estimated contribution (or "
            "its efficiency relative to TV) enough that the naive numbers can't "
            "be trusted as-is. The 15% TV-to-digital/email reallocation should be "
            "RE-VALIDATED before standing behind it in the Q3 presentation."
        )
        confidence = "LOW"
    else:
        headline = (
            "The calendar bug does NOT meaningfully change the picture here: naive "
            "and corrected aggregation give statistically indistinguishable channel "
            "contributions and relative efficiency. The 15% TV-to-digital/email "
            "reallocation appears ROBUST to the calendar fix."
        )
        confidence = "MODERATE"

    # Separate from the calendar-bug question: does the CORRECTED fit even
    # recover the known true contribution? If not, there's a second,
    # independent reliability problem (e.g. channel collinearity, small
    # sample) that the calendar fix alone doesn't solve - worth saying so
    # explicitly rather than letting a "robust to the calendar fix" verdict
    # imply the number is trustworthy.
    truth_recovered = {
        c: correct_fit[c]["low"] <= true_totals[c] <= correct_fit[c]["high"]
        for c in CHANNEL_COLUMNS
    }
    if not all(truth_recovered.values()):
        missed = [ROLE_LABELS[c] for c, ok in truth_recovered.items() if not ok]
        confidence = "LOW"
        headline += (
            f" HOWEVER: even the corrected fit's credible interval misses the known "
            f"true contribution for {', '.join(missed)} - the calendar fix alone does "
            f"NOT make this attribution trustworthy. Something else (likely channel "
            f"collinearity given the limited months of data) is independently "
            f"distorting the result, and that needs fixing before this recommendation "
            f"should be presented as data-backed."
        )

    return {
        "credible_intervals_shifted": shifted,
        "naive_digital_email_vs_tv_edge": naive_edge,
        "correct_digital_email_vs_tv_edge": correct_edge,
        "edge_inflated_by_naive_pct": edge_inflated_pct,
        "truth_recovered_by_corrected_fit": truth_recovered,
        "headline": headline,
        "confidence": confidence,
    }


def compare_runs(weekly_base: pd.DataFrame, synthetic: pd.DataFrame) -> dict:
    naive_df = build_dataset(weekly_base, synthetic, naive_monthly)
    correct_df = build_dataset(weekly_base, synthetic, correct_monthly)

    naive_fit = fit_mmm(naive_df)
    correct_fit = fit_mmm(correct_df)

    true_totals = {
        "tv_spend": synthetic["true_tv_contribution"].sum(),
        "digital_spend": synthetic["true_digital_contribution"].sum(),
        "email_spend": synthetic["true_email_contribution"].sum(),
    }

    naive_eff = _efficiency(naive_fit, naive_df)
    correct_eff = _efficiency(correct_fit, correct_df)

    return {
        "naive_fit": naive_fit,
        "correct_fit": correct_fit,
        "ground_truth": true_totals,
        "naive_efficiency": naive_eff,
        "correct_efficiency": correct_eff,
        "verdict": _build_verdict(naive_fit, correct_fit, naive_eff, correct_eff, true_totals),
    }


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "data"))
    from load_base import pull_meridian_sample  # noqa: E402
    from synth_sales import generate_true_sales  # noqa: E402

    base = pull_meridian_sample()
    synthetic = generate_true_sales(base)

    print("Fitting MMM on NAIVE aggregation, then CORRECT aggregation...")
    result = compare_runs(base, synthetic)

    print()
    print("=" * 78)
    print("CHANNEL CONTRIBUTIONS (total over the period)")
    print("=" * 78)
    print(f"{'Channel':<10}{'Naive (90% CI)':<30}{'Correct (90% CI)':<30}{'Truth':<12}")
    for c in CHANNEL_COLUMNS:
        label = ROLE_LABELS[c]
        n, k, t = result["naive_fit"][c], result["correct_fit"][c], result["ground_truth"][c]
        naive_str = f"{n['mean']:,.0f} [{n['low']:,.0f}, {n['high']:,.0f}]"
        correct_str = f"{k['mean']:,.0f} [{k['low']:,.0f}, {k['high']:,.0f}]"
        print(f"{label:<10}{naive_str:<30}{correct_str:<30}{t:,.0f}")

    v = result["verdict"]
    print()
    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(v["headline"])
    print(f"Confidence: {v['confidence']}")
    print(f"Credible intervals shifted by the fix: {v['credible_intervals_shifted']}")
    print(f"Naive digital+email-vs-TV efficiency edge:   {v['naive_digital_email_vs_tv_edge']:.3f}")
    print(f"Correct digital+email-vs-TV efficiency edge: {v['correct_digital_email_vs_tv_edge']:.3f}")
    print(f"Edge inflated by the naive (bugged) aggregation: {v['edge_inflated_by_naive_pct']:.1f}%")
    print(f"Truth recovered by corrected fit's 90% CI: {v['truth_recovered_by_corrected_fit']}")
