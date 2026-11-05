# Minervini: a bottoming pilot in the market filter, and exits by trade type

Two ideas from Minervini's bear-market webinar ([creator notes](creator-mark-minervini.md) §2.1–2.3, §6, §7),
tested as **optimise-stage** (2013-01-01 → 2021-12-31) variants of the `minervini` strategy (`minervini_spec.py`),
US and India. No verify run. Status: **measured (optimise stage only); no variant passes in both markets, so no default change is proposed** (§6). The switches are committed as 1.46, all off.

## 1. The ideas

1. **Probe at the low.** The best setups come before and at the market low, and you cannot know the low, so "default
   to the stocks": buy a few names small, and add only as they work (§2.3). The repo's market filter is binary: no new
   buys while it is risk-off, full size once it is on. The variant makes it three-state: **off / pilot / on**.
2. **Sell a trade, hold a leader.** He scales out of "tradable" moves (PBF) and holds true leaders for the bigger move
   (§7). Today EX-04 sells a third (0.33) at +2R on every trade. The variant takes that part only when the company
   fails SEPA's growth tests on the trade's own date.

His selection claim ("stocks that fell least lead") is out of scope: [Relative strength](learn-price-rs.md) §4.3
contradicts it.

## 2. What was built (1.46: three research switches, all off)

All are module constants of `minervini_spec.py`, in `signal_exempt_consts` (evaluate() never reads them), documented in
`param_docs`, and default to 1.45's behaviour. Adding them moved the fingerprint, so the strategy is **1.46** with
`signal_version = "1.45"`: spec id `v1.46-961900a3`, signal id `v1.45-s06f396ba` (unchanged), so every variant reuses
1.45's cached signal rows instead of rescanning.

| Constant | Default | Meaning |
|---|---|---|
| `MKT_PILOT` | 0 | 0 = binary gate. 1 / 2 = while the gate is risk-off, buy at `PE_PILOT_FRAC` (0.5) of the risk budget when a bottoming signal is present; full size only once the existing test holds |
| `MKT_FTD_LOW_DAYS` | 50 | (1) the rally attempt starts from the lowest close of this many sessions |
| `MKT_FTD_MIN_DAY` | 4 | (1) earliest day of the attempt that can follow through |
| `MKT_FTD_MIN_GAIN_PCT` | 1.0 | (1) benchmark up at least this %, on volume above the previous session's |
| `MKT_PILOT_BREADTH_DAYS` | 10 | (2) breadth (share of the most-traded stocks above their 50-day) higher than this many sessions earlier |
| `MKT_FILTER` | 1 | 0 = no market filter at all — the control (the queue cannot drop `--market-filter` from `backtest_args`) |
| `PARTIAL_BY_SEPA` | 0 | 1 = the +2R part only from WEAK or NO DATA companies (ACCEPTABLE / LEADER hold to the trend exit); 2 = only WEAK |

**Where.** `backtesting/spec.py`: `market_ok` returns, in pilot mode, a float series — 1.0 on, 0.5 pilot, 0.0 off —
which every yes/no reader still reads correctly; `follow_through` and `pilot_signal` are the two bottoming signals.
`backtesting/portfolio_sim.py`: a fill on a pilot session is sized at `min(progressive-exposure size, 0.5)` and tagged
`mkt_pilot` in trades.csv; `ExitPolicy.partial_by_sepa` / `_holds_for_trend` skip the +2R part by the trade's recorded
SEPA verdict. A smoke test on synthetic prices confirmed both (pilot fill 49 shares against 99; a LEADER keeps all its
shares at +2R under mode 1, a NO DATA company only under mode 2).

**Definitions and choices.**

- **Follow-through day** ([Distribution days and the follow-through day](learn-health-distribution.md) §4): day 1 is
  the first up close after the lowest close of the last 50 sessions; a follow-through is day 4 or later, up ≥ 1.0% on
  higher volume. It stays in force until a close below the attempt's low (failed) or until the full test holds
  (consumed — a later risk-off needs a new one). The 1.0% threshold is the task's; the Learn guide measured 1.25% and
  1.7%. On SPY it reproduces the guide's dates (6 Apr 2020, 24 Jun 2022).
