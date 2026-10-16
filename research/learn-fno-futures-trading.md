# Trading and hedging with futures — leverage, swing shorts, portfolio hedges and pairs

**In short**

- Futures do four useful jobs for a swing trader: a leveraged long, a short held for days, a hedge for a whole portfolio, and a pair trade between two related stocks.
- In India, a stock future is the practical way to hold a short position overnight. Cash-market short sales must be closed the same day.
- Size every futures trade by contract value and by the loss at the stop, never by the margin. One lot is large, so small accounts often cannot take a trade at all.
- A Nifty futures hedge sized by beta removed most of the market's swing from a diversified basket in our test. On single stocks it removed little.
- Shorts and pairs are hard. In our studies a plain breakdown short was a coin toss, and a quarter of them rallied 10% against the trader within a month.

## 1. The idea

```series
title: Tata Consultancy Services — a breakdown short, February to April 2026
from: 2025-11-01
to: 2026-04-30
tf: D
line: india:TCS.NS | TCS
line: india:TCS.NS@sma50 | 50-day average
line: india:TCS.NS@sma200 | 200-day average
mark: 2026-02-04 | Close below the 20-day low
mark: 2026-04-07 | Trailing stop hit
caption: TCS closed at 2,999 on 4 February 2026, below its 20-day low, with both averages falling. A short future sold at the next open and trailed with a 10-day high stop was closed at 2,482 on 7 April.
```

On 4 February 2026 TCS closed at ₹2,999.1. That was below the lowest price of the previous 20 sessions. The stock was under its long-term average, and both its averages were falling. A trader who wanted to be short could not sell the shares and hold them overnight in India. So the trader sold one lot of TCS futures instead.

The future was sold at the next morning's open, about ₹2,990. Over the next two months TCS fell to about ₹2,350. The trade was closed at ₹2,482 when the price rose above its highest point of the previous 10 sessions. At today's lot of 225 shares, that was a gain of about ₹1.14 lakh on one lot.

That is the core idea of trading with futures. A future lets you take a position that shares alone do not allow — short for days, or a market-wide hedge — and lets you size it without paying the full value upfront.

The four playbooks have four payoff shapes, drawn here with prices from 10:15 on 15 October 2026.

```payoff
title: Leveraged long — one lot of Nifty futures (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22000 24000
leg: buy future @ 22940
caption: Playbook A. A straight line: ₹65 per Nifty point either way. The stop limits the loss only if the price trades through it.
```

```payoff
title: Swing short — one lot of TCS futures (27 Oct 2026 expiry)
underlying: 2369.8
lot: 225
range: 2150 2600
leg: sell future @ 2371.8
caption: Playbook B. The short gains ₹225 for every rupee TCS falls, and its loss has no ceiling on the way up.
```

```payoff
title: Portfolio hedge — shares worth two Nifty lots, with two lots of Nifty futures sold
underlying: 22909.85
lot: 65
range: 22000 24000
leg: buy 2x stock @ 22909.85
leg: sell 2x future @ 22940
caption: Playbook C, for a portfolio that moves exactly with the Nifty. The line is flat: the hedge removes the market's move both ways and locks in the basis. A real portfolio keeps its own moves relative to the Nifty.
```

```payoff
title: Pair trade — ₹10 lakh long one bank, ₹10 lakh short the other
range: 85 115
lot: 10000
leg: buy stock @ 100
caption: Playbook D. The horizontal axis is the long leg's price relative to the short leg's, rebased to 100 at entry. A 5% relative gain earns about ₹50,000, whatever the market does.
```

**Who is on the other side?** For a futures short, the buyer is often an arbitrage fund buying the future against a short in the shares, or a trader betting on a bounce. For a hedge, the other side is someone happy to take market risk for the expected return of stocks. For a pair trade, you are betting that a gap between two similar stocks is a temporary overreaction by other traders. None of these edges is large or guaranteed. The futures contract itself adds no edge; it is a tool for carrying a view efficiently.

## 2. When it works and when it doesn't

