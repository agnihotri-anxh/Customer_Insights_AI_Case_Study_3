"""Two ways to turn weekly TV spend into monthly TV spend - the bug and the fix.

naive_monthly() reproduces the vendor's broadcast-week-to-month rollup
(Exhibit 1's bug); correct_monthly() apportions each week's spend across the
calendar days it actually spans.
"""

import pandas as pd


def naive_monthly(
    weekly: pd.DataFrame, date_col: str = "week_start", value_col: str = "tv_spend"
) -> pd.Series:
    """Bucket each week into whichever month its start date falls in."""
    df = weekly[[date_col, value_col]].copy()
    df["month"] = df[date_col].dt.to_period("M")
    return df.groupby("month")[value_col].sum()


def correct_monthly(
    weekly: pd.DataFrame, date_col: str = "week_start", value_col: str = "tv_spend"
) -> pd.Series:
    """Split each week's spend across the calendar days it spans, proportional
    to how many of those days fall in each month.
    """
    rows = []
    for _, row in weekly.iterrows():
        week_start = row[date_col]
        week_days = pd.date_range(week_start, periods=7, freq="D")
        per_day = row[value_col] / len(week_days)
        for day in week_days:
            rows.append((day.to_period("M"), per_day))
    daily = pd.DataFrame(rows, columns=["month", "spend"])
    return daily.groupby("month")["spend"].sum()
