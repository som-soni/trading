# App notes moved out of learn-risk-portfolio (verbatim)

## From the intro (Where this shows in the app; The data)
Learning material: what all your open positions can lose together. It covers
open risk ("heat"), how many positions to hold, correlation and sector
clusters, market-wide drops, drawdown arithmetic, and cutting or adding
exposure. All of it is measured on this app's own backtests. This is the last
of four risk guides, after [Expectancy](learn-risk-expectancy.md), [Position sizing](learn-risk-sizing.md)
and [Stops and exits](learn-risk-stops-exits.md).

**Where this shows in the app.** A backtest's report (strategy → **Backtests**
tab, or **System → Reports archive**) has a drawdown chart. Its equity table
shows *Drawdown %* and *Open positions* for every day. The screener caps the
day's tradeable picks at three per sector (setting `sector_limit_per_sector`;
the extra rows are marked WATCH - SECTOR LIMIT). **Watchlists** shows each
stock's peer group or sector. What the app does *not* do — track what you
hold — is in §10.

**The data.** The same runs as the stops guide: US Minervini v1.6
(2010–2026); US and India trend pullback and Donchian, US breakout, and India
chart patterns (2013–2026). There are also five US Minervini variants that
change only the portfolio rules. These are backtests with modelled costs, on
stocks listed today (so they carry survivorship bias). Each trade risks 1%, with
at most 10 positions open (8 for Minervini). Sectors come from the app's
industry table: 11 sectors, using today's classification.

---


## From §1 Open risk (backtester's open-risk cap)
## 1. Open risk — the "heat" of the portfolio

For one position, risk is (price − stop) × shares. Once the position is in
profit, count from your cost instead of the price, since only your own capital
is at risk. **Open risk, or heat, is that summed over every position**, as a
share of the account. On a ₹20 lakh account:

| Position | Shares | Price | Stop | At risk | % of account |
|---|---|---|---|---|---|
| A | 400 | ₹1,000 | ₹950 | ₹20,000 | 1.0% |
| B | 250 | ₹1,600 | ₹1,520 | ₹20,000 | 1.0% |
| C (stop raised to cost) | 300 | ₹1,500 | ₹1,520 | ₹0 | 0.0% |
| D | 1,000 | ₹480 | ₹460 | ₹20,000 | 1.0% |
| **Heat** | | | | **₹60,000** | **3.0%** |

A stop at or above cost puts **zero** capital at risk (position C). Heat is
measured to where the stop is *now*, so raising stops lowers the portfolio's
heat. The backtester's open-risk cap measures it this way: for each position,
the lower of the last close and the entry, minus the stop, times shares; then
summed (`portfolio_sim.py`). Heat ignores **open profit**: C can still give back
everything above ₹1,520.


## From §2 Why 1% per trade is not 1% total (US Donchian heat)
## 2. Why 1% per trade is not 1% total

Each trade risks 1%. With ten open, up to **10% of the account is at risk at
once**. Four things push the real figure higher:

- **Equity falls, heat rises.** Each position was sized on the account's value
  at its entry. After a losing stretch, the same stops are a bigger share of a
  smaller account. US Donchian's heat reached 10.4% of equity with ten positions.
- **Gaps.** One stop in twelve fills worse than −1R, averaging −1.5R
  ([stops guide](learn-risk-stops-exits.md)). When the whole market gaps down,
  many stops fill worse at the same time.
- **Re-entry.** Heat is a snapshot of one day. A strategy that keeps buying new
  breakouts during a decline keeps adding fresh risk (§4).
- **Correlation.** Ten positions that fall together behave like a few large
  ones (§5).

Losing streaks compound: ten 1% losses in a row cost 9.6%, and ten 2% losses
cost 18.3% ([Expectancy](learn-risk-expectancy.md) covers how often streaks happen).


## §3 How many positions at once — measured (whole section)
## 3. How many positions at once — measured

Heat below uses each trade's initial stop. For the bracket strategies (fixed
stop and target), stops never move, so the figure is exact. For Minervini,
whose stops can move up to breakeven, it is an upper bound.

| Run | Open positions: mean · max | Heat: mean · 95th pct · max | Worst 10 sessions |
|---|---|---|---|
| US Minervini | 2.9 · 8 | 2.5% · 5.5% · 6.8% | −9.1% (to 4 May 2022) |
| US trend pullback | 6.2 · 10 | 3.8% · 6.5% · 8.5% | −11.0% (to 10 Mar 2026) |
| US breakout | 4.1 · 10 | 3.0% · 5.0% · 6.9% | −9.1% (to 28 Feb 2020) |
| US Donchian | 9.7 · 10 | 5.9% · 9.1% · 10.4% | −16.7% (to 2 Mar 2020) |
| India trend pullback | 2.4 · 10 | 2.0% · 5.7% · 8.1% | −9.4% (to 15 Sep 2026)* |
| India Donchian | 9.5 · 10 | 6.9% · 9.0% · 10.2% | −17.7% (to 13 May 2022) |
| India chart patterns | 4.4 · 10 | 3.5% · 6.6% · 7.8% | −12.2% (to 15 Sep 2026)* |