**Leveraged longs** work in calm, rising markets, when daily moves are small and trends persist. They fail in volatile markets: in 2020 the Nifty moved more than 2% on 42 sessions. A leveraged long in that year was a series of margin calls.

**Swing shorts** work in broad declines, when many stocks break down together and rallies are weak. They fail in markets that are falling but violent. Bear markets produce the sharpest rallies, and a short future has no ceiling on its loss. In our breakdown study, shorts started while the Nifty was below its 200-day average did *worse* than the rest.

**Portfolio hedges** work when you hold a diversified portfolio and expect a period of market risk: a falling trend, an election result, a policy decision. They do little for one or two stocks, because most of a single stock's movement is its own, not the market's.

**Pair trades** work between companies whose businesses really are similar and whose price ratio wanders around a stable level. They fail when one company is steadily winning — the ratio then trends instead of returning.

**India.** Stock futures exist on about 200 large stocks only, so small and mid-sized companies cannot be shorted for days. Stocks enter a **ban period** when open interest nears the exchange's limit for that stock; only closing trades are allowed until it falls. Stock futures settle by physical delivery. There are no daily price limits on F&O stocks, but their circuit filters in the cash market are flexible and can widen.

**US.** A US trader shorts shares directly by borrowing them, so single-stock futures are not needed. Hedging uses E-mini or Micro E-mini S&P 500 futures, or index ETFs and options. Pairs are traded in shares, long one and short the other.

## 3. The rules

The rules below cover four playbooks. Each condition is written so a program can check it. Every number appears in the parameter table in section 4.

### Universe and filters

- The contract is on NSE's derivatives list and is not in a ban period.
- Use the near-month contract. In the last 3 sessions before its expiry, use the next month.
- The near-month contract's average daily turnover over 20 sessions is at least ₹100 crore.
- The quoted bid–ask spread is at most 0.05% of the price for index futures and 0.10% for stock futures.
- For shorts and pairs: no scheduled results for the company within the next 5 sessions.

### Setup

**A. Leveraged long (index futures).** The Nifty closes above its 50-day average. The 50-day average is above the 200-day average. The 50-day average is higher than 20 sessions earlier.

**B. Swing short (stock futures).** All four must hold at the close:

1. The close is below the 200-day average.
2. The 50-day average is below the 200-day average.
3. The 200-day average is lower than 20 sessions earlier.
4. The stock's 63-session return is below the Nifty's 63-session return.

**C. Portfolio hedge (Nifty futures).** The Nifty closes below its 50-day average, and the 50-day average is lower than 20 sessions earlier. A scheduled event you choose to hedge, such as an election result, is an alternative trigger.

**D. Pair trade (two stock futures).** The two companies are in the same industry. The correlation of their daily returns over 250 sessions is at least 0.6. Compute the log of the price ratio, its 60-session mean and standard deviation, and the z-score — how many standard deviations today's ratio sits from its mean.

### Entry

- **A.** The Nifty closes above its highest close of the previous 20 sessions. Buy the future at the next open.
- **B.** The stock closes below the lowest low of the previous 20 sessions. Sell the future at the next open.
- **C.** Sell Nifty futures at the next open after the trigger. The number of lots is in "Position size" below.
- **D.** The z-score crosses beyond ±2 from inside. Buy the cheap leg and sell the rich leg at the next open. Skip the trade if the z-score has already jumped beyond ±3.
- **All.** Use limit orders near the best price, not market orders, except in the most liquid contracts.

### Initial stop

- **A and B.** Two times the 14-session ATR from the entry price: below it for a long, above it for a short.
- **C.** A hedge has no price stop. Its exit is a rule (below).
- **D.** The z-score reaches ±3 against you, measured at the close.

### Exits

- **A.** Trailing stop at the lowest low of the previous 10 sessions, moved only upward. Also exit on a close below the 50-day average.
- **B.** Trailing stop at the highest high of the previous 10 sessions, moved only downward. Time stop: exit if the trade is not in profit after 15 sessions.
- **C.** Remove the hedge when the Nifty closes above its 50-day average *and* the 50-day is higher than 20 sessions earlier. For an event hedge, remove it after the event.
- **D.** Exit when the z-score returns inside ±0.5. Time stop: exit after 20 sessions whatever the z-score.
- **All.** Never hold a stock future into its expiry week unless you intend delivery. Roll in the last 3 sessions.

