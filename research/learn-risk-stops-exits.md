# Stops and exits — where a trade is wrong, and how it ends

Learning material: where a stop goes and how wide it may be, gaps through it,
and the ways a trade ends — targets, breakeven and trailing stops, trend
breaks, climax sales, time stops — measured on this app's own backtest trades.
Third of four risk guides, after [Expectancy](learn-risk-expectancy.md) and
[Position sizing](learn-risk-sizing.md); [Portfolio risk](learn-risk-portfolio.md) follows.

**Where this shows in the app.** Each strategy's stop and exit rules are on
**Strategies** (generated from `entry_rules` and `exit_rules` in
`strategies/*.py`). Backtest trade lists — columns *Initial stop*, *Exit*, *R*,
*Days held* — are on the strategy's **Backtests** tab and in **System →
Reports archive**, and the Chart page draws a run's stored trades. Exits are
simulated in `backtesting/portfolio_sim.py`.

**The data.** Each strategy's latest full run on its current version: US
`minervini` v1.6 (2010–2026, 551 closed trades), US `trend_pullback`
(2013–2026, 863), US `breakout` (703), US `donchian` (496), India
`trend_pullback` (347), India `donchian` (437), India `chart_pattern` (515);
India `minervini` only has v1.5 runs (192 trades), labelled where used. These
are **backtests with modelled costs** (slippage 5 bp a side US, 10 bp India;
the Minervini spec runs use their own charges and slippage), on today's listed
stocks (survivorship bias), each trade risking 1% of equity. R = profit ÷ money
at risk at entry; days are calendar days.

---

## 1. The stop is decided before the entry

A stop is **the price at which the reason for the trade is proven wrong**.
Decide it first, because:

- **Size comes from it**: shares = risk ÷ (entry − stop) ([sizing](learn-risk-sizing.md)).
- **It sets the reward test.** A target 2R away means something only if R is
  known; every strategy here except `donchian` refuses or downgrades a plan
  under 2R.
- **It is the only calm decision.** Once a trade is red, every reason to lower
  the stop looks good. So: **raise a stop by rule, never lower it.**

## 2. Where to put it — under structure

Put the stop **just below the level that must hold if the idea is right** —
the nearest demand ([learn-supply-demand.md](learn-supply-demand.md)): a swing
low, a base's tight area, the pattern's low — plus a small buffer.

| Strategy | Initial stop | Limits |
|---|---|---|
| `minervini` | 0.5% under the base's tight low (cheat entries: under the shelf low) | Fill skipped if the stop is more than **8%** below it |
| `trend_pullback` | Pullback low − 0.1 ATR (TC-01) or 10-bar low − 0.1 ATR (TC-02) | HIGH CONFIDENCE needs ≤ 3 ATR and ≤ 12%; beyond 3.5 ATR or 15% is WATCH |
| `breakout` | Low of the 20 prior bars − 0.1 ATR, never more than 2 ATR below entry | Over 8% is WATCH; HIGH CONFIDENCE needs ≤ 7% |
| `chart_pattern` | Under the pattern's invalidation level, no wider than 2 ATR, no tighter than 0.6 ATR or 1.5% | Over 8% is rejected as a trade |
| `donchian` | The lower of entry − 2 ATR(14) and entry − 2% | None; no minimum R |

Four are *structural* stops with a volatility ceiling; `donchian`'s is pure
volatility.

## 3. How wide may a stop be?

Minervini aims for losses averaging 6–7% and an absolute maximum near 10%
(*Trade Like a Stock Market Wizard*); O'Neil's rule is 7–8%. The app's
Minervini strategy uses **8%** (`MAX_STOP_PCT` in
`strategies/minervini_spec.py`, rule SL-03), and `breakout` and
`chart_pattern` will not trade a stop wider than 8%. Sizing already makes each
loss 1R; the cap is about **what a wide stop says** — a base whose support is
12% away is loose, and loose bases fail more. In the US Minervini run the cap
skipped 68 fills.

Median initial stops: US `minervini` 5.5%, `trend_pullback` and `breakout`
4.8%, `donchian` 7.4%; India `trend_pullback` 6.3%, `chart_pattern` 6.2%,
`donchian` 8.9% — India runs wider for the same rules, as its mid and small
caps move more per day.

## 4. Too tight against too wide — measured

By initial stop distance (stopped = share closed by the initial stop; days =
median held):

