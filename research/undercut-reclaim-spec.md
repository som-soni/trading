# Undercut and reclaim — a strategy spec

*Status: **draft 0, 2026-11-17; built the same day as strategy `undercut_reclaim` v1.0** (§7). The definitions
below were fixed before any backtest. A first version was checked against stored prices for how often it fires,
and changed once because of that check (§3). No outcomes were looked at, and no backtest has been run.*

**In short**

- From four diagrams by @ohiain on X ([creator note](creator-ohiain.md)): in a leader's base, **don't buy the
  obvious breakout of the pivot. Buy when price undercuts the base's support and reclaims it**, with the stop
  under the undercut low. A second entry comes at the break of the first bounce's high, after a higher low.
- The claim to test is a **trade-off**. The reclaim entry is far cheaper in risk than the breakout: median stop
  2.6–3.2%, and the base's top sits a median 3.0–3.75R above. In exchange, more of its trades should fail inside
  the base.
- The check found that **a daily 21-EMA can't hold through an undercut of a six-week base**: zero cases on eight
  leaders. The trend line the undercut must hold is the **weekly 21-EMA**, approximated here by the 100-day EMA.
  The 9/21-day EMAs govern the exit.
- Pass criteria, written now: the reclaim must beat a **breakout entry on the same bases** in both markets.
  That comparison is the creator's claim, so the backtest runs both.

## 1. The method, as the diagrams show it

| Step | What happens | What they do |
|---|---|---|
| Base | An uptrend pauses in a range between a **support pivot** (tested more than once) and a **breakout pivot** | Watch. The breakout pivot is the obvious buy, and the one they avoid |
| Undercut | Price dips **under support** for a few bars and doesn't collapse | Nothing yet. Buying the fall into the level is ✗ (diagram 3) |
| Reclaim | Price closes back **above support** | **1st entry**, stop under the undercut low |
| Higher low, higher high | A bounce, a shallower pullback, then a break of the bounce's high | **2nd entry**, stop under the higher low |
| Run | Price rises through the base and the breakout pivot | Hold while the 9/21 EMAs hold |
| End | Wedge drop; 9 EMA under 21 EMA; the bounce to them fails on above-average selling volume | Out |

## 2. Definitions (fixed before any backtest)

Bars are daily. EMAs are exponential averages of the close; ATR is the 14-day Wilder ATR; "average volume" is
the 50-day average. Each number becomes a named constant. These are first guesses at the diagrams, which carry
no numbers.

| Code | Rule | Draft-0 definition |
|---|---|---|
| — | Candidates | The Trend Template screen (`stage2`), **without C1** (close above the 50-day). An undercut of a base's low often dips under the 50-day, which is the point. The other gates still apply: above the 150- and 200-day, averages stacked, 200-day rising, off the 52-week low, near the 52-week high, relative strength |
| G-base | A base | The `BASE_BARS` = 30 sessions ending `UNDERCUT_WINDOW` = 5 sessions before today. Support = its lowest low; pivot = its highest high. Height (pivot ÷ support − 1) at most `BASE_MAX_PCT` = 20% |
| G-tested | Support was tested | At least `MIN_TOUCHES` = 2 swing lows in the base (a low that is the lowest of the 2 bars either side), at least 5 sessions apart, each within `TOUCH_PCT` = 2% of support |
| G-undercut | An undercut | In the undercut window (the 5 sessions before today), the lowest low is under support, by at most `UNDERCUT_MAX_ATR` = 1.5 ATR |
| G-hold | The trend holds | No close from the start of the undercut window to today is under the 100-day EMA by more than `HOLD_ATR` = 0.5 ATR. `HOLD_SPAN` = 100 stands in for the weekly 21-EMA (21 weeks ≈ 105 sessions) |
| G-market | Market | The strategies' shared market filter |
| **S1** | Reclaim | Today is the **first close back above support** after the undercut: yesterday closed at or under it, today above it. **One S1 per base**: a second reclaim of the same support after a fresh dip is not an entry. Stop: the undercut low. Not bought if the stop is more than `MAX_STOP_PCT` = 8% under the entry |
| **S2** | Higher high after a higher low | Within `S2_WINDOW` = 15 sessions after an S1: a pullback low above the undercut low (the higher low), then a close above the highest high from the S1 day to that higher low (the bounce high). One per base. Stop: the higher low. In a stock already held from S1 it adds a tranche; otherwise it is a fresh entry |
| W1 | Volume on the reclaim | Flag only: the S1 session's volume is under its 50-day average. Diagram 1 stresses volume; diagrams 2–4 don't show it |
| W2 | Little room | Flag only: the pivot is less than 2R above the entry |
| EX | Exit | Each tranche at its stop. Then the 9/21 crossback of diagram 1: once the 9-day EMA has closed above the 21-day after the entry, the first close with the 9-day back under it sells everything at that close. No target; the pivot is the plan's nominal target, for the R column only |