### Position size

For directional trades (A and B), the size comes from the stop:

```
risk budget   = capital × risk per trade (0.5%–1%)
risk per lot  = |entry − stop| × lot size
lots          = floor(risk budget / risk per lot)       -- if 0, skip the trade
then check:     contract value of all futures ≤ 1.5 × capital
                margin of all futures         ≤ 30% of capital
                a 10% gap against one stock position costs ≤ 2% of capital
```

The TCS trade shows why accounts must be large. The stop was ₹153 above entry, so the risk per lot of 225 was about ₹34,400. At 1% risk per trade, that needs at least ₹34.4 lakh of capital for one lot.

For the hedge (C), the size comes from beta:

```
lots = portfolio value × portfolio beta / (Nifty futures price × lot size)   -- round to the nearest lot
beta = value-weighted average of each stock's 250-session daily beta against the Nifty
```

For the pair (D), make the two legs equal in rupee value as closely as the lots allow. The value of the larger leg may exceed the smaller by at most 15%.

### Managing the trade

- Settle daily losses in cash. Keep enough free cash that a 5% adverse move does not trigger a margin call.
- Roll before expiry; a short collects the roll spread, a long pays it.
- Before a known event (results, RBI policy, the Budget), decide in advance whether to hold, reduce or close.
- Do not add to a losing futures position. Adding to a winner is allowed only if the combined position still passes the size checks.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Roll window | last 3 sessions (2–5) | When to switch to the next month | Earlier rolls avoid expiry-day noise |
| Minimum turnover | ₹100 crore a day (₹50–500 crore) | Liquidity of the contract | Higher cuts the universe sharply |
| Maximum spread | 0.05% index, 0.10% stock | Cost of entry and exit | Check at your trading time |
| Results blackout | 5 sessions (3–10) | Avoids results-day gaps | Longer blackouts skip more trades |
| Trend averages | 50 and 200 sessions | Defines the trend in A, B and C | 20/100 is faster and noisier |
| Average slope lookback | 20 sessions (10–40) | Whether an average is rising or falling | |
| Relative-return lookback | 63 sessions (40–126) | Weakness against the Nifty in B | |
| Breakout / breakdown window | 20 sessions (10–55) | Entry trigger in A and B | Longer windows trade less |
| ATR length | 14 sessions | Volatility for the stop | |
| Stop multiple | 2 × ATR (1.5–3) | Initial stop in A and B | Tighter means more stop-outs, bigger size |
| Trailing window | 10 sessions (5–20) | Trailing stop in A and B | Longer gives back more, holds longer |
| Time stop (short) | 15 sessions (10–30) | Cuts shorts that go nowhere | |
| Risk per trade | 0.5%–1% of capital | Lots per trade | The main control on drawdown |
| Gross contract-value cap | 1.5 × capital (1–2) | Total leverage | |
| Margin cap | 30% of capital (20%–40%) | Buffer for margin calls | |
| Gap check | 10% gap costs ≤ 2% of capital | Single-stock exposure | Single stocks gap 10% about once a year |
| Beta window | 250 sessions (120–500) | Hedge ratio | Betas drift; re-estimate monthly |
| Pair correlation minimum | 0.6 (0.5–0.8) | Which pairs qualify | |
| Pair z-score window | 60 sessions (40–120) | Mean and spread of the ratio | |
| Pair entry / exit / stop | ±2 / ±0.5 / ±3 | When to open, close and cut | Wider entry trades less, reverts more often |
| Pair time stop | 20 sessions (10–40) | Cuts pairs that do not revert | |
| Pair value mismatch | at most 15% | Rupee neutrality across lots | Lot sizes make exact balance rare |

## 5. Variations

