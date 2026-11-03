# Case 3: The Two Calendars

**Your role:** FDE associate on the account
**Domain:** Pharma, diabetes, marketing mix modelling

## Key Terms

| Term | Meaning |
|---|---|
| Marketing mix modelling (MMM) | Statistical model estimating each channel's contribution to sales, used to decide spend. |
| Broadcast / media calendar | Weeks always run Monday to Sunday, grouped into 4–5 week quarters; does not line up with calendar months. |
| Attribution | Giving credit for a sale to the marketing activity that most likely caused it. |
| Lift | Extra effect of an activity above what would have happened anyway. |

## Situation

Six months ago your team built an MMM for a mid-size diabetes brand. Its latest recommendation moved 15% of TV spend into digital and email, presented to their VP as data-backed, and it has been implemented. Three weeks into the quarterly refresh, you notice some weekly totals differ slightly from what the calendar suggests. The Brand Director presents Q3 results in 10 days, and the TV-to-digital calendar shift is the headline.

> Note: the source photo of this paragraph is rotated/partially obscured; the sentence order above is reconstructed to read coherently. If you have the original sheet, double-check this section against it.

## Exhibit 1: Data Source Notes (vendor file specification)

| Data source | Field notes |
|---|---|
| TV / media spend | Weekly, vendor media-buying week (Monday to Sunday) |
| Digital / email spend | Monthly, calendar month |
| *(third row — source label cut off in photo)* | Monthly, calendar month |

> The photo is cropped at the bottom-left of this table, so the data source name for the third row isn't legible. It reports on calendar months like digital/email. If you have the original sheet, fill this in (likely candidates given the case: sales data / Rx data).

## Exhibit 2: Model Output Excerpt (prior quarter)

| Channel | Estimated contribution to sales |
|---|---|
| TV | 22% |
| Digital | 19% |
| Email | 11% (flagged "high efficiency" in the reallocation memo) |

## Your Solutioning Task

Find out whether the calendar mismatch changes the recommendation the client has already acted on, and build a pipeline that prevents it from happening again.

### Your solution should:

1. Generate synthetic weekly TV spend, monthly digital spend, and monthly email spend, and monthly sales for at least two years, with a known true effect per channel. Alternatively, adapt a public MMM sample dataset.
2. Reproduce the error: aggregate TV weeks to months the naive way, then correctly by apportioning each week's spend across days and calendar months.
3. Fit a simple MMM (adstock and saturation, with any library or your own code) on both versions and compare channel contributions with uncertainty intervals.
4. State whether the 15% TV-to-digital reallocation still holds, and how confident you are.
5. Build a data-validation step that checks grain and calendar alignment on every refresh. Use an LLM to read vendor file specifications and show how you verify what it flags, and flag calendar or grain assumptions.

### Collaterals to submit

Runnable code, the data generator, validation tests, an HTML before-and-after view of channel contributions, and an optional slide deck of 8 slides or fewer.

### Data pointers

Synthetic generation is expected. The simulated weekly dataset shipped with Meta's open-source Robyn MMM package, or the sample data in Google's open-source Meridian MMM package, can be adapted.

> The photo of this page is a phone shot of a flipped page at an angle — line order above is reconstructed to read coherently. If anything here looks off against your original sheet, flag it and I'll correct it.
