"""Generate monthly sales from DECLARED ground-truth per-channel effects,
using Meridian's spend series as a realistic base.

This is the only place in the pipeline where "true" effects are defined -
everything downstream (naive fit vs. corrected fit) tries to recover them.
TV's true monthly spend uses the CORRECT calendar-day apportionment, because
the real world doesn't care how a vendor's file happens to bucket weeks -
sales respond to how much was actually spent in a given month.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aggregate import correct_monthly  # noqa: E402

# Declared ground truth - tune here, nowhere else. "contribution_share" is
# the target average fraction of BASELINE_SALES that channel's saturated,
# adstocked spend should contribute. "saturation_k_factor" scales the
# saturation curve's half-point relative to that channel's own mean
# adstocked spend (1.0 = centered on the typical operating point, so spend
# swings actually move the saturated effect instead of everything sitting
# pinned near the ceiling - a channel saturating 100% of the time is both
# unrealistic and statistically unidentifiable).
TRUE_EFFECTS = {
    "tv": {"contribution_share": 0.22, "adstock_decay": 0.35, "saturation_k_factor": 1.0},
    "digital": {"contribution_share": 0.14, "adstock_decay": 0.15, "saturation_k_factor": 1.0},
    "email": {"contribution_share": 0.06, "adstock_decay": 0.05, "saturation_k_factor": 1.0},
}
BASELINE_SALES = 2_000_000
NOISE_STD_FRACTION = 0.03


def _adstock(spend: pd.Series, decay: float) -> pd.Series:
    """Geometric carryover: this month's effect = spend + decay * last month's effect."""
    out = np.zeros(len(spend))
    carry = 0.0
    for i, s in enumerate(spend.values):
        carry = s + decay * carry
        out[i] = carry
    return pd.Series(out, index=spend.index)


def _saturate(x: pd.Series, k: float) -> pd.Series:
    """Diminishing returns: approaches 1 as spend grows, half-saturated at k."""
    return 1 - np.exp(-x / k)


def _monthly_sum(weekly: pd.DataFrame, value_col: str) -> pd.Series:
    by_month = weekly.set_index(weekly["week_start"].dt.to_period("M"))[value_col]
    return by_month.groupby(level=0).sum()


def generate_true_sales(weekly_base: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Return a monthly DataFrame of tv/digital/email spend and the resulting
    synthetic sales, driven by TRUE_EFFECTS plus noise.
    """
    rng = np.random.default_rng(seed)

    tv_monthly = correct_monthly(weekly_base, value_col="tv_spend")
    digital_monthly = _monthly_sum(weekly_base, "digital_spend")
    email_monthly = _monthly_sum(weekly_base, "email_spend")

    months = tv_monthly.index.intersection(digital_monthly.index).intersection(
        email_monthly.index
    )
    tv_monthly, digital_monthly, email_monthly = (
        tv_monthly[months],
        digital_monthly[months],
        email_monthly[months],
    )

    spends = {"tv": tv_monthly, "digital": digital_monthly, "email": email_monthly}
    contributions = {}
    total_effect = pd.Series(0.0, index=months)
    for name, spend in spends.items():
        params = TRUE_EFFECTS[name]
        adstocked = _adstock(spend, params["adstock_decay"])
        k = params["saturation_k_factor"] * adstocked.mean()
        effect = _saturate(adstocked, k)
        target_avg = params["contribution_share"] * BASELINE_SALES
        scaled = effect * (target_avg / effect.mean())
        contributions[name] = scaled
        total_effect += scaled

    noise = rng.normal(0, NOISE_STD_FRACTION * BASELINE_SALES, size=len(months))
    sales = BASELINE_SALES + total_effect.values + noise

    return pd.DataFrame(
        {
            "month": months.astype(str),
            "tv_spend": tv_monthly.values,
            "digital_spend": digital_monthly.values,
            "email_spend": email_monthly.values,
            "sales": sales,
            "true_tv_contribution": contributions["tv"].values,
            "true_digital_contribution": contributions["digital"].values,
            "true_email_contribution": contributions["email"].values,
        }
    )


if __name__ == "__main__":
    from load_base import pull_meridian_sample

    base = pull_meridian_sample()
    result = generate_true_sales(base)

    print(result.head())
    print()
    print(f"Months: {len(result)}")
    print(f"Mean monthly sales: {result['sales'].mean():,.0f}")

    total_sales = result["sales"].sum()
    true_shares = {
        name: result[f"true_{name}_contribution"].sum() / total_sales
        for name in ("tv", "digital", "email")
    }
    print(f"Realized true contribution shares (of total sales): {true_shares}")
