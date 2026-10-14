# Portfolio risk — what all your positions can lose at once

Learning material: open risk ("heat"), how many positions to hold, correlation
and sector clusters, market-wide drops, drawdown arithmetic, and cutting or
adding exposure — measured on this app's own backtests. Last of four risk
guides, after [Expectancy](learn-risk-expectancy.md), [Position sizing](learn-risk-sizing.md)
and [Stops and exits](learn-risk-stops-exits.md).

**Where this shows in the app.** A backtest's report (strategy → **Backtests**
tab, or **System → Reports archive**) has a drawdown chart and, in its equity
table, *Drawdown %* and *Open positions* for every day. The screener caps the
day's tradeable picks at three per sector (`sector_limit_per_sector`, rows
marked WATCH - SECTOR LIMIT). **Watchlists** shows each stock's peer group or
sector. What the app does *not* do — track what you hold — is in §10.

**The data.** The runs used in the stops guide — US `minervini` v1.6
(2010–2026); US and India `trend_pullback` and `donchian`, US `breakout`, India
`chart_pattern` (2013–2026) — plus five US `minervini` variants that change only
portfolio rules. Backtests with modelled costs on today's stocks (survivorship
bias), 1% risk per trade, at most 10 positions (8 for `minervini`). Sectors:
`symbol_industry` (11 sectors, today's classification).

---

## 1. Open risk — the "heat" of the book

For one position, risk is (price − stop) × shares — counted from your cost
rather than the price once it is in profit, since only your capital is at
risk. **Open risk, or heat, is that summed over every position**, as a share of
the account. On a ₹20 lakh account:

| Position | Shares | Price | Stop | At risk | % of account |
|---|---|---|---|---|---|
| A | 400 | ₹1,000 | ₹950 | ₹20,000 | 1.0% |
| B | 250 | ₹1,600 | ₹1,520 | ₹20,000 | 1.0% |
| C (stop raised to cost) | 300 | ₹1,500 | ₹1,520 | ₹0 | 0.0% |
| D | 1,000 | ₹480 | ₹460 | ₹20,000 | 1.0% |
| **Heat** | | | | **₹60,000** | **3.0%** |

A stop at or above cost is **zero** capital at risk (C), and heat is measured
to the stop *now*, so raising stops cools the book. The backtester's open-risk
cap measures it this way (`portfolio_sim.py`: `min(last close, entry) − stop`,
times shares, summed). Heat ignores **open profit**: C can still give back
everything above ₹1,520.

## 2. Why 1% per trade is not 1% total

Each trade risks 1% (`core/sizing.py`); ten open is up to **10% at risk at
once** — and four things push the real figure higher:

- **Equity falls, heat rises.** Each position was sized on equity at its entry;
  after a losing stretch the same stops are a bigger share of a smaller
  account. US `donchian`'s heat reached 10.4% of equity with ten positions.
- **Gaps.** One stop in twelve fills worse than −1R, averaging −1.5R
  ([stops guide](learn-risk-stops-exits.md)); on a market-wide gap many fill
  worse together.
- **Re-entry.** Heat is a snapshot. A strategy that keeps buying new
  breakouts during a decline keeps renewing its heat (§4).
- **Correlation.** Ten positions that fall together behave like a few large
  ones (§5).

Streaks compound: ten 1% losses in a row cost 9.6%, ten 2% losses 18.3%
([Expectancy](learn-risk-expectancy.md) covers how often streaks happen).

## 3. How many positions at once — measured

Heat below uses each trade's initial stop. For the bracket strategies stops
never move, so it is exact; for `minervini` (breakeven stops) it is an upper
bound.

| Run | Open positions: mean · max | Heat: mean · 95th pct · max | Worst 10 sessions |
|---|---|---|---|
| US `minervini` | 2.9 · 8 | 2.5% · 5.5% · 6.8% | −9.1% (to 4 May 2022) |
| US `trend_pullback` | 6.2 · 10 | 3.8% · 6.5% · 8.5% | −11.0% (to 10 Mar 2026) |
| US `breakout` | 4.1 · 10 | 3.0% · 5.0% · 6.9% | −9.1% (to 28 Feb 2020) |
| US `donchian` | 9.7 · 10 | 5.9% · 9.1% · 10.4% | −16.7% (to 2 Mar 2020) |
| India `trend_pullback` | 2.4 · 10 | 2.0% · 5.7% · 8.1% | −9.4% (to 15 Sep 2026)* |
| India `donchian` | 9.5 · 10 | 6.9% · 9.0% · 10.2% | −17.7% (to 13 May 2022) |
| India `chart_pattern` | 4.4 · 10 | 3.5% · 6.6% · 7.8% | −12.2% (to 15 Sep 2026)* |

\*Includes the HEGAM.NS drop of 7 Sep 2026, which looks like a data artefact.

- **Selective strategies rarely fill the book** (US `minervini`: three on a
  typical day, none on a fifth of days); **always-on ones run hot** (both
  `donchian` books full nearly every day, 6–7% heat, 9% one day in twenty).
- **The worst ten sessions lost more than the heat on any single day** —
  −16.7% and −17.7% against peak heat near 10% — through new entries being
  stopped too, and open profit given back (§4).

The Minervini spec caps heat at **6%** (`MAX_OPEN_RISK_PCT`, rule PF-04,
applied with `--spec`): a fill that would take the book past it waits. In the
US run that skipped 34 fills.

## 4. Heat is a snapshot — the 2020 example

```series
title: The S&P 500 ETF, February–April 2020
from: 2020-01-02
to: 2020-04-30
tf: D
line: us:SPY | SPY
band: 2020-02-19 2020-03-23 | −34% in 23 sessions
caption: On 19 Feb the US donchian book held ten positions with 4.7% heat. Over the next six weeks it was stopped 36 times, bought 32 new breakouts and lost about 30% of equity.
```

On 19 February 2020, US `donchian` held ten positions with **4.7% of equity at
risk**: every stop hit at once would have cost about 5%. What happened:
between 18 February and 31 March, 41 positions closed (36 on stops), **32 new
ones were bought**, and the closed trades lost −35.4R, about $21,500 against
their entry prices; the rest was open profit given back. Equity went from about
$97,900 (14 Feb) to $68,700 in late April — **−30%**, six times the first day's
heat. A heat limit bounds what the current book can lose from cost; it does not
protect open profit or stop a strategy refilling the book in a falling market.
That needs a rule about *new* risk (§8).

## 5. Correlation — positions that move together

Stocks in one industry share customers, costs and owners. Measured on
positions held on the same day (60-day correlation of daily returns):

| Run | Same industry | Same sector | Different sector |
|---|---|---|---|
| US `donchian` | 0.62 | 0.39 | 0.19 |
| US `trend_pullback` | 0.47 | 0.36 | 0.25 |
| US `breakout` | 0.47 | 0.38 | 0.27 |
| India `donchian` | 0.40 | 0.32 | 0.19 |
| India `chart_pattern` | 0.45 | 0.30 | 0.20 |

**Two stocks in the same industry moved two to three times as closely as two
in different sectors.** Three positions in one industry are closer to one large
position than to three independent ones.

How often did books cluster? The share of held positions sharing a sector
with another, against random picks from the strategy's own traded names:

| Run | Shared a sector | Random | Shared an industry | Random |
|---|---|---|---|---|
| US `minervini` | 43% | 33% | 8% | 5% |
| US `trend_pullback` | 51% | 50% | 10% | 8% |
| US `donchian` | 64% | 61% | 16% | 13% |
| US `breakout` | 38% | 37% | 7% | 5% |
| India `trend_pullback` | 40% | 33% | 16% | 9% |
| India `donchian` | 68% | 62% | 36% | 25% |
| India `chart_pattern` | 42% | 41% | 14% | 14% |

Mostly close to chance, with real clustering in India `donchian`, US
`minervini` and India `trend_pullback`. With 11 broad sectors **ten positions
share sectors by chance alone**; and leaders come from leading groups
([learn-sectors-groups.md](learn-sectors-groups.md)), so a book of leaders
concentrates when a theme is hot — India `donchian` once held eight positions
in one sector.

## 6. Market-wide drops hit every long at once

The biggest correlation is the market itself. A long-only book is one bet on
the market, whatever its sectors. Stop-outs cluster in its declines:

| Run | Most stops in one week |
|---|---|
| US `donchian` | 15 (week of 24 Feb 2020); 10 (13 Oct 2014) |
| US `breakout` | 12 (week of 25 Jan 2021) |
| US `trend_pullback` | 8 (24 Feb 2020 and 24 Mar 2014) |
| India `donchian` | 8 (week of 9 May 2022) |

US `donchian`'s worst months were March 2020 (−21.4R) and October 2014
(−14.2R). Spreading across sectors helps less than it looks when the index
falls; the defence is **less exposure when the market is weak** — the regime
([learn-health-trend.md](learn-health-trend.md)) and breadth
([learn-health-breadth.md](learn-health-breadth.md)) say when.

## 7. Drawdowns and the arithmetic of recovery

A loss needs a larger gain to undo:

| Drawdown | Gain needed | Years to recover at 10% a year |
|---|---|---|
| −10% | +11% | 1.1 |
| −20% | +25% | 2.3 |
| −30% | +43% | 3.7 |
| −40% | +67% | 5.4 |
| −50% | +100% | 7.3 |
| −60% | +150% | 9.6 |

```series
title: The S&P 500 and its distance below its record, 2000–2014
from: 2000-01-01
to: 2014-12-31
tf: W
line: us:SP500_PRICE_LONG | S&P 500 (price) | log
line: us:SP500_PRICE_LONG@dd | % below its record | pane2 zero
band: 2000-03-24 2007-05-30 | 7 years to regain the 2000 high
band: 2007-10-09 2013-03-28 | 5½ years to regain the 2007 high
caption: −49% by October 2002 and −57% by March 2009 — each needed a doubling or more to recover. The index sat below its 2000 high for most of 13 years.
```

The long history is in [the trend guide](learn-health-trend.md): the 1929
high was not regained until 1954. India's version: the Nifty 50 fell 60%
from January to October 2008 and first closed back above its high in November
2010; 2020's 38% fall was regained in about ten months.

```series
title: The Nifty 50's distance below its record, 2008–2015
from: 2007-09-17
to: 2015-12-31
tf: W
line: india:NIFTY50@dd | Nifty 50, % below its record | zero
band: 2008-01-08 2010-11-09 | below the January 2008 high
caption: −60% at the October 2008 low. It took almost three years to get back, and the high did not hold for long.
```

The backtests' own equity curves:

| Run | Max drawdown | Peak → trough | Back to the peak? | Benchmark max DD |
|---|---|---|---|---|
| US `minervini` | −43.5% | Jan 2014 → Oct 2023 | Not by Oct 2026 | −34.1% (SPY) |
| US `trend_pullback` | −46.5% | Feb 2021 → Mar 2026 | Not by Oct 2026 | −34.1% |
| US `breakout` | −29.7% | Jun 2018 → Nov 2023 | Feb 2026 (7.6 years) | −34.1% |
| US `donchian` | −49.3% | Feb 2020 → Oct 2023 | Sep 2025 (5.5 years) | −34.1% |
| India `trend_pullback` | −32.1% | Jun 2024 → Mar 2026 | Not by Oct 2026 | −38.3% (Nifty 500) |
| India `donchian` | −44.2% | Jan 2025 → Mar 2026 | Not by Oct 2026 | −38.3% |
| India `chart_pattern` | −27.8% | Sep 2018 → Jul 2020 | Sep 2021 (3.0 years) | −38.3% |

**Years underwater are the norm**, even at 1% risk per trade; a drawdown rule
(§11) is about staying able to follow the system through them.

## 8. Cutting exposure after losses, adding after wins

The backtester can test both on the same signals (`--pe`, `--pe-press`,
`--market-filter`, `--pyramid`). Progressive exposure (`Exposure` in
`portfolio_sim.py`) halves the risk per trade during the first five trades,
after two losses in a row, or while the last ten closed trades are not net
positive; `--pe-press` risks 1.25× and allows two extra positions once those
ten are +4R or better. The market filter takes no new trades while the
benchmark is below its 200-day (or its 50-day below its 200-day). US
`minervini` v1.6, 2010–2026 (SPY: 12.1% a year, −34.1% at worst):

| Variant | CAGR | Max drawdown |
|---|---|---|
| Base | 0.65% | −43.5% |
| Half size after losses (`--pe`) | 0.58% | −34.6% |
| … and press after wins (`--pe-press 4`) | 0.68% | −34.9% |
| Market filter | 1.34% | −28.6% |
| Market filter, 5-day confirmation | 0.72% | −31.2% |
| Market filter (5-day) + half size after losses | 0.53% | −27.5% |

A v1.5 pair tested adding into strength (`--pyramid 0.5`: half at entry, the
rest 2% higher): 0.85% → −0.39% a year, drawdown −42.2% → −44.1%. **The "cut"
rules took a fifth to a third off the worst drawdown at little or no cost;
pressing added little; pyramiding hurt.** None made the strategy beat the
index — managing exposure changes the path, not the edge.

## 9. Cash is a position

Flat is a position: a known return (the cash rate), no drawdown. US
`minervini` held nothing on 20% of days (32% with the market filter) — days a
rule said the odds were poor. Make each trade earn its way out of cash.

## 10. What the app tracks — and what it does not

| Exists | Where |
|---|---|
| Per-trade sizing: 1% risk (0.5% when the VIX or India VIX is high), 25% position cap | `core/sizing.py`, `config/us.py`, `config/india.py` |
| At most three tradeable picks per sector in each screener run | `screening/portfolio.py`, `sector_limit_per_sector` |
| The screener script prints the total risk and size of the day's TRADE picks against the account | `screening/output.py` (console only) |
| Position cap, open-risk cap, progressive exposure, market filter — **in backtests** | `backtesting/portfolio_sim.py`, `backtest.py` flags |
| Drawdown and open positions per day of each backtest | Backtest report, equity table |

**Not tracked:** your holdings, shares and stops — so **no live heat,
correlation or sector concentration of your book**. Watchlists hold symbols,
notes and the screener's planned entry and stop, not positions; the daily
journal template has a hand-filled *Positions* table. The sector cap applies to
a day's candidates, not to what you own, and no backtest applies it.

## 11. What a trader does

1. **Set a heat limit** — e.g. **6%** of the account at risk across all
   positions (the Minervini spec's figure). New trades wait while you are at
   the limit; raising stops frees room.
2. **Set a concentration limit** — e.g. no more than **two or three positions
   per industry group** and about **a third of the account in one sector**.
   Count industries, not just sectors: same-industry pairs moved two to
   three times as closely as different-sector pairs.
3. **Set a drawdown rule** — e.g. at **−10% from the equity peak, halve the
   risk per trade; at −20%, stop opening trades** and review. Restore size
   after wins, not after a calendar date.
4. **Let the market set exposure**: fewer and smaller positions below the
   200-day or on weak breadth; no new risk the day before a big event.
5. **Recompute heat each week**: (lower of price and cost − stop) × shares,
   summed over positions, against today's equity.

## 12. What the evidence says

- **Robust:** losses compound against you (the recovery table is arithmetic);
  stocks in one industry are correlated; market declines hit all longs.
- **Measured here:** books ran at 2–7% average heat; the worst real losses
  came from **renewed** risk during declines, not from the heat on one day;
  cutting size after losses or in a weak market cut the worst drawdown by a
  fifth to a third at little cost; pressing and pyramiding did not help.
- **Not shown:** that sector limits improve returns — these books clustered
  little beyond chance by sector, and no stored backtest applies a sector cap.
  The thresholds in §11 are common practice, not optimised.
- **Caveats:** backtests on today's stocks; one account size per market; costs
  modelled, not paid; every strategy here trails buy-and-hold.

## 13. Checklist

- [ ] Heat this week: Σ (lower of price and cost − stop) × shares ÷ equity — under the limit?
- [ ] Positions per industry group and per sector — any over the limit?
- [ ] Equity against its peak — has the drawdown rule changed my risk per trade?
- [ ] Market regime and breadth: is this a week for new risk at all?
- [ ] Any event (results, CPI, Fed, RBI, Budget) where several holdings gap together?
- [ ] Cash: am I holding it on purpose?

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — position sizing and
  total portfolio risk in R.
- Mark Minervini, *Think & Trade Like a Champion* — progressive exposure:
  smaller after losses, larger after wins.
- William O'Neil, *How to Make Money in Stocks* — moving to cash when the
  market turns.
