# Position sizing — how many shares, decided by the stop

Learning material: how much to buy. Fixed-fractional risk, the one formula
that turns a stop into a share count, the app's sizing exactly as coded (and
how often its position cap overrides it), volatility-based stops, why fixed
share counts and fixed amounts fail, the arithmetic of losses and risk of
ruin simulated on this app's own trades, Kelly as an upper bound, adding to
winners and cutting size after losers, and the Indian specifics. Second of
four risk guides: read [expectancy](learn-risk-expectancy.md) first; then
[stops and exits](learn-risk-stops-exits.md) and
[portfolio risk](learn-risk-portfolio.md).

**Where this shows in the app.** Sizing is `core/sizing.py`, with the account
settings in `config/us.py` and `config/india.py`. Every screener row is sized:
on Strategies → (a strategy) → **Setups today**, the *Columns* menu adds
`shares`, `position_value` and `usd_at_risk` next to the default *Entry*,
*Stop* and *Risk %* (the stop's distance below the entry). The backtester sizes
every trade the same way (`backtesting/portfolio_sim.py`), and each backtest's
Trades tab lists the `shares` and `notional` it bought.

---

## 1. Fixed-fractional risk — decide the loss first

The professional answer to "how much should I buy?" starts somewhere else:
**how much am I willing to lose if the stop is hit?** Set that as a fixed
fraction of the account — typically **0.5% to 1%**, rarely above 2% — and let
the share count follow from the stop.

A fraction rather than a fixed sum, because **losses shrink as the account
shrinks** (a losing streak decays it rather than emptying it), **gains
compound**, and **every trade carries the same weight** — which is what makes
expectancy in R ([expectancy](learn-risk-expectancy.md)) turn into money.

## 2. The formula

> **Shares = risk amount ÷ (entry − stop)**, rounded down.
> Risk amount = account × risk %.

The app's configured accounts are **$50,000** (US) and **₹20,00,000** (India),
each at **1%** risk: $500 and ₹20,000 a trade.

**US, $50,000 account, $500 risk.** Buy at $100.

| Stop | Risk per share | Shares | Position | Share of account | Loss if stopped |
|---|---|---|---|---|---|
| $92 (8% below) | $8 | 62 | $6,200 | 12% | $496 |
| $95 (5% below) | $5 | 100 | $10,000 | 20% | $500 |
| $96 (4% below) | $4 | 125 | $12,500 | 25% | $500 |

**India, ₹20,00,000 account, ₹20,000 risk.** Buy at ₹1,500.

| Stop | Risk per share | Shares | Position | Share of account | Loss if stopped |
|---|---|---|---|---|---|
| ₹1,380 (8% below) | ₹120 | 166 | ₹2,49,000 | 12% | ₹19,920 |
| ₹1,410 (6% below) | ₹90 | 222 | ₹3,33,000 | 17% | ₹19,980 |
| ₹1,440 (4% below) | ₹60 | 333 | ₹4,99,500 | 25% | ₹19,980 |

The key line: **a tighter stop means more shares, not more risk.** The loss if
stopped is the same in every row; only the position grows. What changes with
a tight stop is the *probability* of being stopped by noise, and — as §4
shows — the damage a gap can do.

## 3. The app's sizing, exactly as coded

`size_position` in `core/sizing.py`:

1. **Risk amount** = `account_size` × `risk_pct` (1%), or × `risk_pct_high_vol`
   (0.5%) when the volatility index closed above its threshold — VIX 25 in
   the US, India VIX 20 ([the volatility guide](learn-health-volatility.md)
   covers when that happens).
2. **Shares** = floor(risk amount ÷ (entry − stop)).
3. **The cap.** If shares × entry exceeds `max_position_pct` (25%) of the
   account, shares = floor(25% of the account ÷ entry), and the row reports
   the smaller **actual** amount at risk.
4. **Too large for account.** If the result is under one share, the trade is
   flagged. The breakout, trend pullback, Donchian and chart-pattern
   strategies then grade it *WATCH – WAIT* with the reason "too large for
   account". With the configured accounts that takes a share price above a
   quarter of the account, or a risk per share above $500 / ₹20,000.

### When the cap binds

At 1% risk and a 25% cap, the arithmetic is simple: **the cap binds whenever
the stop is less than 4% below the entry** (1% ÷ 25%). In high volatility, at
0.5% risk, only below 2%. A trade with a 3% stop then risks 0.75%, not 1%.

How often that happened in the backtests (each strategy's current-version
full run; risk measured against equity on the day before entry):

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
can need 250% of the account, so when cash runs short the simulator buys what
the cash allows rather than skipping the breakout — a smaller position, so
less than the intended risk, never more (`portfolio_sim.py`). Across these runs
the average risk actually taken was 0.63%–0.86% of equity in the US runs and
0.80%–0.99% in India, not the nominal 1%.

Also: **the live screener sizes off the configured account**, the backtest off
current equity (so it compounds); and **the backtest always sizes at 1%** — it
passes `vix_above_threshold=False`, so the high-volatility halving is untested.

## 4. Why the cap matters: gaps

The formula assumes the stop fills at the stop. A gap below it fills at the
open, and then **the loss scales with the position, not with the risk**. A
tight stop gives a big position, and a big position is what a gap punishes:

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

The cap is also **gap insurance**: even a stock that opens 80% lower
([expectancy](learn-risk-expectancy.md) §3) cannot take more than a quarter of
the account. Through earnings, size for the gap, not the stop
([the calendar guide](learn-macro-calendar.md)).

## 5. Volatility-based (ATR) stops and sizing

An alternative to a stop under a chart level is a stop a fixed number of
**average true ranges** below the entry. ATR(14) is the stock's typical daily
range, so an ATR stop sits outside its normal noise, and fixed-fractional
sizing then gives every position **the same risk in volatility units**: a
calm stock gets more shares, a wild one fewer. This is the Turtles' "N" sizing.

In this app:

- **Donchian channel** uses exactly this: stop = the lower of entry − 2 × ATR(14)
  and entry × (1 − 2%), so never closer than 2%; size = risk ÷ that distance.
- **Volume breakout** puts its stop under the consolidation but never wider
  than 2 ATR; **Chart patterns** keeps it between max(0.6 ATR, 1.5%) and 2 ATR;
  **Trend pullback** caps it at 3 ATR. The trend-pullback code explains why
  the cap is in ATRs, not percent: a percentage cap is "a volatility filter
  wearing a risk label", and sizing already buys fewer shares as the stop
  widens.
- **The backtest's `--exit-mode trail_atr`** trails the stop at the highest
  close since entry minus 3 × ATR(14) (`--atr-mult`), only ever raising it and
  keeping the initial stop for R. It is an exit test, not a sizing rule.

A good structural stop is usually 1–3 ATR away; when the two disagree, the
wider stop with fewer shares is the honest choice
([stops and exits](learn-risk-stops-exits.md)).

## 6. Why not fixed shares or fixed amounts

- **Fixed share count** ("always 100 shares"): ignores both price and stop;
  the risk is random.
- **Fixed amount** ("always $10,000"): better, but the risk still scales with
  the stop. In the US Donchian run the stop ranged from 3.7% (10th percentile)
  to 14.7% (90th) below entry; at a flat $10,000 a trade that is $370 to $1,470
  of risk — fourfold, so wide-stop trades would dominate the result.
- **"Conviction" sizing**: the trades you feel best about are not measurably
  better. Let conviction decide whether to trade, the stop how much.

## 7. The arithmetic of losses

Losses and gains are not symmetric:

| Loss | Gain needed to recover |
|---|---|
| 10% | 11% |
| 20% | 25% |
| 30% | 43% |
| 50% | 100% |
| 75% | 300% |

And a losing streak compounds against the fraction risked:

| Risk per trade | After 10 losses | After 20 losses | After 29 losses |
|---|---|---|---|
| 0.5% | −4.9% | −9.5% | −13.5% |
| 1% | −9.6% | −18.2% | −25.3% |
| 2% | −18.3% | −33.2% | −44.4% |
| 5% | −40.1% | −64.2% | −77.4% |

Twenty or more losses in a row happened in three of the app's US runs, and 29
in India Donchian ([expectancy](learn-risk-expectancy.md) §4). At 1% that is survivable;
at 5% it is the end of the account.

### Drawdowns simulated on real R sequences

To see the whole range rather than one streak, take a run's actual trade
results and reshuffle them: 10,000 bootstrap resamples (drawn with
replacement, the same number of trades as the run), each played one trade at a
time at a fixed fraction of current equity, recording the maximum drawdown.
Re-running with other random seeds moves these by about a point.

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
  run's median path ends at 0.56× the starting equity despite its positive
  expectancy, and the chance of finishing below the start rises from 27% at
  0.5% to 61%. Big losses compound away more than big wins add.
- **This is the gentle case.** The simulation takes one trade at a time. Real
  books hold 8–10 positions together, and they fall together: the actual US
  Donchian backtest fell 49% with an average risk of only about 0.6% a trade.
  That is the subject of [portfolio risk](learn-risk-portfolio.md).

## 8. Kelly — the ceiling, not the target

The Kelly criterion gives the fraction that maximises long-run growth. For a
simple win/lose bet, **Kelly % = W − (1 − W) ÷ payoff ratio**. On the app's
runs, with the log-growth-maximising fraction computed on the actual R
distribution alongside:

| Run | Win rate | Payoff ratio | Simple Kelly | Kelly on the real R distribution |
|---|---|---|---|---|
| Donchian channel, US | 28.6% | 4.2 | 11.8% | 5.0% |
| Minervini SEPA, US | 27.8% | 2.8 | 2.2% | 2.0% |
| Volume breakout, US | 34.3% | 2.0 | 2.0% | 1.8% |

Why traders stay well below it:

- **The inputs are estimates.** For the thin-edge runs the expectancy is within
  error of zero ([expectancy](learn-risk-expectancy.md) §5), and so is the true
  Kelly fraction. Betting the estimated Kelly on a zero edge is pure loss.
- **Full Kelly hurts.** Half Kelly gives up about a quarter of the growth rate
  for a much smoother ride; at full Kelly, drawdowns of half the account are
  normal. Practitioners use a quarter to a half.
- **The simple formula overstates fat-tailed systems** (11.8% against 5.0%
  for Donchian), because an average win hides how rare the big ones are.

The app's 1% is about half the estimated Kelly for the thin-edge strategies —
not conservative for them.

## 9. Adding to winners, and cutting size after losers

**Pyramiding.** O'Neil buys at the pivot and adds in small steps only as the
stock rises, not more than about 5% above the buy point; Minervini starts with
a pilot position and adds on proof — full size only in stocks that are
working. The backtester's `--pyramid FRAC --pyramid-add-pct PCT` takes a
fraction at entry and rests a buy-stop for the rest a set % higher. One test, on the previous Minervini version (v1.5, US, 2010–2026): half at entry
and half 2% higher **lowered** expectancy from +0.05R to −0.10R and CAGR from
0.9% to −0.4%, with a slightly deeper drawdown (−44.1% against −42.2%). One
variant on one strategy is not a verdict on pyramiding, but it is a warning
that adding raises the average cost and many breakouts fail after the add.

**Scaling down after losses.** Minervini's "progressive exposure": trade small
while the recent record is poor, full size once it pays. The backtester's
`--pe`: risk half the fraction while the last 10 closed trades net zero R or
less, after two losses in a row, and for the first 5 trades. On Minervini US
(v1.6, 2010–2026) it cut the maximum drawdown from **−43.5% to −34.6%** for a
CAGR of 0.58% against 0.65%. It does what it claims: a losing streak costs
less, at a small price in return.

## 10. India specifics

- **No lot sizes in the cash market.** Lot sizes apply to futures and options;
  delivery equity trades in single shares, so the formula works unchanged.
- **Costs are larger than in the US.** For delivery trades: STT of 0.1% on both
  the buy and the sell, stamp duty on the buy, exchange and SEBI charges, GST on
  brokerage and exchange fees, and a depository charge per sale — roughly
  0.2%–0.25% a round trip at a zero-brokerage broker (check your broker's
  current schedule). The Minervini spec runs model 12bp a side plus 15bp
  slippage; the other India runs model slippage only.
- **Costs grow in R as the stop tightens**: 0.25% is 0.06R on a 4% stop,
  0.03R on an 8% stop.
- **Price bands.** Many NSE stocks have 5%, 10% or 20% daily circuit limits; a
  stock locked at its lower circuit cannot be sold at all that day. That is gap
  risk by another name — another reason for the position cap.
- **Tax** (short-term capital gains on listed equity, 20% since the July 2024
  Budget) is not in any backtest; it lowers every result for a taxable account.

## 11. What the trader does

1. **Fix the risk per trade** — 0.5%–1%; halve it in high volatility or a
   market below its 200-day ([the trend guide](learn-health-trend.md)).
2. **Place the stop where the idea is wrong**, then compute shares from it.
   Never move the stop to get a bigger position.
3. **Apply a position cap** (the app's 25%) and accept the lower risk when it
   binds; with earnings ahead, size for the gap.
4. **Re-measure the account monthly**, so the 1% follows the equity down and up.
5. **Cut size during a losing streak**, restore it after the record recovers.
6. **Check the total**: a screener run ends by printing "N TRADE rows: … at
   risk, … total position", and whether that fits the account;
   open risk across positions belongs to [portfolio risk](learn-risk-portfolio.md).

## 12. What the evidence says

- **Robust:** the loss-recovery arithmetic is exact; drawdown scales with risk
  per trade, and over-betting destroys a positive edge (the bootstrap, §7).
- **Robust:** Kelly maximises growth only with known odds; with estimated odds,
  fractional Kelly is standard practice (Thorp).
- **Mixed:** progressive exposure cut drawdown at little cost; one pyramiding
  variant hurt — both on one strategy's backtest. The simulations take one
  trade at a time, so they understate real drawdowns.

## 13. Checklist

- [ ] Risk % for the week set (1%, or 0.5% in high volatility / weak market)
- [ ] Every entry: shares = risk ÷ (entry − stop), rounded down
- [ ] Position under the 25% cap; actual risk noted when the cap binds
- [ ] Earnings or results inside the holding period? Size for the gap or skip
- [ ] After a losing streak: size reduced until the last 10 trades are net positive

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — position sizing.
- Ralph Vince, *The Mathematics of Money Management* — fixed-fractional
  sizing, optimal f and drawdowns.
- Edward O. Thorp, "The Kelly Criterion in Blackjack, Sports Betting and the
  Stock Market" (2006).
- Curtis Faith, *Way of the Turtle* — N (ATR) based stops and unit sizing.
- William O'Neil, *How to Make Money in Stocks*; Mark Minervini, *Trade Like a
  Stock Market Wizard* — pyramiding and progressive exposure.