- **Trend following in futures.** Commodity trading advisers hold long and short futures in many markets, following the trend. Moskowitz, Ooi and Pedersen (2012) documented this "time-series momentum" across dozens of futures markets. The guides on [moving-average trend following](learn-strat-ma-trend.md) and [channel breakouts](learn-strat-channel-breakout.md) cover the rules.
- **Hedge ratio by regression.** Ederington (1979) framed hedging as choosing the ratio that minimises the variance of the hedged position. Beta from a regression on daily returns is the equity version of that idea.
- **Partial hedges.** Many investors hedge half the beta-weighted value, keeping some upside, rather than all of it.
- **Put options instead of futures.** A protective put caps the loss but keeps the upside, for a premium (see [Hedging with options](learn-fno-hedging.md)).
- **Pairs by distance or cointegration.** Gatev, Goetzmann and Rouwenhorst (2006) matched pairs by the smallest historical distance between normalised prices, opening at two standard deviations. Others test whether the two prices are cointegrated — tied together in the long run — before trading them.
- **Short selling with a market filter.** Many practitioners short only when the index is below its 200-day average. Our study (section 8) did not support that filter for plain breakdowns, so test it rather than assume it.

## 6. Worked examples

All examples use stored daily cash-market prices. The futures traded a few points away because of the basis. Lot sizes are today's, applied to past dates for illustration.

### Example 1 — TCS, a breakdown short that worked (February–April 2026)

| Step | Date | Detail |
|---|---|---|
| Setup and trigger | 4 Feb 2026 | Close ₹2,999.1, below the 20-session low of ₹3,082.0 |
| Averages | 4 Feb 2026 | 50-day ₹3,203, 200-day ₹3,214 and falling from ₹3,241 |
| Relative return | 4 Feb 2026 | 63 sessions: TCS +0.3%, Nifty +0.7% — slightly weaker |
| Entry | 5 Feb 2026 | Sell one lot (225) at the open, ₹2,990 |
| Initial stop | — | ATR ₹76.5 × 2, so the stop is ₹3,143 |
| Risk | — | ₹153 a share, about ₹34,400 a lot |
| Rolls | late Feb and late Mar | Two rolls into the next month |
| Exit | 7 Apr 2026 | Price rose above the 10-session high, ₹2,482 |
| Result | 40 sessions | +₹508 a share, about +₹1.14 lakh a lot, +3.3R |

The trade worked because a large company kept falling for weeks, without one sharp rally. The 15-session time stop never applied: the trade was in profit throughout. Because the trader was short in contango, each roll also earned the small spread between months.

### Example 2 — Kalyan Jewellers, a short squeezed in two days (June 2026)

```series
title: Kalyan Jewellers — a breakdown short that failed, June–July 2026
from: 2026-04-01
to: 2026-07-31
tf: D
line: india:KALYANKJIL.NS | Kalyan Jewellers
line: india:KALYANKJIL.NS@sma50 | 50-day average
line: india:KALYANKJIL.NS@vol | Volume | pane2 bars
mark: 2026-06-11 | Breakdown
mark: 2026-06-15 | Stop hit
caption: Every short rule was met on 11 June. Two sessions later the stock jumped through the stop, and a month later it was about two-thirds above the breakdown close.
```

| Step | Date | Detail |
|---|---|---|
| Setup and trigger | 11 Jun 2026 | Close ₹330.8, below the 20-session low of ₹337.0 |
| Averages | 11 Jun 2026 | 50-day ₹388.1, 200-day ₹443.9 and falling |
| Relative return | 11 Jun 2026 | 63 sessions: Kalyan −15.8%, Nifty −4.5% |
| Entry | 12 Jun 2026 | Sell one lot (1,350) at the open, ₹338.0 |
| Initial stop | — | ATR ₹13.6 × 2, so the stop is ₹365.2 |
| Exit | 15 Jun 2026 | Opened at ₹352, rose to ₹386.7; stopped at ₹365.2 |
| Result | 2 sessions | −₹27.2 a share, about −₹36,800 a lot, −1R |

On 15 June the stock traded about 39 million shares, nearly five times its 50-day average. A month later, on 15 July, it closed at ₹548.1. A short without a stop, or with a stop moved "just a bit higher", would have lost several times the planned risk. This is what a short squeeze looks like: shorts buying back in a hurry push the price up further.