| Stop | US `donchian` stopped · R · days | US `trend_pullback` | US `minervini` |
|---|---|---|---|
| ≤ 3% | (16 trades) | 72% · +0.16 · 23 | 41% · −0.22 · 16 |
| 3–5% | 68% · +0.38 · 20 | 75% · 0.00 · 21 | 31% · −0.02 · 16 |
| 5–7% | 63% · +0.38 · 44 | 75% · −0.03 · 24 | 24% · +0.05 · 21 |
| 7–8% | 56% · +0.39 · 55 | 81% · −0.51 · 20 | 19% · +0.19 · 19 |
| 8–10% | 56% · +0.87 · 61 | 69% · −0.02 · 29 | capped |
| 10–15% | 55% · −0.05 · 58 | 53% · +0.42 · 26 | capped |
| > 15% | 31% · +0.44 · 88 | (8 trades) | capped |

- **Wider stops are hit less often and held longer** — `donchian` 68% stopped
  at 3–5% against 31% beyond 15% (India `donchian`: 75% and 42%).
- **Average R follows no clean line.** No width is reliably best; the gaps
  between buckets are within the noise of a few dozen trades.
- So **the stop comes from structure**, not from a taste for tight or wide. A
  stop well inside one day's normal range is a coin toss; one far wider than
  the base says the setup is loose. Both are reasons to pass.

## 5. Gaps — when the stop is not the price you get

A stop becomes a market order when touched; if the stock **opens below it**,
you get the open. The backtester fills a stop at `min(stop, open)` and lets it
win a tie with the target on the same bar. Across 2,393 stop exits (a "gap" is
a fill more than 0.5% below the stop):

| Run | Stop exits | Gapped | Avg R gapped | R lost beyond −1R | Worst |
|---|---|---|---|---|---|
| US `minervini` | 144 | 10 (6.9%) | −1.32 | −3.2R | −1.56 |
| US `trend_pullback` | 633 | 69 (10.9%) | −1.64 | −44.5R | −5.96 |
| US `breakout` | 462 | 39 (8.4%) | −1.50 | −19.3R | −4.06 |
| US `donchian` | 288 | 34 (11.8%) | −1.52 | −17.8R | −7.43 |
| India `trend_pullback` | 242 | 12 (5.0%) | −1.36 | −4.4R | −2.27 |
| India `donchian` | 257 | 17 (6.6%) | −1.31 | −5.2R | −2.06 |
| India `chart_pattern` | 348 | 20 (5.7%) | −1.37 | −7.4R | −1.93 |

(Two India trades in HEGAM.NS, a 64% overnight drop on 7 Sep 2026 shaped like
an unadjusted corporate action, are left out.) Clean stops cost −1.01 to
−1.02R. **About one stop in twelve gapped**, averaging −1.51R (median −1.28R;
fill a median 1.9% below the stop). The tail is long — −7.4R (a biotech's
failed trial, October 2022), −6.0R, −4.2R — and in US `trend_pullback` gaps
cost 44.5R beyond −1R: without them its −11.6R would have been about +33R.

### What causes them

The app stores each company's quarterly filing dates (`quarterly_results`). A
stop counts as "near results" if it falls within three weeks before a
quarterly filing (six for the annual) — a rough proxy, since results are
released days to weeks before the filing. Across 1,495 stops with filing data:

| | Near results | Index down > 2% that day | Neither |
|---|---|---|---|
| Gapped stops (138) | 50% | 25% | 33% |
| Clean stops (1,357) | 35% | 12% | 56% |

**Results are the biggest single cause, not the only one.** Gapped stops were
also twice as likely to fall on a day the index dropped 2%+ (24 Aug 2015,
24 Feb and 12 Mar 2020, 5 Aug 2024, 4–7 Apr 2025 all appear); the last third
were single-stock news no calendar shows. The
[calendar guide](learn-macro-calendar.md) covers results seasons — and notes
that **the backtests apply no earnings rule**, so these trades include holding
through results that the live gates partly avoid.

```series
title: Autodesk (ADSK) through its November 2017 results
from: 2017-09-01
to: 2018-01-31
tf: D
line: us:ADSK | Autodesk
mark: 2017-11-28 | breakout entry
mark: 2017-11-29 | results gap
caption: US breakout bought at 131.13 on 28 Nov, stop 126.90 (3.2% risk). Results came that evening; the stock opened at 114.03 and closed at 109.34. Filled at the open: −4.1R, the run's worst trade.
```

Live, `breakout`'s earnings gate would have refused this setup. The best
defence is the simplest: **know the results date; do not buy just before it.**

## 6. The backtester's exit modes

`backtest.py --exit-mode` picks how a position is managed (`portfolio_sim.py`).
Every mode keeps the initial stop and never lowers it.