\*Includes the HEGAM.NS drop of 7 Sep 2026, which looks like an error in the data.

- **Selective strategies rarely fill all their slots.** US Minervini held three
  positions on a typical day, and none on a fifth of days. **Strategies that
  are always in the market run with high heat.** Both Donchian portfolios were
  full nearly every day, at 6–7% heat, and 9% one day in twenty.
- **The worst ten sessions lost more than the heat on any single day**:
  −16.7% and −17.7%, against peak heat near 10%. The extra came from new
  entries being stopped out too, and from open profit given back (§4).

The Minervini spec caps heat at **6%** (rule PF-04, applied when the backtest
runs with the spec's rules). A fill that would take the portfolio past it
waits. In the US run that skipped 34 fills.


## §4 Heat is a snapshot — the 2020 example (US Donchian run)
## 4. Heat is a snapshot — the 2020 example

```series
title: The S&P 500 ETF, February–April 2020
from: 2020-01-02
to: 2020-04-30
tf: D
line: us:SPY | SPY
band: 2020-02-19 2020-03-23 | −34% in 23 sessions
caption: On 19 Feb the US Donchian portfolio held ten positions with 4.7% heat. Over the next six weeks it was stopped out 36 times, bought 32 new breakouts and lost about 30% of equity.
```

On 19 February 2020, US Donchian held ten positions with **4.7% of equity at
risk**. If every stop had been hit at once, it would have cost about 5%. What
actually happened, between 18 February and 31 March:

- 41 positions closed, 36 of them on stops.
- **32 new ones were bought.**
- The closed trades lost −35.4R, about $21,500 measured from their entry prices.
  The rest of the loss was open profit given back.

Equity went from about $97,900 (14 Feb) to $68,700 in late April. That is
**−30%**, six times the first day's heat. A heat limit bounds what the current
positions can lose from their cost. It does not protect open profit. Nor does
it stop a strategy buying new positions as old ones are stopped out in a
falling market. That needs a rule about *new* risk (§8).


## §5 Correlation (measured on backtest positions; clustering table)
## 5. Correlation — positions that move together

Stocks in one industry share customers, costs and shareholders. The table is
measured on positions held on the same day, using the correlation of their
daily returns over 60 days:

| Run | Same industry | Same sector | Different sector |
|---|---|---|---|
| US Donchian | 0.62 | 0.39 | 0.19 |
| US trend pullback | 0.47 | 0.36 | 0.25 |
| US breakout | 0.47 | 0.38 | 0.27 |
| India Donchian | 0.40 | 0.32 | 0.19 |
| India chart patterns | 0.45 | 0.30 | 0.20 |

**Two stocks in the same industry moved two to three times as closely as two
in different sectors.** Three positions in one industry are closer to one large
position than to three independent ones.

How often did the portfolios cluster? The table shows the share of held
positions that shared a sector (or industry) with another holding. Beside it
is the share you would get from random picks among the names the strategy
actually traded:

| Run | Shared a sector | Random | Shared an industry | Random |
|---|---|---|---|---|
| US Minervini | 43% | 33% | 8% | 5% |
| US trend pullback | 51% | 50% | 10% | 8% |
| US Donchian | 64% | 61% | 16% | 13% |
| US breakout | 38% | 37% | 7% | 5% |
| India trend pullback | 40% | 33% | 16% | 9% |
| India Donchian | 68% | 62% | 36% | 25% |
| India chart patterns | 42% | 41% | 14% | 14% |

Mostly this is close to chance. There was real clustering in India Donchian,
US Minervini and India trend pullback. With only 11 broad sectors, **ten
positions share sectors by chance alone**. And leading stocks come from leading
groups ([learn-sectors-groups.md](learn-sectors-groups.md)). So a portfolio of
leaders becomes concentrated when one theme is popular: India Donchian once
held eight positions in one sector.


## §6 Market-wide drops (stops per week in the runs)
## 6. Market-wide drops hit every long at once

The biggest correlation is with the market itself. A portfolio that only buys
(never sells short) is one bet on the market, whatever its sectors. Stop-outs
bunch together when the market falls:

| Run | Most stops in one week |
|---|---|
| US Donchian | 15 (week of 24 Feb 2020); 10 (13 Oct 2014) |
| US breakout | 12 (week of 25 Jan 2021) |
| US trend pullback | 8 (24 Feb 2020 and 24 Mar 2014) |
| India Donchian | 8 (week of 9 May 2022) |

US Donchian's worst months were March 2020 (−21.4R) and October 2014
(−14.2R). When the index falls, spreading across sectors helps less than it
looks. The defence is **less exposure when the market is weak**. The market's
trend ([learn-health-trend.md](learn-health-trend.md)) and breadth
([learn-health-breadth.md](learn-health-breadth.md)) tell you when.


## From §7 Drawdowns (the backtests' own equity curves)
|---|---|---|---|---|
| US Minervini | −43.5% | Jan 2014 → Oct 2023 | Not by Oct 2026 | −34.1% (SPY) |
| US trend pullback | −46.5% | Feb 2021 → Mar 2026 | Not by Oct 2026 | −34.1% |
| US breakout | −29.7% | Jun 2018 → Nov 2023 | Feb 2026 (7.6 years) | −34.1% |
| US Donchian | −49.3% | Feb 2020 → Oct 2023 | Sep 2025 (5.5 years) | −34.1% |
| India trend pullback | −32.1% | Jun 2024 → Mar 2026 | Not by Oct 2026 | −38.3% (Nifty 500) |
| India Donchian | −44.2% | Jan 2025 → Mar 2026 | Not by Oct 2026 | −38.3% |
| India chart patterns | −27.8% | Sep 2018 → Jul 2020 | Sep 2021 (3.0 years) | −38.3% |

**Years below the previous peak are the norm**, even at 1% risk per trade. A
drawdown rule (§11) is about staying able to follow the system through them.


## §8 Cutting exposure after losses, adding after wins (backtest variants)
## 8. Cutting exposure after losses, adding after wins

The backtester can test both on the same signals (options `--pe`, `--pe-press`,
`--market-filter`, `--pyramid`). The rules:

- **Progressive exposure** (`--pe`) halves the risk per trade during the first
  five trades, after two losses in a row, or while the last ten closed trades
  are not net positive.
- **Pressing** (`--pe-press`) risks 1.25× and allows two extra positions once
  those ten trades are +4R or better.
- **The market filter** takes no new trades while the benchmark index is below
  its 200-day average (or its 50-day average is below its 200-day).

Results for US Minervini v1.6, 2010–2026 (SPY: 12.1% a year, −34.1% at worst):

| Variant | CAGR | Max drawdown |
|---|---|---|
| Base | 0.65% | −43.5% |
| Half size after losses (`--pe`) | 0.58% | −34.6% |
| … and press after wins (`--pe-press 4`) | 0.68% | −34.9% |
| Market filter | 1.34% | −28.6% |
| Market filter, 5-day confirmation | 0.72% | −31.2% |
| Market filter (5-day) + half size after losses | 0.53% | −27.5% |

A pair of v1.5 runs tested adding to winners (`--pyramid 0.5`: half at entry,
the rest 2% higher). Return went from 0.85% to −0.39% a year, and drawdown
from −42.2% to −44.1%. **The "cut" rules took a fifth to a third off the worst
drawdown at little or no cost. Pressing added little. Pyramiding hurt.** None
made the strategy beat the index. Managing exposure changes the path the
account takes, not the edge.


## From §9 Cash is a position
## 9. Cash is a position

Holding no stocks is a position too. It has a known return (the cash rate) and
no drawdown. US Minervini held nothing on 20% of days (32% with the market
filter). On those days a rule said the odds were poor. Make each trade earn
its way out of cash.


## §10 What the app tracks — and what it does not (whole section)
## 10. What the app tracks — and what it does not

| Exists | Where |
|---|---|
| Per-trade sizing: 1% risk (0.5% when the VIX or India VIX is high), 25% position cap | `core/sizing.py`, `config/us.py`, `config/india.py` |
| At most three tradeable picks per sector in each screener run | `screening/portfolio.py`, `sector_limit_per_sector` |
| The screener script prints the total risk and size of the day's TRADE picks against the account | `screening/output.py` (console only) |
| Position cap, open-risk cap, progressive exposure, market filter — **in backtests** | `backtesting/portfolio_sim.py`, `backtest.py` flags |
| Drawdown and open positions per day of each backtest | Backtest report, equity table |

**Not tracked:** your holdings, shares and stops. So the app shows **no live
heat, correlation or sector concentration for your own portfolio**. Watchlists
hold symbols, notes and the screener's planned entry and stop, not positions.
The daily journal template has a *Positions* table you fill in by hand. The
sector cap applies to a day's candidates, not to what you own, and no backtest
applies it.


## From §11 What a trader does
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


## From §12 What the evidence says
## 12. What the evidence says

- **Robust:** losses compound against you (the recovery table is arithmetic).
  Stocks in one industry are correlated. Market declines hit all long positions.
- **Measured here:** the portfolios ran at 2–7% average heat. The worst real
  losses came from **renewed** risk during declines, not from the heat on one
  day. Cutting size after losses or in a weak market cut the worst drawdown by
  a fifth to a third, at little cost. Pressing and pyramiding did not help.
- **Not shown:** that sector limits improve returns. These portfolios clustered
  by sector only a little more than chance, and no stored backtest applies a
  sector cap. The thresholds in §11 are common practice, not optimised.
- **Caveats:** backtests on today's stocks; one account size per market; costs
  modelled, not paid; every strategy here does worse than buy-and-hold.