### Example 3 — hedging a ₹30 lakh portfolio with Nifty futures (January–June 2026)

```series
title: Nifty 50 with the hedge rule, 2026
from: 2025-12-01
to: 2026-07-31
tf: D
line: india:NIFTY50 | Nifty 50
line: india:NIFTY50@sma50 | 50-day average
mark: 2026-01-28 | Hedge on
mark: 2026-06-16 | Hedge off
caption: The hedge went on when the Nifty closed below a falling 50-day average and came off when it closed above a rising one.
```

Suppose an investor holds ₹30 lakh of shares with a beta-weighted beta of 1.1. On 28 January 2026 the Nifty closed at 25,342.8, below its 50-day average of 25,899.5, which was falling.

| Step | Detail |
|---|---|
| Beta-weighted exposure | ₹30 lakh × 1.1 = ₹33 lakh |
| One lot's value | 25,342.8 × 65 = about ₹16.5 lakh |
| Lots to sell | 33 / 16.5 = 2.0, so 2 lots |
| Nifty at the March low (30 Mar) | 22,331.4, down 11.9% |
| Hedge gain at that point | about +₹3.91 lakh |
| Hedge off (16 Jun) | Nifty 23,989.2, above a rising 50-day |
| Hedge gain at the close-out | 1,353.6 points × 130 units = about +₹1.76 lakh |
| Portfolio change expected from beta | about −₹1.76 lakh |

The hedge did what it was built for: at the worst point, the shares were down about ₹3.9 lakh if beta held, and the futures were up about the same. The investor did not have to sell any shares or pay capital-gains tax to get that protection.

The same rule also cost money. From 2025 to September 2026 it put the hedge on five times. Three of the four completed hedges lost between 228 and 708 Nifty points as the market rose while hedged. Before costs, the four completed hedges roughly cancelled out. A hedge is insurance against a deep fall, not a profit engine.

### Example 4 — HDFC Bank against ICICI Bank, a pair (June–July 2026)

```series
title: HDFC Bank divided by ICICI Bank, 2019–2026
from: 2019-01-01
to: 2026-10-14
tf: W
line: india:HDFCBANK.NS / india:ICICIBANK.NS | HDFC Bank / ICICI Bank
mark: 2026-01-06 | z-score −3.8 in one day
mark: 2026-06-11 | Pair entry signal
caption: The ratio fell from about 1.5 to about 0.5 over these years. A pair that trends like this punishes anyone who buys the cheap leg on every dip.
```

On 11 June 2026 the HDFC Bank / ICICI Bank ratio was 0.565, a z-score of −2.49 against its 60-session mean. Their daily returns had a correlation of 0.61 over 250 sessions, just above the minimum.

| Step | Detail |
|---|---|
| Entry (12 Jun open) | Buy 2 lots of HDFC Bank (1,300 shares) at ₹754.7: ₹9.81 lakh |
| | Sell 1 lot of ICICI Bank (700 shares) at ₹1,330.0: ₹9.31 lakh |
| Value mismatch | about 5%, inside the 15% limit |
| Exit signal | 9 Jul 2026, z-score −0.17 |
| Exit (10 Jul open) | HDFC Bank ₹824.0, ICICI Bank ₹1,389.7 |
| HDFC Bank leg | +₹90,090 |
| ICICI Bank leg | −₹41,790 |
| Result before costs | about +₹48,300, in just under the 20-session limit |

Both stocks rose, and the market direction hardly mattered. What paid was HDFC Bank rising faster.

Now look at the long chart. Five months earlier, on 6 January 2026, the z-score jumped to −3.8 in one day. The rules said skip, because the jump was already past the stop. Sixty sessions later the ratio was about 9% lower still. After the June exit it kept falling too, to a low near 0.49 at the end of August.

## 7. Common mistakes

