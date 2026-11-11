# Strategy family review briefs

Eight briefs, one thread each under **1.1 Strategies** (start each from the module's main thread). Each
thread reviews its family's strategies with `/backtest-review`, one strategy at a time, and ends with the
family's improvement plan. Paste the common part and the family's own section as the first message.

---

## Common part (paste with every family)

> **Goal: refine these strategies until they capture the edge their methods are known for** — not to
> retire them. For each strategy below, run `/backtest-review http://localhost:8000/#/strategies/<key>`
> in turn. Lead with step 4 of the skill, the fidelity check: where does the code differ from the method
> as its originator teaches it, and which differences most plausibly cost the edge? For a method with a
> strong documented record, treat "no edge as built" as an implementation gap until a faithful version
> has been tested.
>
> After the last strategy, write the family summary:
> 1. **The family's best version today** — which strategy (or which combination of their rules) is the
>    closest to a working edge, and why.
> 2. **The improvement plan**, ranked across the family: the fidelity gaps to close and the evidence-led
>    changes, each with its pass criteria fixed before any run, the optimise-stage commands, and whether
>    it needs code (version bump, changelog, docs per CLAUDE.md).
> 3. **Shared fixes** — a gap common to several strategies (e.g. the same missing market filter) is
>    proposed once, for the family.
> 4. **The paper-trading gate** for the family's best version.
>
> Rules: optimise stage only (2013–2021); never read verify runs beyond their verdict; analysis and plan
> only — no code edits, no queued jobs, no commits until I approve the plan. Save the family summary to
> `research/strategy-review-<family>.md`.

---

## 1. Base breakouts

Strategies: `minervini`, `minervini_coil`, `breakout`, `darvas`, `chart_pattern`, `delivery_breakout`.

Methods to check against: Mark Minervini's SEPA — the Trend Template, VCP and pivot buy point, his
fundamentals (earnings and sales acceleration), market-direction rules, and his sell rules, position
sizing and progressive exposure (*Trade Like a Stock Market Wizard*, *Think & Trade Like a Champion*;
`research/minervini-backtest-spec.md`); William O'Neil's CAN SLIM bases and pivots; Nicolas Darvas's box
method; classical chart patterns as Thomas Bulkowski and Peter Brandt describe them. Focus: Minervini
first — what a faithful SEPA implementation needs that this one lacks.

## 2. Momentum bursts

Strategies: `kullamagi`, `momentum_burst`.

Methods: Kristjan Kullamägi's breakouts and episodic pivots (opening-range entries, stop at the day's
low, partial sells into strength, trailing on the 10/20-day, market conditions); Pradeep Bonde's
(Stockbee) momentum bursts. Note what daily bars cannot capture (intraday entries) and how best to
approximate it.

## 3. Trend pullbacks and stages

Strategies: `stage_analysis`, `trend_pullback`, `ema_pullback`, `ema100_trend`, `supertrend`, `kell_cycle`.

Methods: Stan Weinstein's stage analysis (*Secrets for Profiting in Bull and Bear Markets*: the 30-week
average, Stage 2 breakouts, relative strength, volume); Oliver Kell's cycle of price action; standard
pullback-to-moving-average methods; the weekly + daily 100 EMA trade from the video notes
(`research/video-strategy-notes.md`).

## 4. Trend following

Strategies: `donchian`, `turtle_trend`, `ma_trend`.

Methods: the Turtle rules (Curtis Faith, *Way of the Turtle*: channel entries, ATR sizing in units,
pyramiding, 2N stops, diversification across markets); Richard Donchian's channel breakouts; Mebane
Faber's moving-average timing (*A Quantitative Approach to Tactical Asset Allocation*). Trend following
relies on diversification and fat tails — check the universe and sizing match.

## 5. Portfolio momentum (the family with a verified edge)

Strategies: `quality_momentum`, `momentum_vol_scaled`, `momentum_dual_combo`, `dual_momentum`,
`momentum_baseline`, `rs_leaders`, `sector_rotation`.

Methods: cross-sectional momentum (Jegadeesh & Titman), volatility-managed momentum (Barroso &
Santa-Clara), Gary Antonacci's dual momentum, quality + momentum combinations, O'Neil-style RS leaders,
sector rotation. Several already show an out-of-sample edge: the aim here is robustness, costs, capacity
and the paper-trading gate — protect what works before changing it.

## 6. Earnings events

Strategies: `pead`, `earnings_gaps`.

Methods: post-earnings-announcement drift (Ball & Brown; Bernard & Thomas — surprise measured against
expectations, drift over the following weeks); earnings gaps and episodic pivots (Bonde, Kullamägi).
Check how the surprise and the event date are measured point in time.

## 7. Shorts and mean reversion

Strategies: `mean_reversion`, `stage4_shorts`, `parabolic_short`.

Methods: Larry Connors's short-term mean reversion (RSI(2) on indices and ETFs, above the 200-day);
Weinstein's Stage 4 shorts; Kullamägi's parabolic shorts. These are often hedges more than standalone
earners — judge them also on what they add to a long book.

## 8. Special situations

Strategies: `masonson_tqqq`, `etf_swing`, `fno_income`.

Methods: the source each strategy's `thesis` cites (Masonson's TQQQ timing and sector RS rotation; ETF
swing rules; option-income structures — put spreads and ratio spreads as described in the video notes
and option-selling practice). Check the data each needs is stored point in time (e.g. option chains).
