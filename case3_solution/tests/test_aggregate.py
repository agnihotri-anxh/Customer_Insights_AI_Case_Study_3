import pandas as pd

from aggregate import correct_monthly, naive_monthly


def _weekly(dates, spend):
    return pd.DataFrame({"week_start": pd.to_datetime(dates), "tv_spend": spend})


def test_naive_dumps_straddling_week_into_its_start_month():
    # Week of 2024-01-29 .. 2024-02-04 straddles Jan/Feb.
    weekly = _weekly(["2024-01-29"], [700.0])

    result = naive_monthly(weekly)

    assert result[pd.Period("2024-01", "M")] == 700.0
    assert pd.Period("2024-02", "M") not in result.index


def test_correct_splits_straddling_week_by_day_count():
    # 3 days in January, 4 days in February -> 300 / 400 of 700.
    weekly = _weekly(["2024-01-29"], [700.0])

    result = correct_monthly(weekly)

    assert result[pd.Period("2024-01", "M")] == 300.0
    assert result[pd.Period("2024-02", "M")] == 400.0


def test_week_fully_inside_one_month_is_identical_both_ways():
    weekly = _weekly(["2024-03-04"], [490.0])

    naive = naive_monthly(weekly)
    correct = correct_monthly(weekly)

    assert naive[pd.Period("2024-03", "M")] == 490.0
    assert correct[pd.Period("2024-03", "M")] == 490.0