- **Sizing by margin.** "I have ₹2 lakh, the margin is ₹1.8 lakh, so one lot" ignores that one lot is a ₹15 lakh position.
- **Shorting because a stock is "too high".** Shorts that work are usually in stocks already falling, not in strong stocks that look expensive.
- **Moving a short's stop up.** A short squeeze is exactly when the stop matters most, as Kalyan Jewellers showed.
- **Holding a stock future into expiry.** It becomes a delivery obligation of several lakh rupees.
- **Hedging one or two stocks with Nifty futures.** Most of a single stock's movement is its own. The hedge adds a second risk rather than removing the first.
- **Trading pairs that are not pairs.** A falling ratio can be a business losing to a rival, not noise.
- **Ignoring the lot mismatch in pairs.** Two lots of one stock against one of the other may leave a large net bet on the market.
- **Forgetting costs.** STT, brokerage, exchange charges, stamp duty and slippage apply to every leg and every roll.

## 8. What the evidence says

**Short sellers as a group.** Boehmer, Jones and Zhang (2008) found that heavily shorted US stocks went on to underperform, mostly because of institutional short sellers. That is evidence that informed shorting can work. It is not evidence that a simple chart rule can.

**Our breakdown study.** We took today's stock futures list and found every session from 2011 to September 2026 that met setup B and the 20-day-low trigger. Events were spaced at least 20 sessions apart per stock, and days near a price jump larger than 35% (usually a corporate action) were dropped.

| Measure (3,226 events, 209 stocks) | Result |
|---|---|
| Stock lower 20 sessions later | 49% |
| Median 20-session return | about 0% |
| Rallied 5% or more against the short within 20 sessions | 48% |
| Rallied 10% or more against the short within 20 sessions | 25% |
| Fell 10% or more by session 20 | 12% |
| Rose 10% or more by session 20 | 16% |
| Lower after 20 sessions, Nifty above its 200-day | 52% |
| Lower after 20 sessions, Nifty below its 200-day | 44% |

A plain breakdown was a coin toss, and squeezes were common. Whatever edge a short-selling strategy has must come from the stop, the exit and extra filters, which you must test. The sample uses today's survivors, which removes failed companies — a bias against shorts — so the true picture may be a little better.

**Our hedging study.** At every quarter-end from 2010 to mid-2026 we estimated each stock's beta from 250 sessions. We then hedged it with the Nifty for the next 63 sessions, rebalanced daily, before costs.

| Measure (63 quarters, up to 213 stocks) | Result |
|---|---|
| Single stock: median reduction in daily variance | 15% |
| Single stock: share of cases where the hedge reduced variance | 89% |
| Median gap between estimated beta and the next quarter's actual beta | 0.26 |
| Equal-weighted basket of all the stocks: median variance reduction | 75% |
| Basket, quarter after 31 Dec 2019: unhedged / hedged | −31.7% / −3.0% |
| Basket, quarter after 31 Dec 2025: unhedged / hedged | −9.7% / +5.0% |

The hedge worked well on a diversified basket and poorly on single stocks. Beta estimates were noisy, as Blume (1971) found for US stocks decades ago. What remained after hedging was the basket's performance relative to the Nifty, which can be positive or negative.

**Our pair study.** Ten same-industry pairs among large Indian stocks, from 2012 to July 2026, with the entry, exit and stop levels of section 3, gave 688 entries.

| Measure (688 events, 10 pairs) | Result |
|---|---|
| z-score back inside ±0.5 within 20 sessions | 51% |
| z-score reached ±3 before reverting | 24% |
| Trade in profit after 20 sessions, before costs | 56% |
| Median 20-session result, before costs | about +1.0% |
| Worst 5% of 20-session results | −10.4% or worse |

Gatev, Goetzmann and Rouwenhorst (2006) found profits from pair trading in US stocks from 1962 to 2002. Do and Faff (2010) found those profits had shrunk in later years. Our small Indian sample shows a slight edge before costs and a fat left tail. Costs on four legs and the lot mismatch could erase it.

## 9. Building and testing it yourself

**Data.** Daily open, high, low and close for the stocks and the Nifty, adjusted for splits and bonuses. A history of which stocks were in the F&O list on each date, and their lot sizes. Results dates. Ideally, historical futures prices to measure the basis; otherwise cash prices plus an assumed basis.

**Look-ahead traps.** Signals are computed at the close and filled at the next open. A trailing stop uses only bars before today. Betas and z-scores use only past data. The F&O list must be the one in force at the time, not today's.

