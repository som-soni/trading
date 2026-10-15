# App notes moved out of learn-bases

## Intro — "Where this shows up in the app"

**Where this shows up in the app.** The `minervini` strategy finds bases with
the code in `scripts/swing_screener/core/vcp_spec.py`. The `chart_pattern`
strategy recognises named bases (cup, flat base, double bottom, flag,
triangle) with `core/chart_patterns.py`. Both show their rules on the
Strategies page. The Stage 2 screen (Screens → Stage 2 — Trend Template)
lists the stocks in which a base is *worth* watching.

## §2 Trend Template

The Trend Template (the Stage 2 screen, conditions M1–M8) defines Stage 2 by
fixed rules: ...

## §2 Base count

The
backtest records the count (`base_no`; the `--max-base` option limits trades
to early bases).

## §5 Step 1

Its
  industry group is not weak (the app's group-strength study found that
  strength in the group helps).

## §7 How this app measures a base

The `minervini` strategy turns the description above into exact rules. They
are in `core/vcp_spec.py` and documented on the Strategies page:

- **Base high** — the most recent confirmed swing high that no *decisive*
  close has cleared. A swing high here is a bar whose high is above the 5 bars
  on either side. It is only known 5 bars later, so the rule uses no
  hindsight. To end the base, a close must clear the base high by about one
  ATR. A base's ceiling is a zone, not an exact line, so a close just barely
  above it does not count.
- **Prior advance** — the base high is at least 30% above the low of the 126
  sessions before it.
- **Length** — 15 to 325 sessions (about 3 to 65 weeks).
- **Trend through the base** — the full Trend Template passes on the day of
  the base high, and the moving averages stay in the right order every day.
  (The close may dip slightly under the 200-day, because a deep first
  contraction can legitimately do that.)
- **Base number** — 1 + the number of earlier bases in the same stock that
  produced a setup since the trend last broke. The count resets when the
  moving averages are out of order for 20 sessions in a row.

The tightness and volume steps are the VCP rules — see
[learn-vcp.md](learn-vcp.md).

(The general, non-app parts of this — a swing high known only N bars later, a ceiling as a zone, the 30% / 126-session
prior advance, the reset rule — are kept in the guide in general words under "Measuring a base by rule".)

## §8 Evidence — the project's own backtests (removed; work in progress)

- **This project's backtests found no reliable edge** from bases detected by
  rule on daily data, in either market, from 2010 — see
  [minervini-spec-sensitivity-india.md](minervini-spec-sensitivity-india.md),
  [minervini-spec-sensitivity-us.md](minervini-spec-sensitivity-us.md) and the
  record of tests in [momentum-trend-research.md](momentum-trend-research.md).
  Strict definitions find very few complete bases. Loose ones find many that
  fail.
- **Context mattered more than shape.** Skipping stocks in weak industry
  groups improved the earlier Minervini version's results in both markets.
  The market's direction matters too: most breakouts fail in a weak market.

So: learn to *see* bases. They organise when you act and where your stop
goes. But judge any system that trades them by its backtest, not by how good
the chart looks.