## 3. Checked against stored prices (how often it fires, nothing else)

A scratch detector of the definitions, run on daily bars to 2021-12-31 (the optimise stage's end). It counts
setups only. No forward returns were computed, so no rule was chosen on outcome.

**Version 1 failed: the daily 21-EMA can't hold an undercut.** The first draft asked that no close be more than
0.5 ATR under the 21-day EMA, and that the 21-day EMA be rising. Over the full stored history of eight leaders it
found **zero** setups: NVDA, AMD, TSLA, SHOP, Bajaj Finance, Dixon, Tata Elxsi and Deepak Nitrite. The reason is
mechanical. Inside a six-week range, the 21-day EMA sits near the middle of the range, so any close under the
range's low is far under the EMA, and the EMA turns down. Diagram 2 draws the EMAs meeting the undercut low. That
only works on a slower line.

| Line the undercut must hold | 30-session base | 60-session base |
|---|---:|---:|
| 21-day EMA | 0 | 0 |
| 50-day EMA | 2 | 0 |
| **100-day EMA (≈ weekly 21-EMA)** | **20** | 0 |

*Setups on the eight leaders, trend test on the slow averages (50-day above 200-day, close above the 200-day,
200-day rising over 20 sessions). A 60-session base rarely fits under the 20% height cap in a leader.*

So the draft uses the 100-day EMA for the hold. It keeps the 9/21-day EMAs for the exit, which is where diagram 1
uses them. That matches the creator's "weekly pivot" wording.

**How often it fires.** 400 random stored symbols per market, kept if the median daily traded value over their
last year to 2021 was at least ₹50 Cr or $20 million. This gives 103 US and only 17 Indian stocks, so the India
row is thin. The counts cover each stock's history up to 2021, so they include years before 2013.

| Market | Liquid stocks | Setups (all rules) | Without G-hold | Without G-tested | Without the trend test | No gates |
|---|---:|---:|---:|---:|---:|---:|
| US | 103 | 591 | 1,341 | 762 | 642 | 4,466 |
| India | 17 | 56 | 108 | 74 | 57 | 362 |

| Market | Median stop | 90th percentile stop | Stops over 8% | Median room to pivot | 25th percentile room |
|---|---:|---:|---:|---:|---:|
| US | 2.6% | 5.9% | 3.7% | 3.0R | 2.0R |
| India | 3.2% | 6.0% | 1.8% | 3.75R | 2.5R |

Three things follow:

1. **The stops are tight.** Kell's one-bar stops of about one ATR were stopped out on 49% of US trades. Here the
   median stop is a third of the way between Kell's and an ATR-based stop. A 1-ATR floor under support is a
   fixed variant (§5).
2. **Costs matter.** India's round trip of about 27 bps is roughly 0.08R on a 3.2% stop. The backtest's costs
   must be the market's real ones.
3. **Double reclaims happen.** Bajaj Finance reclaimed the same support on 30 March and 1 April 2021. Hence
   "one S1 per base" in §2.

The trend test removes few setups (642 → 591 in the US); the hold and the tested-support rules do the work.

## 4. How a backtest would trade it (draft)

- **Universe and candidates:** §2. Liquidity is the market's usual floor (`cfg.screener.min_dollar_volume`).
- **Entries:** S1 at the signal session's close. S2 at its close, as an add while S1 is in profit and the
  position is under full size, or as a fresh entry. Each tranche is sized so that its own stop risks the
  account's risk per trade. Portfolio rules are the minervini strategy's (`--spec`), as for `kell_cycle`.
- **Exits:** §2 EX. No time stop in the base version.
- **The comparison run (`ENTRY_MODE` = 2):** the **same bases**, entered instead at the first close above the
  pivot within 30 sessions of the S1 signal. The stop is the same undercut low, capped at 8% under that entry,
  and the exits are the same. This is the "obvious breakout" of diagram 2, on exactly the setups the reclaim
  buys, so the comparison isolates the entry.

## 5. Variants, fixed now

Each runs beside the base version in the optimise stage. None is chosen as a replacement for the base because
it scored better: a winning variant becomes a new version, verified on its own.

| Variant | Change | Why |
|---|---|---|
| `ENTRY_MODE=2` | Breakout entry on the same bases (§4) | The creator's claim |
| `MIN_STOP_ATR=1.0` | Stop at least 1 ATR under the entry | Kell's tight-stop problem (§3) |
| `S2_ONLY=1` | Only the 2nd entry | Diagram 3's ✓ includes it as the more confirmed entry |
| `EXIT_MODE=2` | Kell's EMA break (close under the 21-day by 0.5 ATR) in place of the 9/21 cross | The nearer-coded exit, for comparison with `kell_cycle` |

## 6. Pass criteria for the first backtest (decided now)

Optimise stage only (2013–2021), both markets, the draft-0 definitions, nothing tuned after the first run:

1. **Enough trades:** at least 100 closed trades per market.
2. **Expectancy:** at least +0.25R a trade net of costs in each market.
3. **The claim:** the reclaim entry (base) beats the breakout entry on the same bases (`ENTRY_MODE=2`) in
   expectancy per trade **and** in CAGR, in both markets.
4. **Not one stock's result:** with the best 5% of trades removed, expectancy stays above zero in both markets.

If all four pass, the strategy gets one verify run (2022 on) with the same criteria, when the owner says so. If
any fails, the result is written here as a failure. The definitions are then revised once, as draft 1, with the
reason stated, and draft 1 gets its own run.

## 7. Open questions

- **Weekly bars.** The hold line is a daily stand-in for the weekly 21-EMA, and the base is a daily window.
  Detecting the support pivot on weekly bars may match the creator better; not in draft 0.
- **India's sample.** Only 17 of 400 random Indian symbols met the ₹50 Cr floor over the check window. The
  backtest's full universe will be larger, but India may still fall short of 100 trades. Criterion 1 then
  fails, and that is reported, not loosened.
- **Overlap.** The same day can be a `wyckoff_spring` S1 (range after a decline) or a `minervini` S9 shakeout
  (bought later, through the base's high). Report how many S1 signals coincide with either, as a diagnostic.
- **Weekly bars** aside, the build settled the remaining wording (§7).

## 7a. How it was built (2026-11-17)

Strategy `undercut_reclaim` v1.0: the scan is `core/undercut_reclaim.py`, the class `strategies/undercut_reclaim.py`.
Where the code had to settle what §2 left open:

| Point | As built |
|---|---|
| "One S1 per base" | No S1 within `REARM_BARS` = 30 sessions of the last |
| Candidates | The Trend Template's own row test with C1 dropped (`trend_template_row(..., above_50=False)`), and the minervini strategy's turnover floor |
| S2 and the breakout after an S1 | Both are watched from the S1. A close under the undercut low ends the watch |
| `MIN_STOP_ATR` | At least that many ATR under the *entry*, as in `kell_cycle` (§5 corrected) |
| Exit | A new backtest exit mode, `--exit-mode reclaim`: `kell_cycle`'s tranche machinery (each tranche's own stop, adds at the close) with no exhaustion sale, selling everything when the 9-day EMA closes under the 21-day after being at or above it the session before. EXIT_MODE 2 is a close under the 21-day EMA by 0.5 ATR |
| Plan target | The base's pivot, or entry + 3R when the pivot is not above the entry; the R column only (`--no-target`) |
| Evidence grade | D: diagrams, no published test |

## 8. Results

None yet.