- **India's benchmark has no stored volume on ~40–55% of 2020–21 sessions** (including the COVID low). There the price
  test alone decides; 4 of India's 30 follow-throughs in 2013–2021 were judged that way (31 Mar 2020 among them).
- **Breadth pilot**: any risk-off session with breadth higher than 10 sessions earlier — the index below its 50-day,
  and also the index above a still-falling 50-day. No breadth stored that day: no pilot.
- **Order timing**: a resting buy-stop reads the previous session's state (as the risk-off cancel already does); a
  close order reads its own session's close.
- **What `PARTIAL_BY_SEPA` leaves alone**: the breakeven stop at +2R (EX-03), the strength sale 25% above
  the 50-day and the climax part (EX-04/05) still apply to every trade.
- **`MKT_CONFIRM_DAYS` (5) is not applied by a default run.** It acts only with `--mkt-confirm`, which `backtest_args`
  does not pass, so "the existing risk-on test" here is the unconfirmed one.

## 3. Before the runs

**How much of the calendar each gate opens** (% of sessions, 2013–2021):

| US | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | all |
|---|---|---|---|---|---|---|---|---|---|---|
| On (full) | 83 | 71 | 34 | 50 | 90 | 45 | 67 | 65 | 82 | 65.0 |
| Pilot: follow-through | 4 | 6 | 20 | 11 | 0 | 22 | 16 | 16 | 2 | 10.7 |
| Pilot: breadth | 4 | 8 | 29 | 25 | 1 | 25 | 15 | 17 | 4 | 14.3 |

| India | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | all |
|---|---|---|---|---|---|---|---|---|---|---|
| On (full) | 32 | 79 | 30 | 56 | 79 | 29 | 38 | 62 | 72 | 52.8 |
| Pilot: follow-through | 19 | 2 | 39 | 18 | 7 | 15 | 19 | 20 | 5 | 16.0 |
| Pilot: breadth | 33 | 4 | 32 | 21 | 9 | 30 | 22 | 18 | 9 | 19.8 |

Follow-throughs in the window: 25 (US), 30 (India). The pilot opens most in the choppy years (2015, 2016, 2018), which
is exactly where the filter earned its keep — the test is whether half-size buys there cost more than the early
entries into recoveries (2016, 2019, 2020) return.

**How many trades the exit variant can touch.** On the last stored optimise runs (1.41), trades by SEPA verdict, and
those that sold a part (any part: +2R, strength or climax):

| | WEAK | NO DATA | ACCEPTABLE | LEADER |
|---|---|---|---|---|
| US, trades | 449 | 225 | 95 | 30 |
| US, sold a part | 44 | 26 | 6 | 5 |
| India, trades | 112 | 102 | 24 | 10 |
| India, sold a part | 32 | 24 | 11 | 2 |

Mode 1 can change at most ~11 US and ~13 Indian trades; mode 2 adds the NO DATA ones (~26 / ~24). **Expect a small
effect either way**: the strategy mostly buys companies its own fundamental tests rate WEAK.

**Pass criteria, fixed before the runs.** A variant is "clearly better" only if, against the 1.46 default (= 1.45
rules) of the same market, it has a **higher CAGR and a shallower max drawdown in both markets**, with expectancy
not lower. Differences under 0.3 points of CAGR or 1 point of drawdown are ties. Better in one market only → reported,
no default change proposed. These are optimise-stage numbers: in-sample, never a verdict.

## 4. Runs (job queue, `--stage optimise`)

| | Default | Filter off | Pilot: FTD | Pilot: breadth | Partial by SEPA 1 | Partial by SEPA 2 |
|---|---|---|---|---|---|---|
| US | #1084 | #1108 | #1109 | #1110 | #1111 | #1112 |
| India | #1086 | #1113 | #1114 | #1115 | #1116 | #1117 |

