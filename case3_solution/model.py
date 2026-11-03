"""Fit a Bayesian MMM (adstock + saturation) via pymc-marketing and return
each channel's total contribution to the target over the whole period, with
a credible interval - run once per TV aggregation (naive vs. correct).
"""

import numpy as np
import pandas as pd
from pymc_marketing.mmm import MMM, GeometricAdstock, LogisticSaturation

CHANNEL_COLUMNS = ["tv_spend", "digital_spend", "email_spend"]


def fit_mmm(
    monthly_df: pd.DataFrame,
    target_column: str = "sales",
    month_column: str = "month",
    draws: int = 1000,
    chains: int = 4,
    tune: int = 2000,
    target_accept: float = 0.97,
    credible_interval: float = 0.90,
    random_seed: int = 42,
) -> dict:
    """Fit the MMM on monthly_df and return, per channel, its total
    contribution to the target summed over the whole period:
    {"mean": ..., "low": ..., "high": ...}. The fitted MMM object is
    returned under the "_model" key for further inspection.
    """
    data = monthly_df[[month_column, target_column, *CHANNEL_COLUMNS]].copy()
    data["date"] = pd.PeriodIndex(data[month_column], freq="M").to_timestamp()

    mmm = MMM(
        date_column="date",
        channel_columns=CHANNEL_COLUMNS,
        target_column=target_column,
        adstock=GeometricAdstock(l_max=3),
        saturation=LogisticSaturation(),
    )

    mmm.fit(
        X=data[["date", *CHANNEL_COLUMNS]],
        y=data[target_column],
        random_seed=random_seed,
        progressbar=False,
        draws=draws,
        chains=chains,
        tune=tune,
        target_accept=target_accept,
    )

    posterior = mmm.compute_counterfactual_contributions_dataset(period="all_time")

    lower_q = (1 - credible_interval) / 2
    upper_q = 1 - lower_q

    result = {"_model": mmm}
    for channel in CHANNEL_COLUMNS:
        values = np.asarray(posterior[channel].values).flatten()
        result[channel] = {
            "mean": float(values.mean()),
            "low": float(np.quantile(values, lower_q)),
            "high": float(np.quantile(values, upper_q)),
        }
    return result


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent / "data"))
    from load_base import pull_meridian_sample  # noqa: E402
    from synth_sales import generate_true_sales  # noqa: E402

    base = pull_meridian_sample()
    synthetic = generate_true_sales(base)

    print("Fitting MMM on the (correctly aggregated) synthetic dataset...")
    fit = fit_mmm(synthetic)

    for channel in CHANNEL_COLUMNS:
        r = fit[channel]
        print(f"{channel}: mean={r['mean']:,.0f}  90% CI=[{r['low']:,.0f}, {r['high']:,.0f}]")
