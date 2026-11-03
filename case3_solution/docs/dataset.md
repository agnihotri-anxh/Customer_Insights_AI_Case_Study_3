# Base Dataset: Google Meridian Simulated Sample Data

## Source

- **File:** `geo_all_channels.csv`
- **URL:** `https://raw.githubusercontent.com/google/meridian/refs/heads/main/meridian/data/simulated_data/csv/geo_all_channels.csv`
- Ships with Google's open-source [Meridian](https://github.com/google/meridian) MMM library as its own getting-started sample data. It is **simulated**, not real client data — exactly the kind of public MMM sample data the case's "Data pointers" section names as adaptable.

See `workflow.md` for why this dataset (vs. Robyn's) was chosen.

## Raw Structure

- **Grain:** weekly, **geo-level** (many regions: `Geo0`, `Geo1`, ... at least a dozen+)
- **Date range:** 2021-01-25 to 2024-01-15 (156 weeks ≈ 3 years per geo)
- **Columns:**
  - `geo`, `time`
  - 5 paid channels `Channel0`–`Channel4`, each with `_impression` and `_spend`
  - `Organic_channel0_impression` (organic/earned media)
  - `Promo` (non-media treatment variable)
  - `competitor_sales_control`, `sentiment_score_control` (control variables)
  - `conversions` (the KPI Meridian's own tutorial models), `revenue_per_conversion`
  - `population` (per-geo)

Channels are generically named (`Channel0`–`Channel4`) — Meridian doesn't label any of them "TV," "digital," or "email." There's no real-world channel semantics baked into the file.

## What We Did With It (`data/load_base.py`)

1. **Collapsed geo to national.** Summed `_spend` (and could sum `_impression`) across all geos per week, since Case 3 is framed as a single national brand campaign, not a geo-level rollout.
2. **Assigned channel roles by spend size.** Ranked the 5 channels by total national spend and took the top 3: the largest → **TV**, the next two → **Digital** and **Email**. This isn't a semantic match (Meridian never says which channel "is" TV) — it's a deliberate, documented stand-in, chosen because TV is typically the dominant line item in a pharma media mix, matching Exhibit 2's pattern where TV (22%) is the largest contributor.
3. **Left the other columns unused for now** (`Promo`, controls, `conversions`) — not needed for this case's narrow question (does the calendar bug change the TV→digital/email attribution), though they remain available in the raw cache if a later step wants them.

## What We Got (confirmed by running `load_base.py`)

| Role | Meridian column | Total spend (156 weeks) | Weekly avg |
|---|---|---|---|
| TV | `Channel3_spend` | ~87.9M | ~564K |
| Digital | `Channel4_spend` | ~47.7M | ~306K |
| Email | `Channel0_spend` | ~40.5M | ~260K |

- 156 weeks, 2021-01-25 → 2024-01-15 — exceeds the case's "at least two years" requirement.
- **No zero-spend weeks** for any of the three roles at the national level (even though individual geos have plenty of zeros — summing across geos smooths that out), so we have clean, continuous series with no gaps to patch.
- TV spend is roughly ~2x digital or email — a realistic "TV-dominant, smaller-digital/email" starting mix to layer the calendar bug and the 15% reallocation scenario onto.

## Caveat

The exact channel-to-role mapping (`Channel3`→TV etc.) is a byproduct of this dataset's random generation and isn't a stable "fact" — rerunning the loader against a different/updated copy of the CSV could, in principle, re-rank channels differently. `load_base.py` always re-derives the mapping by spend rank rather than hardcoding column names, so this stays correct even if the mapping shifts.
