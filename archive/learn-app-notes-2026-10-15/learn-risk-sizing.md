# App notes moved out of learn-risk-sizing (verbatim)

## From the intro (contents list and 'Where this shows in the app')
Learning material: how much to buy. This guide covers:

- fixed-fractional risk (risking the same small share of the account on every trade);
- the one formula that turns a stop into a share count;
- the app's sizing exactly as coded, and how often its position cap overrides it;
- volatility-based stops;
- why fixed share counts and fixed amounts fail;
- the arithmetic of losses, and the risk of ruin (losing so much you cannot
  recover), simulated on this app's own trades;
- Kelly as an upper bound;
- adding to winners and cutting size after losers;
- the Indian specifics.

This is the second of four risk guides. Read [expectancy](learn-risk-expectancy.md)
first; then [stops and exits](learn-risk-stops-exits.md) and
[portfolio risk](learn-risk-portfolio.md).

**Where this shows in the app.** The sizing code is `core/sizing.py`. The
account settings are in `config/us.py` and `config/india.py`. Every screener row
is sized. On Strategies → (a strategy) → **Setups today**, the *Columns* menu
adds `shares`, `position_value` and `usd_at_risk` next to the default *Entry*,
*Stop* and *Risk %* (the stop's distance below the entry). The backtester sizes
every trade the same way (`backtesting/portfolio_sim.py`). Each backtest's
Trades tab lists the `shares` and `notional` (the position's value) it bought.


## From §2 The formula (configured accounts)
The app's configured accounts are **$50,000** (US) and **₹20,00,000** (India),
each at **1%** risk: $500 and ₹20,000 a trade.

## §3 The app's sizing, exactly as coded (whole section, incl. 'When the cap binds' backtest table)
## 3. The app's sizing, exactly as coded

The sizing function (`size_position` in `core/sizing.py`) works in four steps:

1. **Risk amount** = account size × the risk setting (`risk_pct`, 1%). When the
   volatility index closed above its threshold, it uses the high-volatility
   setting instead (`risk_pct_high_vol`, 0.5%). The threshold is VIX 25 in
   the US and India VIX 20 ([the volatility guide](learn-health-volatility.md)
   covers when that happens).
2. **Shares** = floor(risk amount ÷ (entry − stop)). "Floor" means rounded
   down to a whole share.
3. **The cap.** The position may not be worth more than 25% of the account
   (`max_position_pct`). If shares × entry is larger, shares = floor(25% of the
   account ÷ entry). The row then reports the smaller **actual** amount at risk.
4. **Too large for account.** If the result is under one share, the trade is
   flagged. The breakout, trend pullback, Donchian and chart-pattern
   strategies then grade it *WATCH – WAIT* with the reason "too large for
   account". With the configured accounts, that happens when the share price is
   above a quarter of the account, or the risk per share is above $500 / ₹20,000.

### When the cap binds

At 1% risk and a 25% cap, the arithmetic is simple: **the cap binds whenever
the stop is less than 4% below the entry** (1% ÷ 25%). In high volatility, at
0.5% risk, it binds only when the stop is less than 2% below. A trade with a 3%
stop then risks 0.75%, not 1%.

How often that happened in the backtests (each strategy's full run on its
current version; risk is measured against the account's value on the day
before entry):

| Run | Trades | Median stop distance | Cap bound (stop under 4%) | Their median risk |
|---|---|---|---|---|
| Volume breakout, US | 705 | 4.8% | 29% | 0.80% |
| Trend pullback, US | 870 | 4.8% | 33% | 0.51% |
| Minervini SEPA, US | 557 | 5.5% | 15% | 0.81% |
| Donchian channel, US | 506 | 7.5% | 13% | 0.44% |
| Trend pullback, India | 352 | 6.3% | 10% | 0.78% |
| Chart patterns, India | 518 | 6.2% | 4% | 0.80% |
| Donchian channel, India | 447 | 8.9% | 1% | 0.54% |

US setups have tighter stops and hit the cap far more. A second limit binds
even more often in the backtests: **cash**. Ten positions of up to 25% each
can need 250% of the account. When cash runs short, the simulator buys what
the cash allows rather than skipping the breakout. That gives a smaller
position, so less than the intended risk, never more (`portfolio_sim.py`).
Across these runs, the average risk actually taken was 0.63%–0.86% of the
account in the US runs and 0.80%–0.99% in India, not the nominal 1%.

Two more differences:

- **The live screener sizes off the configured account.** The backtest sizes
  off the account's current value, so it compounds.
- **The backtest always sizes at 1%.** It passes `vix_above_threshold=False`,
  so the halving in high volatility has never been tested.


## From §4 Why the cap matters: gaps (chart caption of the app's trade)
## 4. Why the cap matters: gaps

The formula assumes the stop fills at the stop price. If the stock gaps below
the stop, the sale fills at the open instead. Then **the loss scales with the
position, not with the risk**. A tight stop gives a big position, and a big
position is what a gap punishes:

```series
title: Autodesk (ADSK), late 2017 — a tight stop, a full-size position, a gap
from: 2017-10-01
to: 2018-01-31
tf: D
line: us:ADSK | Autodesk (ADSK)
mark: 2017-11-28 | Volume breakout entry about $131, stop $126.90
mark: 2017-11-29 | Opened about $114 after results
caption: The stop was 3.2% below the entry, so the cap bound: 24.8% of equity, 0.8% at risk. The close went from $129.9 to $109.3; the trade lost 4.1R — 3.3% of the account.
```

The cap is also **gap insurance**. Even a stock that opens 80% lower
([expectancy](learn-risk-expectancy.md) §3) cannot take more than a quarter of
the account. When holding through earnings, size the position for a possible
gap, not for the stop ([the calendar guide](learn-macro-calendar.md)).


## From §5 Volatility-based stops (In this app)
In this app:

- **Donchian channel** uses exactly this. The stop is the lower of entry − 2 × ATR(14)
  and entry × (1 − 2%), so never closer than 2%. Size = risk ÷ that distance.
- **Volume breakout** puts its stop under the consolidation, but never wider
  than 2 ATR. **Chart patterns** keeps it between max(0.6 ATR, 1.5%) and 2 ATR.
  **Trend pullback** caps it at 3 ATR. The trend-pullback code explains why
  the cap is in ATRs, not percent: a percentage cap is "a volatility filter
  wearing a risk label". In other words, it only rejects volatile stocks, and
  sizing already buys fewer shares as the stop widens.
- **The backtest's `--exit-mode trail_atr`** option trails the stop. The stop
  sits at the highest close since entry minus 3 × ATR(14) (`--atr-mult`). It is
  only ever raised, and the initial stop is kept for measuring R. It is an exit
  test, not a sizing rule.

A good structural stop (one under a real chart level) is usually 1–3 ATR away.
When the two disagree, the honest choice is the wider stop with fewer shares
([stops and exits](learn-risk-stops-exits.md)).


## From §6 Fixed amounts (US Donchian run)
  so the risk is random.
- **Fixed amount** ("always $10,000"): better, but the risk still scales with
  the stop. In the US Donchian run, the stop ranged from 3.7% (10th percentile)
  to 14.7% (90th) below entry. At a flat $10,000 a trade, that is $370 to $1,470
  of risk — a fourfold range, so the wide-stop trades would dominate the result.
- **"Conviction" sizing** (betting more on the trades you feel best about):

## From §7 Arithmetic of losses (the app's streaks and bootstrap on real R sequences)
Twenty or more losses in a row happened in three of the app's US runs, and 29
in a row in the India Donchian run ([expectancy](learn-risk-expectancy.md) §4).
At 1% that is survivable; at 5% it is the end of the account.

### Drawdowns simulated on real R sequences

To see the whole range of outcomes rather than one streak, take a run's actual
trade results and reshuffle them. The table below uses 10,000 bootstrap
resamples. Each resample draws trades at random from the run's real results
(the same trade can be drawn more than once), as many trades as the run had.
Each resample is played one trade at a time, risking a fixed fraction of the
current account, and its maximum drawdown is recorded. Re-running with other
random seeds moves these figures by about a point.

| Risk per trade | Donchian US (+0.49R, 496 trades): median / 1 in 10 / 1 in 100 | Volume breakout US (+0.04R, 703 trades): median / 1 in 10 / 1 in 100 |
|---|---|---|
| 0.5% | −15% / −23% / −32% | −17% / −27% / −37% |
| 1% | −29% / −41% / −54% | −32% / −48% / −62% |
| 2% | −51% / −68% / −80% | −56% / −75% / −86% |
| 5% | −86% / −96% / −99% | −92% / −99% / −100% |

What it shows:

- **Drawdown roughly doubles with the risk fraction**, while the expectancy in
  R does not change at all.
- **Over-betting turns a winner into a loser.** At 5% a trade, the breakout
  run's median path ends at 0.56× the starting account, despite its positive
  expectancy. The chance of finishing below the start rises from 27% at
  0.5% to 61%. Big losses take away more than big wins add.
- **This is the gentle case.** The simulation takes one trade at a time. Real
  portfolios hold 8–10 positions at once, and they fall together. The actual US
  Donchian backtest fell 49% with an average risk of only about 0.6% a trade.
  That is the subject of [portfolio risk](learn-risk-portfolio.md).


## From §8 Kelly (the app's runs)
## 8. Kelly — the ceiling, not the target

The Kelly criterion gives the fraction of the account to risk that maximises
long-run growth. For a simple win/lose bet, **Kelly % = W − (1 − W) ÷ payoff
ratio**, where W is the win rate and the payoff ratio is the average win
divided by the average loss. The table applies it to the app's runs. Alongside
it is the growth-maximising fraction computed on each run's actual spread of
R results, not just its averages:

| Run | Win rate | Payoff ratio | Simple Kelly | Kelly on the real R distribution |
|---|---|---|---|---|
| Donchian channel, US | 28.6% | 4.2 | 11.8% | 5.0% |
| Minervini SEPA, US | 27.8% | 2.8 | 2.2% | 2.0% |
| Volume breakout, US | 34.3% | 2.0 | 2.0% | 1.8% |

Why traders stay well below it:

- **The inputs are estimates.** For the thin-edge runs (those with only a small
  positive expectancy), the expectancy is within measurement error of zero
  ([expectancy](learn-risk-expectancy.md) §5). So is the true Kelly fraction.
  Betting the estimated Kelly on a zero edge is pure loss.
- **Full Kelly hurts.** Half Kelly gives up about a quarter of the growth rate
  for a much smoother ride. At full Kelly, drawdowns of half the account are
  normal. Practitioners use a quarter to a half of Kelly.
- **The simple formula overstates systems that depend on rare big wins**
  (11.8% against 5.0% for Donchian). An average win hides how rare the big
  ones are.

The app's 1% is about half the estimated Kelly for the thin-edge strategies.
For them, it is not conservative.


## From §9 Adding to winners, cutting size after losers (backtester options and results)
## 9. Adding to winners, and cutting size after losers

**Pyramiding** (adding to a position as it moves in your favour). O'Neil buys
at the pivot and adds in small steps only as the stock rises, not more than
about 5% above the buy point. Minervini starts with a small trial position and
adds once the stock proves itself; only stocks that are working get full size.
The backtester's `--pyramid FRAC --pyramid-add-pct PCT` option buys a fraction
at entry. It places a buy-stop order for the rest a set % higher. One test was
run on the previous Minervini version (v1.5, US, 2010–2026): half at entry
and half 2% higher. It **lowered** expectancy from +0.05R to −0.10R and CAGR from
0.9% to −0.4%, with a slightly deeper drawdown (−44.1% against −42.2%). One
variant on one strategy is not a verdict on pyramiding. But it is a warning:
adding raises the average cost, and many breakouts fail after the add.

**Scaling down after losses.** Minervini calls this "progressive exposure":
trade small while the recent record is poor, and at full size once it pays.
The backtester's `--pe` option risks half the usual fraction in three cases:
while the last 10 closed trades net zero R or less, after two losses in a row,
and for the first 5 trades. On Minervini US (v1.6, 2010–2026) it cut the
maximum drawdown from **−43.5% to −34.6%**, for a CAGR of 0.58% against 0.65%.
It does what it claims: a losing streak costs less, at a small price in return.


## From §10 India specifics (cost modelling in runs)
  STT of 0.1% on both the buy and the sell; stamp duty on the buy; exchange and
  SEBI charges; GST on brokerage and exchange fees; and a depository charge per
  sale. That is roughly 0.2%–0.25% for a round trip (a buy plus a sell) at a
  zero-brokerage broker (check your broker's current schedule). The Minervini
  spec runs model costs of 12bp a side plus 15bp slippage; the other India runs
  model slippage only.
- **Costs grow in R as the stop tightens**: 0.25% is 0.06R on a 4% stop, but
  0.03R on an 8% stop.
- **Price bands.** Many NSE stocks have daily circuit limits of 5%, 10% or 20%:
  the price may not move further than that in a day. A stock locked at its
  lower limit cannot be sold at all that day. That is gap risk under another
  name, and another reason for the position cap.
- **Tax** on short-term capital gains on listed equity (20% since the July 2024
  Budget) is not in any backtest. It lowers every result for a taxable account.

## From §11 What the trader does
3. **Apply a position cap** (the app's 25%) and accept the lower risk when it
   binds; with earnings ahead, size for the gap.
4. **Re-measure the account monthly**, so the 1% follows the equity down and up.
5. **Cut size during a losing streak**, restore it after the record recovers.
6. **Check the total.** A screener run ends by printing "N TRADE rows: … at
   risk, … total position", and whether that fits the account. Open risk
   across all positions is covered in [portfolio risk](learn-risk-portfolio.md).


## From §12 What the evidence says
## 12. What the evidence says

- **Robust:** the loss-recovery arithmetic is exact. Drawdown scales with risk
  per trade, and over-betting destroys a positive edge (the bootstrap, §7).
- **Robust:** Kelly maximises growth only when the odds are known. With
  estimated odds, betting a fraction of Kelly is standard practice (Thorp).
- **Mixed:** progressive exposure cut drawdown at little cost, and one
  pyramiding variant hurt. Both results come from one strategy's backtest. The
  simulations take one trade at a time, so they understate real drawdowns.