| Mode | What the code does |
|---|---|
| `bracket` (default) | Fixed stop and target. Exit on the first bar whose low touches the stop (fill at the lower of stop and open) or whose high touches the target (the higher of target and open); both on one bar counts as the stop. |
| `trail_atr` | After each bar without an exit, the stop rises to the highest close since entry − `--atr-mult` × ATR(14) (default 3). Target kept unless `--no-target`. |
| `ma` | Initial stop, plus an exit **at the close** below a moving average (`--ma-col`, default 50-day). |
| `donchian` | Initial stop, plus an exit at the close below the lowest low of the prior `--donchian-bars` bars (default 50). |
| `minervini` | Each session in order: the stop; EX-02 a close below the pivot within 5 sessions; EX-03 stop to breakeven plus costs once the high reaches 2.5R; EX-04 a third sold at 3R; EX-05 a climax once up 25%; EX-06 a close under the 50-day on at least average volume; EX-07 a time stop (off by default). Close-based exits fill at the **next open**. |

No live screener manages an open position: `trend_pullback` and `breakout`
are fixed brackets; `donchian` reports its channel low for you to act on.

**The stored runs do not compare modes** for one strategy and version; each
uses its default. An earlier experiment (`research/momentum-trend-research.md`
§3.3) ran eight on one older `trend_pullback` signal set (879 signals):

| Policy | CAGR | Max drawdown | Avg R |
|---|---|---|---|
| `donchian` 50-day, no target | +1.06% | −38.8% | +0.095 |
| `bracket` | −0.87% | −40.6% | −0.044 |
| `trail_atr` 5 ATR, no target | −1.60% | −46.5% | −0.073 |
| `ma` 50-day, no target | −1.98% | −38.2% | −0.088 |
| `trail_atr` 3 ATR, no target | −4.81% | −51.9% | −0.221 |

Wide exits beat tight ones, and tighter trails did steadily worse. One
strategy, one older version: a hint, not a law.

## 7. Targets against letting winners run

| Run | Exit | Trades | Avg R | Median days |
|---|---|---|---|---|
| US `trend_pullback` | STOP / TARGET | 633 / 230 | −1.08 / **+2.93** | 16 / 52 |
| US `breakout` | STOP / TARGET | 462 / 241 | −1.05 / **+2.14** | 15 / 28 |
| India `chart_pattern` | STOP / TARGET | 350 / 165 | −1.05 / **+2.68** | 19 / 43 |
| India `trend_pullback` | STOP / TARGET | 244 / 103 | −1.07 / **+2.92** | 13 / 43 |
| US `donchian` | STOP / TREND_EXIT | 288 / 208 | −1.07 / **+2.64** | 14 / 149 |
| India `donchian` | STOP / TREND_EXIT | 257 / 180 | −1.03 / **+2.49** | 19 / 175 |
| US `minervini` | STOP / TREND_EXIT | 144 / 367 | −1.04 / +0.10 | 10 / 24 |
| | CLIMAX / BREAKEVEN_STOP | 29 / 11 | **+4.63** / +0.32 | 69 / 46 |