**Survivorship.** Today's F&O list leaves out stocks that collapsed or were removed. For shorts this hides some of the best trades; for longs and hedges it flatters results.

**Costs (approximate, India).** Per round trip on a futures position, count brokerage, exchange transaction charges and STT on the sell side (0.05% of the contract value since 1 April 2026). Also count GST on brokerage and fees, stamp duty on the buy side and SEBI fees. Add slippage of at least one tick each way, and the bid–ask spread on every roll. Pairs pay all of this on two legs.

**Margin and cash.** Model the daily cash flow. A test that ignores margin calls can show a path no real account would survive.

**Parameters to test.** The breakdown window, the stop multiple, the trailing window and the time stop for shorts; the beta window and the hedge trigger for hedges; the z-score window and thresholds for pairs. Change one at a time over a broad grid. Prefer a region of parameters that all work over one sharp peak.

**What a good test reports.**

- Number of trades and win rate.
- Average win and loss in R.
- Expectancy per trade after costs.
- Maximum drawdown, the worst single trade and the longest losing streak.
- Results split by market regime and by time period.

```
for each session t:
    for each stock in the F&O list on date t:
        if not in ban period and turnover ok and no results in next 5 sessions:
            if close < sma200 and sma50 < sma200 and sma200 < sma200[t-20]
               and ret63(stock) < ret63(nifty)
               and close < min(low[t-20 .. t-1]):
                entry = open[t+1]; stop = entry + 2 * atr14[t]
                lots = floor(capital * risk / ((stop - entry) * lot_size))
                if lots >= 1 and caps ok: open short at entry
    for each open short:
        trail = min(trail, max(high[t-10 .. t-1]))
        if high[t] >= trail: exit at max(trail, open[t])
        elif sessions_held >= 15 and price >= entry: exit at close
        if days_to_expiry <= 3: roll to next month
```

## 10. Checklist

- [ ] The contract is liquid, not in a ban period, and I am in the right month.
- [ ] Every setup condition is met at the close, and the trigger has fired.
- [ ] I know my stop in rupees per lot, and the lot count follows from my risk budget.
- [ ] Total contract value, margin and the 10% gap check are inside my limits.
- [ ] No results for this company in the next 5 sessions, or I have decided what to do.
- [ ] I know the expiry date and when I will roll; I will not hold a stock future into expiry.
- [ ] For a hedge: beta is fresh and the lot count matches my portfolio.
- [ ] For a pair: same industry, correlation above the minimum, legs within 15% in value.
- [ ] I have cash beyond the margin for a bad week.

Related guides: [Futures basics](learn-fno-futures-basics.md), [Futures basis and open interest](learn-fno-futures-basis.md), the [map of this section](learn-fno-overview.md), [Position sizing](learn-risk-sizing.md), [Stops and exits](learn-risk-stops-exits.md) and [Portfolio risk](learn-risk-portfolio.md). For F&O-wide sizing see [Risk and position sizing in F&O](learn-fno-risk-sizing.md), and for costs see [India's rules, costs and tax](learn-fno-india-rules.md).

## Further reading

- Ekkehart Boehmer, Charles M. Jones and Xiaoyan Zhang, "Which Shorts Are Informed?", *Journal of Finance*, 2008.
- Marshall E. Blume, "On the Assessment of Risk", *Journal of Finance*, 1971.
- Louis H. Ederington, "The Hedging Performance of the New Futures Markets", *Journal of Finance*, 1979.
- Evan Gatev, William N. Goetzmann and K. Geert Rouwenhorst, "Pairs Trading: Performance of a Relative-Value Arbitrage Rule", *Review of Financial Studies*, 2006.
- Binh Do and Robert Faff, "Does Simple Pairs Trading Still Work?", *Financial Analysts Journal*, 2010.
- Tobias J. Moskowitz, Yao Hua Ooi and Lasse Heje Pedersen, "Time Series Momentum", *Journal of Financial Economics*, 2012.
- John C. Hull, *Options, Futures, and Other Derivatives* — chapters on hedging strategies using futures.
