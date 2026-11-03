# Case 3 Explained: The Two Calendars

## The concepts, in plain language

- **MMM (marketing mix modelling):** a regression-style model that looks at historical spend across channels (TV, digital, email, etc.) and sales, and estimates how much each channel contributed. Brands use it to decide where to shift budget.
- **Attribution:** once the model sees a sale, it has to decide which marketing activity "gets credit" for it. If a TV ad ran the same week as an email blast, the model has to split credit between them.
- **Lift:** not the whole sales number — just the *extra* sales caused by the activity, above the baseline that would have happened with no marketing at all.
- **Broadcast / media calendar:** the advertising industry doesn't bill or report in calendar months. It uses "broadcast weeks" — always Monday to Sunday — bundled into 4–5-4 or similar patterns to make 4–5 week "broadcast months" that roll up into quarters. These boundaries almost never match the 1st-to-30th/31st calendar month.

## The root cause

Exhibit 1 shows the actual bug: the model is built on two data sources that use **different calendars**:

- **TV/media spend** → weekly, on the **broadcast week** (Mon–Sun, bundled into broadcast quarters)
- **Digital/email spend** (and the third, partly-illegible source) → **calendar month**

An MMM needs every input lined up on the same time axis before it can estimate each channel's contribution. If TV spend is bucketed by broadcast week/quarter and digital/email spend is bucketed by calendar month, then near the edges of any month, spend from the "wrong" period bleeds across:

- A TV flight that broadcast-calendar logic places in the last few days of a broadcast period might actually fall in the *next* calendar month.
- Any sales lift that shows up in that next calendar month gets compared against digital/email spend for that same calendar month — but against TV spend for the *wrong* broadcast period.

The result: the model can misattribute TV's trailing effect to digital/email (making digital/email look more effective than it is), or vice versa. That's exactly the symptom described — "weekly totals differ slightly from what the calendar suggests" once you try to reconcile the model's view of a week against the calendar everyone else is using.

> **In simple terms:** TV spend is tracked Monday-to-Sunday; digital/email spend is tracked by plain calendar month. Those two don't line up. Imagine a TV ad that runs Fri–Sun, where that weekend spills from October into November — TV's system books the *whole week's* spend as "October." A few days later, sales bump up in early November. Since there's no TV spend recorded in November to explain it, the model looks for something else in that month to take the credit — and digital/email spend is sitting right there, in the right month, so it gets credited instead. That's why email got flagged "high efficiency": not because email is secretly great, but because some of TV's real effect kept landing in the wrong month and got miscounted as email's. It's a filing error, not a performance difference.

## Why it matters right now

The model's **headline recommendation** — shift 15% of TV spend into digital/email — was built on attribution estimates that came out of this same misaligned pipeline. If the calendar mismatch is inflating digital/email's apparent lift (or deflating TV's), the reallocation may be based on a biased comparison, not a clean one. Presenting that as the Q3 story to the Brand Director, 10 days out, risks:

- Overstating the case for digital/email's effectiveness
- Making a budget recommendation that doesn't hold up if someone re-derives the numbers on a calendar-month basis
- Losing credibility with the VP/Brand Director if the discrepancy surfaces *after* the presentation instead of before it

> **In simple terms:** The company already *acted* on this — they moved real budget from TV to digital/email based on these numbers. In 10 days, the Brand Director has to tell senior leadership (the VP) that this move is a success story. If the numbers behind that story are actually just a calendar filing error, three things can go wrong: (1) they're about to tell leadership something false, (2) someone could catch the mistake later and it reflects badly on the whole team's data once it's already been announced as fact, and (3) there's very little time left — 10 days is enough to quietly check and fix this, but not much more. In short: a real decision and a public presentation are both riding on a number that might be wrong, and the window to catch it quietly is closing.

## What to actually do about it

1. **Confirm the mismatch, quantify it.** Re-express TV spend on calendar-month boundaries (prorating broadcast weeks that straddle a month boundary by the number of days in each month) and see how much the weekly/monthly totals shift versus the current broadcast-week view. This tells you whether the discrepancy is cosmetic or large enough to move the attribution results.
2. **Re-run (or sensitivity-check) the attribution on the reconciled calendar.** If the 15% TV→digital/email shift recommendation holds up after aligning calendars, you have a stronger, defensible story. If it doesn't hold up, you've caught a real error before it reached the Brand Director.
3. **Flag it proactively, not defensively.** Before the Q3 presentation, tell the Brand Director/VP what you found: "we noticed TV and digital/email were reported on different calendars; we reconciled them and [the recommendation still holds / the recommendation changes to X]." This is a normal data-hygiene catch, not a crisis — framing it that way preserves trust in the model.
4. **Fix it upstream for future refreshes.** Standardize all vendor feeds onto one calendar convention (commonly: map everything to broadcast weeks, or everything to calendar months) as part of the MMM's data pipeline, so this doesn't recur every quarter.

> **In simple terms:**
> 1. **Check if it's really a problem, and how big.** Re-sort TV spend onto the same calendar everyone else uses — if an ad straddles two months, split its spend proportionally instead of dumping it all into one month. See how much the numbers move.
> 2. **Redo the math with the fixed numbers.** Run the model again with the corrected data. If the "move 15% to digital/email" conclusion still holds, great — you have a stronger story. If it doesn't hold, you just caught a mistake before it went public.
> 3. **Tell the Brand Director before the presentation, calmly.** Something like: "We found TV and digital/email were measured on different calendars, fixed it, and here's what the numbers say now." Framed that way, it's the team being thorough — not a screwup.
> 4. **Fix the pipeline so it can't happen again.** Make every vendor's data convert onto one standard calendar automatically before it reaches the model, so nobody has to catch this by hand next quarter.
>
> In short: measure how wrong it is → redo the numbers correctly → tell the boss before they present, not after → fix the pipeline so it's automatic going forward.

## Connecting Exhibit 2

Exhibit 2 is the model output that the 15% TV-to-digital/email reallocation was actually based on:

| Channel | Estimated contribution to sales |
|---|---|
| TV | 22% |
| Digital | 19% |
| Email | 11% (flagged "high efficiency" in the reallocation memo) |

Email being flagged "high efficiency" is the detail that should raise suspicion. If email's 11% contribution is being divided by a *smaller* reported spend than it actually had (or TV's 22% by a *larger* one) because of the calendar misalignment described above, email's apparent efficiency is inflated artificially — not because email is genuinely outperforming, but because the spend-to-sales ratio was computed on misaligned periods. That's exactly the kind of result that should make you pause before letting it drive a 15%-of-budget decision.