Also seen: FAILED_BREAKOUT, TIME_STOP (minervini rules, when on) and OPEN (held
at the run's end). Sort a trade list by *Exit* to see where the money is made.

A **fixed target caps the tail**: the best `trend_pullback` trade made 9.3R,
the best `breakout` trade 4.0R. A **trend exit leaves it open**: US
`donchian`'s best made 56.8R (a gold trust held 29 months) and 53.3R (NVIDIA)
— though its *median* trend exit was only +0.69R; most trends end soon.

```series
title: Letting a winner run — NVIDIA in the US donchian backtest, 2016–2018
from: 2016-03-01
to: 2018-12-31
tf: W
line: us:NVDA | NVIDIA (split-adjusted) | log
mark: 2016-05-17 | entry 1.05
mark: 2018-10-11 | 50-day-low exit 5.88
caption: Bought on a channel breakout with a stop about 9% below; held 877 days, until a close under the 50-day low. +53R — over a fifth of the run's whole result.
```

In every run **the top 5% of trades made more than the whole run**: US
`donchian` 25 trades +373R against +241R in total; US `minervini` 28 trades
+137R against +24R; US `trend_pullback` 43 trades +212R against −12R. Without
their best few trades all of them lose money — so an exit that clips those
trades removes the edge it means to protect.

## 8. Breakeven stops

Moving the stop to entry feels free; it turns a normal pullback into a
scratch. In US `minervini` it rises to breakeven plus costs at 2.5R; eleven
trades ended there — seven near 0R (−0.25R at worst), four near +1R because a
third had been sold at 3R.
A note beside `--breakeven-r` in `backtest.py` records an earlier measurement:
breakeven exits had reached a median 2.75R and realised −0.04R. The gain is
elsewhere: the open-risk cap counts a stop at or above entry as zero risk, so
breakeven **frees room for new trades** ([Portfolio risk](learn-risk-portfolio.md)).
A portfolio choice, not free insurance.

## 9. Selling into strength, selling into weakness

- **Into strength** — at a target, a third at 3R, or a *climax* (the biggest
  up day on the biggest volume since entry, 8 up closes in 10, 70% above the
  200-day, a 3% gap after a 50% gain). A good price; you give up what follows.
- **Into weakness** — on a close under the 50-day, the 50-day low, a trailing
  stop. You keep the trend and give back the slice between top and signal.

In US `minervini` 29 CLIMAX exits made +134R, 367 trend exits +35R; stops cost −149R.

```series
title: Selling into strength — Regeneron in the US Minervini backtest, 2013
from: 2013-01-01
to: 2013-07-31
tf: D
line: us:REGN | Regeneron
line: us:REGN@sma50 | 50-day average
mark: 2013-03-20 | entry 175.67
mark: 2013-04-10 | a third sold at 3R
mark: 2013-05-06 | climax: rest sold
caption: Stop 167.67 (4.6% risk). A third sold at 199.66 (3R) on 10 Apr and the stop went to breakeven; a climax sold the rest at the 6 May open near 264 — blended +8.4R. REGN peaked a week later, then fell 24% into June.
```

The Minervini spec's blend is a good default: **sell some into strength, let
the rest go on weakness.**

## 10. Failed breakouts and time stops

- **Failed breakout (EX-02):** a close back under the pivot within 5 sessions,
  sold next open. The US `minervini` v1.5 runs (2010–2026, otherwise identical)
  tested it: on, 609 of 908 trades ended that way at −0.28R and the run made
  −2.13% a year; a 2-day window, −3.02%; off, −1.17%. It cut trades that would
  later have worked; the v1.6 runs have it off. (India v1.5, rule on: 116 of
  192 trades ended this way, median 2 days, −0.36R.)
- **Time stop (EX-07):** sell what has not reached +1R after N sessions. In the
  code, off by default, used by no stored run or live strategy. The trade lists
  cannot settle it: trades closed within 10 days averaged −0.4 to −1.1R, and
  in most runs those held over 120 days +0.8 to +4.1R — but losers end early
  *because* they hit the stop. Length of hold is a result, not a cause.

## 11. What a trader does

1. **Write the stop before the entry**, under the structure that proves the
   idea wrong, and enter it as an order.
2. **Pass on setups whose stop is wider than about 8%** — do not shrink the
   stop to make the trade fit.
3. **Check the results date**; no new position in the week or two before it.
4. **Budget for gaps**: about one stop in twelve costing 1.5R, an occasional
   −4R to −7R. Size so that survives.
5. **Choose the exit style in advance** — target, trend exit, or part into
   strength and the rest on a trend break — never on the day.
6. **Raise stops only by rule**; never lower them.

## 12. What the evidence says

- **Robust:** a trend strategy's result comes from a few big trades (every run
  here); predefined stops keep the typical loss near 1R; gaps make a real
  minority of losses worse than that.
- **Supported here:** wide, structural exits beat tight trails in the one
  stored comparison; climax and partial sales made the US Minervini profit;
  results and market-wide drops explain most gaps.
- **Not shown:** that any stop width is best in R; that breakeven or time
  stops add value; that the failed-breakout rule helps (in the US it hurt).
  Every one of these backtests trails buy-and-hold — they show how exits
  behave, not that the strategies work.
- **Caveats:** survivorship bias; no earnings rule in the backtests; daily bars.

## 13. Checklist

- [ ] Stop written before entry, under a structural level, entered as an order
- [ ] Stop within the strategy's limit (≤ 8% for breakouts and VCPs)
- [ ] Results date checked — none in the next two weeks for a new position
- [ ] Open positions: any stop to raise by rule (breakeven at 2.5R, a trailing level)?
- [ ] Any holding up 25%+ showing climax behaviour — sell some into it?
- [ ] Review the week's exits by reason: stops honoured? any gaps?

## Further reading

- Mark Minervini, *Trade Like a Stock Market Wizard* — the maximum-loss rule
  and selling into strength.
- William O'Neil, *How to Make Money in Stocks* — the 7–8% loss rule and taking
  profits at 20–25%.
- Van K. Tharp, *Trade Your Way to Financial Freedom* — R-multiples, and exits
  as the larger half of a system.
- Curtis Faith, *Way of the Turtle* — channel and volatility stops, and why
  trend followers live on a few trades.
