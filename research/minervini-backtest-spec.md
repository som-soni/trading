# Minervini VCP Strategy — Backtest Specification

Oct 8, 2026 · @Som Soni

## 1. Purpose and scope

This spec turns Mark Minervini's long-only swing strategy into rules a computer can test on daily data. A trade happens only when three layers agree, in this order: the stock is in a Stage 2 uptrend (Section 4), it has formed a completed volatility contraction pattern (Section 5), and it meets setup MV-01 or MV-02 (Section 6).

Minervini describes much of his method qualitatively. Where he gives a number (for example, the Trend Template thresholds or the 10% maximum loss), this spec uses it. Where he does not, the spec chooses a reasonable default and marks it **\[assumption\]**. Every assumption is also listed as a parameter in Section 11 so that you can test other values.

Rule IDs follow your existing style: TT for the Trend Template, VCP for base detection, MV for setups, EN for entries, SL for stops and sizing, EX for exits, and PF for portfolio rules. All prices are split- and bonus-adjusted. "Day t" means the trading day being evaluated, and every signal uses only data up to and including the close of day t.

## 2. Data and universe

The backtest needs daily open, high, low, close and volume (OHLCV) for every stock, plus a benchmark index. At least 15 months of history must exist before the first test date, because the 200-day average and the 12-month relative strength need it.

The data must meet four conditions, ordered from the one that most often breaks a backtest to the least:

1. **Survivorship-free.** Include stocks that were later delisted, merged or suspended. A universe of only today's listed stocks overstates returns, because the failures are missing.
2. **Adjusted for corporate actions.** Prices and volumes must be adjusted for splits and bonus issues (Cupid's 2026 bonus is an example). Unadjusted data creates false 50–80% "crashes" that trigger stops.
3. **Point-in-time universe.** On each date, only stocks that were listed and tradable on that date are eligible.
4. **Benchmark series.** Use a broad index for the market filter and relative strength, for example the Nifty 500 for Indian stocks or the S&P 500 for US stocks.

On each day, a stock is in the tradable universe only if it passes these filters:

| ID | Rule | Default |
| --- | --- | --- |
| U-01 | Close price at least a minimum | ₹50 (or $10) **\[assumption\]** |
| U-02 | 50-day average daily traded value (close × volume) at least a minimum | ₹10 crore (or $5 million) **\[assumption\]** |
| U-03 | At least 260 trading days of history | 260 days |
| U-04 | Not suspended, and (India) not in a trade-for-trade or circuit-limited segment that blocks normal fills | Required |

## 3. Indicator definitions

All indicators are computed on day t using data up to day t's close. The table lists them in the order the later rules use them.

| Name | Definition |
| --- | --- |
| SMA50, SMA150, SMA200 | Simple moving average of the close over 50, 150 and 200 days |
| HI52, LO52 | Highest high and lowest low over the last 252 trading days |
| VOL50 | Simple average of volume over the last 50 days |
| ATR14 | 14-day average true range, where true range = max(high − low, abs(high − previous close), abs(low − previous close)) |
| RS\_raw | Weighted return: 0.4 × 63-day return + 0.2 × 126-day return + 0.2 × 189-day return + 0.2 × 252-day return **\[assumption: a common approximation of IBD's RS rating\]** |
| RS | Percentile rank of RS\_raw across the whole tradable universe on day t, from 1 to 99 |
| Swing high / swing low | Defined below |

### Swing points

The base detector in Section 5 needs swing highs and swing lows. A bar is a **swing high** if its high is the highest high of the k bars before it and the k bars after it. A **swing low** is defined the same way using lows. The default is k = 5 **\[assumption\]**.

This definition has a look-ahead trap. A swing point at bar i is only known at the close of bar i + k. In the backtest, a swing point must be treated as unknown until then. Many zig-zag indicators in charting software silently redraw past points; do not use those in a backtest.

To ignore tiny wiggles, keep a swing low only if it is at least 2% below the preceding swing high **\[assumption\]**, except inside the final tight area, where the tightness rules in Section 5 apply instead.

## 4. Stage 2 filter: the Trend Template

A stock is in Stage 2 on day t only if all eight rules below are true on day t. These are Minervini's published Trend Template criteria; only the way "trending up" is measured in TT-03 is an assumption.

| ID | Rule | Formula on day t |
| --- | --- | --- |
| TT-01 | Price above the 150-day and 200-day averages | close > SMA150 and close > SMA200 |
| TT-02 | 150-day average above the 200-day average | SMA150 > SMA200 |
| TT-03 | 200-day average rising for at least one month | SMA200(t) > SMA200(t − 21) **\[assumption: the slope test\]**; stricter variant uses t − 84 for about four months |
| TT-04 | 50-day average above the 150-day and 200-day averages | SMA50 > SMA150 and SMA50 > SMA200 |
| TT-05 | Price above the 50-day average | close > SMA50 |
| TT-06 | Price at least 30% above the 52-week low | close ≥ 1.30 × LO52 |
| TT-07 | Price within 25% of the 52-week high | close ≥ 0.75 × HI52 |
| TT-08 | Relative strength rating of at least 70 | RS ≥ 70 |

TT-05 needs care during a base. A stock can dip below its 50-day average in an early, deep contraction and still form a valid VCP. So the backtest applies the full template in two places: at the **start of the base** (all eight rules) and on the **signal day** (all eight rules). Between those two days, only TT-01 to TT-04 must hold every day **\[assumption\]**. This matches how Minervini screens candidates and then waits for the base to finish.

### Market filter (optional)

Minervini avoids new buys when the general market is weak. Test the strategy with and without this rule:

| ID | Rule |
| --- | --- |
| MKT-01 | Benchmark close > benchmark SMA200, and benchmark SMA50 > benchmark SMA200 **\[assumption\]** |

## 5. Base and VCP detection

A volatility contraction is "complete" on day t when every required rule from VCP-01 to VCP-10 is true (VCP-07 and VCP-11 are optional). This is the hardest part to code, because Minervini judges it by eye. The algorithm below finds the base, measures each contraction, and then checks the final tight area.

### Step 1: find the base and the prior advance

The **base high (BH)** is the most recent confirmed swing high that no later close has exceeded. The base runs from BH's bar to day t. If any close after BH rises above BH, the old base is discarded and a new base starts at the next confirmed swing high.

| ID | Rule | Default |
| --- | --- | --- |
| VCP-01 | Prior advance: BH is at least 30% above the lowest low of the 126 days before BH | 30% **\[assumption, based on Minervini's preference for a strong prior run\]** |
| VCP-02 | Base duration: from BH's bar to day t | 15 to 325 trading days (about 3 to 65 weeks, Minervini's stated range) |
| VCP-03 | The full Trend Template holds on BH's bar | Required |

### Step 2: measure the contractions

Inside the base, pair each swing high with the lowest low before the next swing high. The first contraction starts at BH. For contraction i, with high H\_i and low L\_i, the depth is:

```latex
d_i = \frac{H_i - L_i}{H_i}
```

| ID | Rule | Default |
| --- | --- | --- |
| VCP-04 | Number of contractions | 2 to 6 (Minervini's typical range) |
| VCP-05 | First contraction not too deep: d\_1 ≤ max\_first\_depth | 35% **\[assumption; test up to 50% in volatile markets\]** |
| VCP-06 | Each contraction clearly smaller than the previous: d\_(i+1) ≤ shrink × d\_i | shrink = 0.80 **\[assumption\]**; a looser variant only requires d\_(i+1) < d\_i |
| VCP-07 | Optional: higher lows, L\_(i+1) ≥ L\_i | Off by default; test on and off |

### Step 3: check the final tight area and volume

The **final tight area** is the last n days ending on day t. Its high is the **pivot (P)**, and its low is the **tight low (TL)**.

| ID | Rule | Default |
| --- | --- | --- |
| VCP-08 | Tightness: the final contraction depth is at most 10%, and (P − TL) / P ≤ 10% over the last n days | n = 10 days, 10% **\[assumption, based on Minervini's descriptions\]** |
| VCP-09 | Pivot near the top of the base: P ≥ 0.90 × BH | 0.90 **\[assumption\]** |
| VCP-10 | Volume dry-up: average volume over the final tight area ≤ 0.70 × VOL50 | 0.70 **\[assumption\]** |
| VCP-11 | Optional: volatility shrink, ATR14(t) / close(t) ≤ 0.60 × ATR14 / close on BH's bar | Off by default |

### Base count

Record a **base number** for every completed base, because Minervini treats later bases as riskier. The count resets to zero when TT-01 to TT-04 fail for 20 or more days in a row **\[assumption\]**. It increases by one each time a base produces an MV-01 signal, whether or not you trade it. Report results by base number, and test a filter that allows only bases 1 to 3.

## 6. Setups MV-01 and MV-02

Both setups require the same precondition: on day t the stock passes the Trend Template (TT-01 to TT-08) and has a completed VCP (Section 5). They differ only in where the close sits relative to the pivot P. In time, MV-02 usually comes first and MV-01 follows if the breakout happens.

| ID | Setup | Formal condition on day t |
| --- | --- | --- |
| MV-02 | Coiled: contraction complete, price within 8% below the pivot, not yet through it | 0.92 × P ≤ close(t) ≤ P, and no close above P since the tight area began |
| MV-01 | Breakout: contraction complete and price has closed above the pivot | close(t) > P, close(t − 1) ≤ P, and the VCP was complete on day t − 1 using the pivot P from day t − 1 |

Two details matter when coding MV-01. First, the pivot must be frozen from day t − 1. If you recompute the tight area on the breakout day, the breakout bar becomes part of it and moves the pivot. Second, the breakout day's own volume and range will break the tightness and volume dry-up rules, so those are checked on day t − 1, not day t.

### Breakout confirmation for MV-01

Minervini wants strong volume on a breakout. Apply these filters on day t:

| ID | Rule | Default |
| --- | --- | --- |
| MV-01a | Breakout volume: volume(t) ≥ vol\_mult × VOL50 | 1.4 **\[assumption, based on his "40–50% above average" guidance\]** |
| MV-01b | Not extended: close(t) ≤ 1.05 × P | 5% (Minervini's buy-range guidance) |
| MV-01c | Close in the upper half of the day's range: (close − low) / (high − low) ≥ 0.5 | 0.5 **\[assumption\]** |

## 7. Entry rules

The backtest should support three entry modes and report each separately. They are ordered from the most conservative (fewest false signals, highest entry price) to the most aggressive.

| ID | Mode | Trigger | Fill price | Skip the trade if |
| --- | --- | --- | --- | --- |
| EN-01 | MV-01 confirmed breakout (default) | MV-01 and MV-01a–c true at day t's close | open(t + 1) | open(t + 1) > 1.05 × P, or open(t + 1) ≤ TL |
| EN-02 | MV-02 buy-stop at the pivot | MV-02 true at day t's close; buy-stop placed at P × 1.001 for the next days | max(open, stop price) on the first day high ≥ stop price | fill > 1.05 × P |
| EN-03 | MV-02 early ("cheat") entry | MV-02 true at day t's close | open(t + 1) | open(t + 1) ≤ TL |

Notes on each mode, in the same order:

1. **EN-01** matches your MV-01 rule exactly, because it waits for the close. It gives up some price compared with an intraday entry. A variant that fills at close(t) is acceptable only if you could realistically trade in the last minutes of the session; label it as optimistic.
2. **EN-02** buys the moment the pivot is crossed, which is how Minervini usually trades. The order stays active for up to 10 days **\[assumption\]** while the VCP stays valid. Cancel it if a close falls below TL. Do not filter EN-02 fills on that day's final volume, because you would not know it at the time of the fill; that would be look-ahead bias.
3. **EN-03** buys inside the tight area before any breakout. It has the tightest stop and the most failures. Treat it as a separate experiment.

### Re-entry

| ID | Rule | Default |
| --- | --- | --- |
| EN-04 | One entry per base. After a stop-out, the stock is eligible again only when a new base forms | On **\[assumption\]**; test allowing one re-entry if the same pivot is reclaimed within 10 days |

## 8. Initial stop and position sizing

The stop is set before entry and decides the position size. The rules are applied in the order listed.

| ID | Rule | Default |
| --- | --- | --- |
| SL-01 | Initial stop = TL × (1 − buffer), the low of the final tight area minus a small buffer | buffer = 0.5% **\[assumption\]** |
| SL-02 | Risk per share R = entry price − initial stop | — |
| SL-03 | Maximum risk: skip the trade if R / entry > max\_stop | 8% (Minervini's guideline; 10% is his absolute ceiling) |
| SL-04 | Shares = floor((equity × risk\_pct) / R) | risk\_pct = 1.0% of equity **\[assumption, within Minervini's 1–1.25% range\]** |
| SL-05 | Cap the position value at max\_pos × equity; reduce shares if needed | max\_pos = 25% **\[assumption\]** |
| SL-06 | Skip if the order would exceed 5% of the stock's 50-day average daily traded value | 5% **\[assumption\]** |

The initial stop never moves down. It only moves up, under the exit rules in Section 9.

An example with a ₹10,00,000 account: entry ₹100 and TL ₹94.47 give a stop of ₹94.00 and R = ₹6.00 (6% risk, so SL-03 passes). The share count is 10,000 / 6 = 1,666 shares, worth ₹1,66,600, which is under the 25% cap of ₹2,50,000.

## 9. Exit rules

Each open position is checked every day, in the priority order below. The first three rules are defensive and limit losses. The last four are offensive and manage gains. If two rules fire on the same day, the higher one in the table wins.

| Priority | ID | Rule | Action and fill |
| --- | --- | --- | --- |
| 1 | EX-01 | Stop hit: low(t) ≤ current stop | Sell all at min(open(t), stop). The open is used when the stock gaps below the stop |
| 2 | EX-02 | Failed breakout: within the first 5 days after entry, close(t) < P | Sell all at open(t + 1) **\[assumption\]** |
| 3 | EX-03 | Breakeven: high(t) ≥ entry + 2R | Raise the stop to the entry price plus round-trip costs, effective from day t + 1 **\[assumption: Minervini says two to three times the risk\]** |
| 4 | EX-04 | Partial profit: high(t) ≥ entry + 3R, first time only | Sell one third at entry + 3R, or at open(t) if it gapped above that **\[assumption\]** |
| 5 | EX-05 | Climax run (see the list below) | Sell all remaining shares at open(t + 1) |
| 6 | EX-06 | Trend break: close(t) < SMA50 and volume(t) ≥ VOL50 | Sell all remaining shares at open(t + 1) |
| 7 | EX-07 | Optional time stop: after 20 days, gain < 1R | Sell all at open(t + 1); off by default **\[assumption\]** |

A climax run (EX-05) is flagged on day t when the position is up at least 25% and **any** of these is true **\[assumption: thresholds turn Minervini's qualitative signs into numbers\]**:

1. Day t has the largest one-day percentage gain since entry, and the largest volume since entry.
2. At least 8 of the last 10 days closed up.
3. Close(t) is at least 70% above SMA200.
4. The stock gapped up at least 3% on day t after rising more than 50% since entry.

### Same-day ambiguity

Daily bars do not show the order of prices within a day. If the stop and a profit level are both touched on the same day, assume the stop was hit first. This is pessimistic, but it avoids overstating results. If you have intraday data, use it to resolve these cases instead.

### Exit variants to test

Test these alternatives one at a time against the defaults above: EX-06 with SMA20 instead of SMA50 for fast-moving stocks; EX-04 at 2R or 4R; EX-04 switched off (hold the whole position); and EX-02 with a 3-day or 10-day window.

## 10. Execution, costs and portfolio rules

Signals are computed after day t's close, and orders fill on day t + 1, except stop and buy-stop orders, which fill during day t + 1 when their price is reached. Never fill an order on the same bar whose close generated it.

### Costs

Charge costs on every fill. Indian equity delivery trades carry brokerage, securities transaction tax (STT), exchange charges, GST and stamp duty. The defaults below are approximations; replace them with your broker's actual schedule.

| ID | Cost | Default per side |
| --- | --- | --- |
| C-01 | Statutory and brokerage charges | 0.12% **\[assumption, approximate for Indian delivery trades\]** |
| C-02 | Slippage on market and stop orders | 0.15% for liquid stocks; 0.30% if 50-day traded value is below ₹25 crore **\[assumption\]** |
| C-03 | Circuit limits (India): no fill is possible on a day the stock is locked at its upper or lower circuit | Carry the order to the next day |

C-03 matters more than it looks. A stop can be useless on a day the stock is locked at its lower circuit, so the real loss can be much larger than R.

### Portfolio rules

| ID | Rule | Default |
| --- | --- | --- |
| PF-01 | Starting equity | ₹10,00,000 |
| PF-02 | Maximum open positions | 8 **\[assumption\]** |
| PF-03 | When more signals arrive than free slots, rank by RS (highest first), then by tightness (smallest (P − TL) / P first) | — |
| PF-04 | Total open risk: the sum of (current price − stop) × shares across positions stays under 6% of equity | 6% **\[assumption\]** |
| PF-05 | Uninvested cash earns nothing | 0% (conservative) |
| PF-06 | Market filter MKT-01 blocks new entries but does not force exits | Test on and off |

## 11. Parameters

This table collects every tunable number in one place, in the order the rules use them. "Source" says whether the default comes from Minervini or is an assumption in this spec.

| Parameter | Rule | Default | Test range | Source |
| --- | --- | --- | --- | --- |
| swing\_k | Swing points | 5 bars | 3–7 | Assumption |
| min\_swing\_pct | Swing points | 2% | 1–4% | Assumption |
| tt\_slope\_days | TT-03 | 21 days | 21–84 | Minervini (1 month minimum) |
| rs\_min | TT-08 | 70 | 70–90 | Minervini |
| prior\_advance | VCP-01 | 30% | 25–100% | Assumption |
| base\_days | VCP-02 | 15–325 days | Fixed | Minervini |
| n\_contractions | VCP-04 | 2–6 | 2–4 minimum | Minervini |
| max\_first\_depth | VCP-05 | 35% | 25–50% | Assumption |
| shrink | VCP-06 | 0.80 | 0.60–1.00 | Assumption |
| tight\_days | VCP-08 | 10 | 5–15 | Assumption |
| tight\_pct | VCP-08 | 10% | 6–12% | Assumption |
| pivot\_near\_high | VCP-09 | 0.90 | 0.85–0.95 | Assumption |
| dryup\_ratio | VCP-10 | 0.70 | 0.50–0.85 | Assumption |
| coil\_pct | MV-02 | 8% | Fixed | Your rule |
| vol\_mult | MV-01a | 1.4 | 1.0–2.0 | Minervini (approximate) |
| buy\_range | MV-01b | 5% | 3–7% | Minervini |
| stop\_buffer | SL-01 | 0.5% | 0–1% | Assumption |
| max\_stop | SL-03 | 8% | 6–10% | Minervini |
| risk\_pct | SL-04 | 1.0% | 0.5–1.25% | Minervini range |
| breakeven\_R | EX-03 | 2R | 2–3R | Minervini |
| partial\_R | EX-04 | 3R | 2–4R, or off | Assumption |
| fail\_days | EX-02 | 5 | 3–10 | Assumption |
| trail\_ma | EX-06 | SMA50 | SMA20, SMA50 | Minervini |
| max\_positions | PF-02 | 8 | 4–12 | Assumption |

Avoid tuning many parameters at once. Change one at a time from the defaults, and keep a parameter only if its effect holds in the out-of-sample period described in Section 13.

## 12. Daily loop pseudocode

The loop runs once per trading day. Its order matters: existing positions are handled first, using today's prices, and new signals are generated last, using today's close, so that they can only fill tomorrow.

```
for each trading day t:

    # 1. Fill orders placed yesterday
    for each pending order:
        if order.type == "market_open":         # EN-01, EN-03, and exits at next open
            fill at open[t] (with slippage), unless a skip rule applies
        if order.type == "buy_stop":            # EN-02
            if high[t] >= order.price:
                fill at max(open[t], order.price)
                skip if fill > 1.05 * pivot
            elif days_active > 10 or close[t] < tight_low:
                cancel order

    # 2. Manage open positions (Section 9), in priority order
    for each position:
        if low[t] <= position.stop:                         # EX-01
            sell all at min(open[t], position.stop); continue
        if days_held <= 5 and close[t] < position.pivot:    # EX-02
            queue sell all at open[t+1]; continue
        if high[t] >= entry + 2R:                           # EX-03
            position.stop = max(position.stop, entry + costs)
        if not partial_done and high[t] >= entry + 3R:      # EX-04
            sell 1/3 at max(open[t], entry + 3R); partial_done = True
        if climax(position, t):                             # EX-05
            queue sell all at open[t+1]; continue
        if close[t] < sma50[t] and volume[t] >= vol50[t]:   # EX-06
            queue sell all at open[t+1]

    # 3. Update indicators and bases using data up to close[t]
    update SMA, HI52, LO52, VOL50, ATR14, RS for all stocks
    confirm swing points from bar t - k (never later bars)
    update each stock's base, contractions, tight area, base number

    # 4. Generate new signals
    if market_filter_on and not MKT01(t): skip to next day
    candidates = []
    for each stock in tradable universe:
        if not trend_template(stock, t): continue
        if MV01(stock, t) and MV01a_c(stock, t):
            candidates.append(EN-01 order at open[t+1])
        elif MV02(stock, t):
            candidates.append(EN-02 buy-stop at pivot * 1.001)
    rank candidates by RS, then tightness              # PF-03
    for each candidate while slots and open risk allow:  # PF-02, PF-04
        compute stop and shares (Section 8); skip if stop > 8%
        place order

    # 5. Record equity, exposure and open risk for day t
```

## 13. Metrics, validation and pitfalls

A result is only trustworthy if it is measured fully, tested on data it was not tuned on, and free of the common biases below.

### Metrics to report

Report these for the whole period and broken down by entry mode (EN-01, EN-02, EN-03), by base number, by year, and with the market filter on and off:

| Metric | Why it matters for this strategy |
| --- | --- |
| Number of trades | Fewer than about 100 trades is too small to trust |
| Win rate | Expect it to be modest, often 35–50%; this is normal for the method |
| Average win and average loss, in R | The method depends on wins being several times larger than losses |
| Expectancy in R: win rate × avg win − loss rate × avg loss | The single best summary of edge per trade |
| CAGR and maximum drawdown | Compare with buying and holding the benchmark |
| Profit factor (gross profit ÷ gross loss) | Above 1.5 is generally considered healthy **\[assumption\]** |
| Exposure (average % of equity invested) | Shows how often the strategy is in the market |
| Average holding period for winners and losers | Losers should be held much shorter than winners |
| Share of losses larger than 1.5R | Measures gap and circuit risk beyond the planned stop |

### Validation

Run the checks in this order, from the most basic to the most demanding:

1. **Split the data.** Tune parameters on an in-sample period (for example 2010–2019) and test once on an out-of-sample period (for example 2020–2026) that you never looked at while tuning.
2. **Walk forward.** Re-tune on a rolling window, such as five years, and test on the following year, repeated across the history.
3. **Sensitivity.** Move each parameter one step around its default. A real edge degrades gradually; an edge that disappears with a small change is probably overfitted.
4. **Monte Carlo.** Shuffle the order of trades many times to see the range of possible drawdowns, not just the one history produced.

### Pitfalls

These are ordered from the most common cause of a falsely good backtest to the least:

1. **Look-ahead bias.** The usual sources here are using swing points before they are confirmed, recomputing the pivot with the breakout bar included, and filtering intraday fills on that day's final volume.
2. **Survivorship bias.** Testing only on stocks that exist today.
3. **Unadjusted prices.** Bonus issues and splits that appear as crashes.
4. **Overfitting.** Tuning many thresholds until the past looks perfect.
5. **Ignoring liquidity and circuits.** Small Indian stocks can be impossible to exit at the stop on a circuit-locked day.
6. **Ignoring costs.** With many short losing trades, costs and slippage noticeably reduce results.

This specification is for research and education. Backtest results do not guarantee future returns, and it is not a recommendation to trade.