> **In simple terms — what each exhibit tells you, and why both matter:**
>
> - **Exhibit 1 is the *cause*.** It shows the three data feeds don't share a calendar (TV = broadcast week, digital/email = calendar month). It's the evidence that explains *why* something could be wrong — without it, you'd just be staring at a weird number with no idea where it came from.
> - **Exhibit 2 is the *effect*.** It's the actual output — TV 22% / Digital 19% / Email 11% "high efficiency" — that got turned into a real decision (the 15% budget shift). Without it, you'd know the data was mismatched but wouldn't know if it actually changed anything or mattered.
> - **Together:** Exhibit 1 tells you *where to look* for the bug; Exhibit 2 tells you *what's at stake* if you don't fix it. You use Exhibit 1 to explain why email's "high efficiency" flag is suspicious, and you use Exhibit 2 to show this isn't an abstract data-quality nitpick — it's the exact number that justified moving real marketing budget.

## The actual solutioning task

The case doesn't stop at diagnosis — it asks you to **prove whether the recommendation still holds** and **build a pipeline so this can't happen silently again**. At a high level, the asked-for solution is:

1. **Synthetic ground truth** — generate ~2 years of weekly TV spend + monthly digital/email spend + monthly sales, with a *known* true effect per channel (or adapt Robyn's or Meridian's public sample datasets), so you have a baseline to check the model against.
2. **Reproduce the bug** — aggregate the weekly TV data into months two ways: the "naive" way (just bucket each broadcast week into whichever month it nominally belongs to) and the "correct" way (apportion each week's spend across the actual calendar days it covers, splitting a week that straddles a month boundary).
3. **Fit and compare** — run a simple MMM (adstock + saturation transforms) on both versions, and compare the estimated channel contributions *with uncertainty intervals*, not just point estimates.
4. **Answer the business question** — does the 15% TV→digital/email shift still make sense once the calendars are aligned, and how confident is that conclusion (i.e., do the corrected contribution intervals for TV vs. digital/email still clearly favor the shift, or do they now overlap)?
5. **Prevent recurrence** — add a data-validation step that checks grain (weekly vs. monthly) and calendar alignment across all vendor feeds on every refresh, using an LLM to read each vendor's file specification and flag mismatched conventions automatically.

Deliverables: runnable code (data generator + validation tests), a before/after comparison of channel contributions, and optionally a short slide deck (≤8 slides) summarizing the finding for the Brand Director.

This is a real build, not just an analysis — worth treating as its own implementation task (synthetic data generator, two aggregation paths, an MMM fit, and a validation checker) rather than squeezing it into this write-up. Say the word and we can scope and build it.

## Takeaway

"The Two Calendars" is a data-alignment problem disguised as a modeling result. The lesson for an FDE associate: before trusting or presenting any cross-channel comparison from an MMM, verify every input is on the same time grid. A statistically significant-looking shift in attribution can simply be an artifact of two vendors reporting time differently.