`#1084` / `#1086` were already queued (as plain `--strategies minervini`); they now run as 1.46 with no switch on,
i.e. 1.45's rules. Every variant is `--const NAME=VALUE` on top.

## 5. Results

All twelve runs are optimise-stage (2013-01-01 → 2021-12-31), spec 1.46. The default ran with every switch off, which
is 1.45's rules. CAGR and max drawdown come from `equity.csv`. Expectancy is the mean R per trade, and profit factor is
gross win ÷ gross loss, both from `trades.csv`. **In-sample numbers, not a verdict on any rule.**

| Market | Variant | CAGR | Max DD | Exp. R | PF | Trades | Pilot trades (exp. R) |
|---|---|---|---|---|---|---|---|
| US | default (1.45 rules) | −0.82% | −25.3% | +0.002 | 0.96 | 1,031 | — |
| US | filter off | +0.66% | −28.4% | +0.008 | 1.03 | 1,350 | — |
| US | pilot: follow-through | **+1.86%** | **−19.5%** | +0.045 | 1.09 | 1,104 | 180 (+0.104) |
| US | pilot: breadth | −0.30% | −24.8% | +0.007 | 0.99 | 1,202 | 250 (−0.013) |
| US | partial by SEPA 1 | −0.09% | −23.4% | +0.016 | 1.00 | 1,007 | — |
| US | partial by SEPA 2 | +0.33% | −22.3% | +0.019 | 1.02 | 1,005 | — |
| India | default (1.45 rules) | +3.65% | −14.1% | +0.158 | 1.40 | 328 | — |
| India | filter off | **+6.19%** | −15.1% | +0.157 | 1.55 | 481 | — |
| India | pilot: follow-through | +3.08% | −17.5% | +0.118 | 1.29 | 412 | 97 (+0.065) |
| India | pilot: breadth | +5.38% | −19.6% | +0.152 | 1.50 | 444 | 133 (+0.091) |
| India | partial by SEPA 1 | +3.65% | −14.1% | +0.165 | 1.40 | 328 | — |
| India | partial by SEPA 2 | +3.47% | −14.7% | +0.159 | 1.38 | 328 | — |

### 5.1 Year by year (% return on equity)

| US | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| Default | 18.2 | −7.7 | −7.2 | −1.8 | 19.2 | −6.1 | −6.3 | −1.2 | −10.2 |
| Filter off | 19.0 | −8.0 | −10.8 | −5.1 | 20.1 | −12.5 | 0.8 | 8.8 | −0.6 |
| Pilot: follow-through | 25.2 | −2.8 | −5.9 | −1.6 | 25.1 | −7.9 | 5.2 | −4.6 | −8.6 |
| Pilot: breadth | 18.9 | −6.2 | −12.7 | −3.2 | 20.2 | −5.6 | 0.1 | −0.3 | −8.9 |
| Partial by SEPA 2 | 17.9 | −7.0 | −6.5 | −1.4 | 27.2 | −6.0 | −6.7 | 0.9 | −8.6 |

| India | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| Default | 0.8 | −2.0 | 1.9 | −3.6 | 13.5 | −0.3 | −2.3 | 4.2 | 23.0 |
| Filter off | 0.8 | −1.2 | −3.3 | −7.6 | 17.4 | 8.9 | −4.7 | 22.9 | 26.5 |
| Pilot: follow-through | 2.3 | −1.2 | −3.1 | −7.0 | 14.2 | −0.3 | −6.4 | 10.8 | 21.0 |
| Pilot: breadth | 1.1 | −1.1 | −2.0 | −7.7 | 38.5 | −2.1 | −2.8 | 9.8 | 20.9 |

**The pilot trades by year** (count, total R):

| | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|---|---|---|
| US, follow-through | 15, +11.9 | 4, +0.4 | 51, −5.8 | 17, −1.8 | — | 31, −2.1 | 53, +18.5 | 8, −3.4 | 1, +1.0 |
| US, breadth | 19, +13.0 | 9, −1.5 | 75, −21.6 | 30, −3.4 | 5, +3.7 | 43, −3.3 | 52, +13.7 | 7, −2.7 | 10, −1.2 |
| India, follow-through | 10, +2.4 | 2, +1.8 | 29, −10.6 | 8, −4.6 | 12, +13.9 | 13, −0.7 | 15, −6.4 | 7, +10.3 | 1, +0.1 |
| India, breadth | 15, 0.0 | 5, −0.9 | 29, −8.9 | 13, −7.1 | 10, +13.5 | 28, +2.7 | 16, +4.2 | 6, +11.4 | 11, −2.7 |

**Partial by SEPA, the trades it changes.** Mode 1 lets ACCEPTABLE and LEADER companies skip the part sale; mode 2
adds NO DATA. US mode 1: those 146 trades made +13.7R, against +7.9R for the default's 139 trades with the same
verdicts. US mode 2: 423 trades, +26.5R against +0.9R. India: 73 trades, +10.1R against +7.8R (mode 1); 134 trades,
+12.7R against +12.5R (mode 2). Most of the US gain landed in 2017 (+6 to +8 points of return over the default).

## 6. Verdict

Judged by the criteria fixed in §3: a higher CAGR **and** a shallower max drawdown in both markets, expectancy not
lower, with gaps under 0.3 points of CAGR or 1 point of drawdown counted as ties.

| Variant | US | India | Passes? |
|---|---|---|---|
| Pilot: follow-through | Better: +2.7 pts CAGR, 5.8 pts shallower | Worse: −0.6 pts, 3.4 pts deeper, expectancy −0.04R | **No** |
| Pilot: breadth | Better CAGR (+0.5); drawdown a tie | Higher CAGR (+1.7) but 5.5 pts deeper | **No** |
| Partial by SEPA 1 | Better: +0.7 pts, 1.9 pts shallower | Tie (identical CAGR and drawdown, +0.007R) | **No** (tie in India) |
| Partial by SEPA 2 | Better: +1.2 pts, 3.0 pts shallower | Tie (−0.2 pts, 0.6 pts deeper) | **No** (tie in India) |
| Filter off | Higher CAGR (+1.5), 3.1 pts deeper | Higher CAGR (+2.5), 1.0 pt deeper | Not a candidate (control) |

**No variant passes, so no default change, version bump or changelog text is proposed.** Every switch stays off.

What the runs say, read with that caveat:

1. **The follow-through pilot is a US-only result, and a narrow one.** Its edge comes from two years: 2013 (+11.9R)
   and 2019 (+18.5R). Pilot trades lost in 2015, 2016, 2018 and 2020. In India the same rule loses: the 2015, 2016
   and 2019 pilots cost more than 2017 and 2020 returned. One market and two years is not a rule.
2. **Breadth turning up is too loose a bottoming signal.** It opens 14–20% of the calendar and buys every choppy
   spell. US 2015 alone cost −21.6R. India's higher CAGR comes almost all from 2017 (38.5% against 13.5%) and arrives
   with a 5.5-point deeper drawdown.
3. **Holding leaders to the trend exit helps in the US and does nothing in India.** In India, too few trades
   (73–134, by verdict) reach +2R to matter. In the US most of the gain is 2017, a strong trending year. A version
   tied to stronger evidence — say, LEADER only, or with the strength sale (EX-04b) also skipped — is the natural
   next variant. It would still need India to agree.
4. **In this window the filter costs return in both markets.** Turning it off raised CAGR (US −0.8% → +0.7%, India
   3.7% → 6.2%) and deepened drawdown (3.1 and 1.0 points). Earlier measurements were made on full 2010–2026 runs
   under older versions; there, only the filter improved both return and drawdown. That is not what 2013–2021 shows
   under 1.46. The trade-off is real, and the filter now reads as a drawdown control that costs return, not a free
   lunch. That changes no rule, but it is worth knowing before the filter is tuned further.

Next steps, if any are taken: a narrower US follow-through variant must not be tuned on these years and then called
verified. Test it on India first as an independent check; as with every rule here, verify once per version.
