"""Pull Google Meridian's open-source simulated dataset and shape it into a
national weekly TV / Digital / Email spend series for Case 3.
"""

from pathlib import Path

import pandas as pd

MERIDIAN_CSV_URL = (
    "https://raw.githubusercontent.com/google/meridian/refs/heads/main/"
    "meridian/data/simulated_data/csv/geo_all_channels.csv"
)
RAW_CACHE_PATH = Path(__file__).parent / "raw" / "geo_all_channels.csv"

SPEND_COLUMNS = [f"Channel{i}_spend" for i in range(5)]


def _fetch_raw() -> pd.DataFrame:
    """Read the Meridian sample CSV, caching a local copy on first use."""
    if RAW_CACHE_PATH.exists():
        return pd.read_csv(RAW_CACHE_PATH, index_col=0)

    df = pd.read_csv(MERIDIAN_CSV_URL, index_col=0)
    RAW_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_CACHE_PATH)
    return df


def pull_meridian_sample() -> pd.DataFrame:
    """Return a tidy national weekly DataFrame with tv_spend, digital_spend,
    email_spend columns, derived from Meridian's geo-level simulated data.

    Channel assignment: the channel with the largest total spend becomes
    "tv" (TV is typically the dominant line item in a pharma media mix);
    the next two largest become "digital" and "email".
    """
    raw = _fetch_raw()
    raw["time"] = pd.to_datetime(raw["time"])

    national = raw.groupby("time")[SPEND_COLUMNS].sum().sort_index()

    ranked_channels = national.sum().sort_values(ascending=False).index.tolist()
    tv_col, digital_col, email_col = ranked_channels[:3]

    out = pd.DataFrame({
        "week_start": national.index,
        "tv_spend": national[tv_col].values,
        "digital_spend": national[digital_col].values,
        "email_spend": national[email_col].values,
    }).reset_index(drop=True)

    out.attrs["channel_mapping"] = {
        "tv": tv_col,
        "digital": digital_col,
        "email": email_col,
    }
    return out


def overview(df: pd.DataFrame) -> str:
    """Build a short human-readable summary of the loaded dataset."""
    mapping = df.attrs.get("channel_mapping", {})
    lines = [
        f"Weeks: {len(df)} ({df['week_start'].min().date()} to {df['week_start'].max().date()})",
        f"Channel mapping: tv={mapping.get('tv')}, digital={mapping.get('digital')}, email={mapping.get('email')}",
        "",
        "Total spend by role:",
        f"  TV:      {df['tv_spend'].sum():,.0f}",
        f"  Digital: {df['digital_spend'].sum():,.0f}",
        f"  Email:   {df['email_spend'].sum():,.0f}",
        "",
        "Zero-spend weeks by role (data is simulated and sparse in places):",
        f"  TV:      {(df['tv_spend'] == 0).sum()}",
        f"  Digital: {(df['digital_spend'] == 0).sum()}",
        f"  Email:   {(df['email_spend'] == 0).sum()}",
        "",
        "describe():",
        df[["tv_spend", "digital_spend", "email_spend"]].describe().to_string(),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    data = pull_meridian_sample()
    print(overview(data))
