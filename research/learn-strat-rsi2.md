# RSI(2) mean reversion — buying short, sharp dips in an uptrend

**In short**

- Larry Connors' rule: when the price is above its 200-day average and the 2-day RSI falls below 5 or 10, buy at the close. Sell on the first close above the 5-day average.
- It buys a few days of selling inside a longer uptrend, and usually holds for 1 to 5 days.
- On the S&P 500 ETF since 1993 and the Nifty 50 since 2007, these signals were followed by better-than-average 5-day returns. The edge per trade is small, and in the US it was smaller after 2009 than before.
- Connors argued against stop losses for this trade. The cost is a rare, very large loss, especially in single stocks hit by news.
- It works better on broad indices than on single stocks, because an index cannot fall apart on one company's bad news.

This guide belongs to the mean-reversion group, with [Bollinger band reversion](learn-strat-bollinger-reversion.md) and [gap fills](learn-strat-gap-fills.md). How RSI is computed is covered in [momentum indicators](learn-price-oscillators.md).

## 1. The idea

### An example first

On 30 May 2024 the Nifty 50 closed at 22,488.65, after several down days in the run-up to India's general election results. The index was well above its 200-day average of about 21,010. Its 2-day RSI was 4.1: almost every bit of movement over the last two days had been down.

```series
title: Nifty 50 — an RSI(2) signal in May 2024
from: 2024-03-01
to: 2024-07-31
line: india:NIFTY50 | Nifty 50
line: india:NIFTY50@sma5 | 5-day average
line: india:NIFTY50@rsi2 | 2-day RSI | pane2
mark: 2024-05-30 | RSI(2) 4.1, above the 200-day
caption: The 2-day RSI fell to 4.1 on 30 May 2024. Two sessions later the index closed far above its 5-day average.
```

A buyer at that close sold two sessions later, on 3 June 2024, when the index closed above its 5-day average at 23,263.90. That was a gain of 3.45%. The jump came from exit polls released over the weekend. Most signals earn far less, and a few lose; section 6 shows one.

### How the 2-day RSI gets so low

RSI averages the up-moves and the down-moves separately, then compares them. With a 2-day setting, the averages are very short. One down day after an up day gives a middling value. Three down closes in a row, with no up close between them, push the up-move average close to zero. The RSI then falls to single digits.

| Close sequence (illustrative) | Approximate 2-day RSI |
|---|---|
| Up, up, up | Above 90 |
| Up, down | Around 30 to 50 |
| Down, down | Around 10 |
| Down, down, down | Below 5 |

So "RSI(2) below 5" is, in practice, "three or more lower closes in a row, with the last ones large". With the trend filter, the signal appeared on roughly 6 to 9 days a year on the two indices studied below.

### What the trade is

**RSI** compares the size of recent up-moves with recent down-moves, on a scale from 0 to 100. The usual setting looks back 14 days. Connors shortened it to 2 days. A 2-day RSI near 0 means the last two or three closes were all lower, with no bounce in between.

The rule has three parts:

- A trend filter: only buy when the close is above the 200-day simple average.
- A trigger: the 2-day RSI closes below a threshold, usually 5 or 10.
- An exit: sell on the first close above the 5-day simple average.

### Why it can work

Short-term reversal in stock prices is one of the oldest findings in finance. Narasimhan Jegadeesh (1990) and Bruce Lehmann (1990) found that stocks that fell over a week or a month tended to rebound in the next. Stefan Nagel (2012) explained it as a payment for supplying liquidity. When many investors sell at once, buyers who step in earn a small premium for taking the shares.

The trend filter matters. In an uptrend, a dip is more often a pause than the start of a decline. Connors and Cesar Alvarez reported that the same signal below the 200-day average was weaker.

### Who is on the other side

The sellers are investors cutting risk after a few bad days, funds meeting withdrawals, and short-term traders whose stops were hit. They pay a small price to sell immediately. You are the buyer who takes their shares, and you are paid if the selling stops soon.

## 2. When it works and when it doesn't

**Broad indices.** An index holds many companies, so one company's disaster moves it little. Its dips are mostly from market-wide selling, which tends to reverse. A single stock can fall because of news that changes its value for good. Then the dip does not reverse.

**Calm, rising markets.** The strategy does best when the index is in a steady uptrend and volatility is moderate. It does worst at the start of a bear market. The index is still above its 200-day average, the RSI signals fire, and the decline continues for weeks. February 2020 was such a period.

**Volatile periods.** Nagel's work suggests reversal profits are larger when volatility is high, because liquidity is scarce. But so are the losses.

**India.** The Nifty 50 can be traded through index ETFs (exchange-traded funds that hold the index) or Nifty futures. ETFs settle T+1 and have lower costs than a basket of shares. Futures need margin and roll each month. Short trades (the reverse rule, selling when RSI is above 95 below the 200-day) need futures. In single stocks, results days and circuit limits create sudden falls the rule cannot see.

**US.** Liquid index ETFs make the trade cheap. Connors tested it mainly on the S&P 500 and on US stocks.

## 3. The rules

### Universe and filters

- Index ETFs or index futures (Nifty 50, Nifty Bank, S&P 500, Nasdaq 100).
- For single stocks: price above ₹100 or $10, 20-day average traded value above ₹20 crore or $20 million, and in a large-cap index.
- No results announcement in the next 5 sessions (single stocks).

### Setup

- The close is above its 200-day simple average (*trend average*).
- Optional: the 200-day average is higher than 20 sessions ago.

### Entry

- Trigger: the 2-day RSI (Wilder's method) closes below 5 (*entry threshold*; 10 gives more trades).
- Order: buy at the close, using a market-on-close order or a buy in the last minutes, when the RSI is all but certain. The practical alternative is the next open; test both.

### Initial stop

Connors argued against stops, and his tests showed stops reduced returns. Choose one of these and test it:

- No price stop, but a **time stop** (below) and a small position.
- A **catastrophe stop**: sell on a close below the 200-day average, or 3 ATRs below the entry.

### Exits

- **Target:** sell on the first close above the 5-day simple average (*exit average*).
- **Alternative target:** the 2-day RSI closes above 65 or 70.
- **Time stop:** sell after 10 sessions if neither has happened (*maximum hold*).

### Position size

- Indices: a fixed share of capital per signal, for example 20% to 50%, with no leverage.
- Single stocks: size so that a 10% drop costs at most 0.5% to 1% of capital. That means a position of 5% to 10% of capital.

### Managing the trade

- **Adding:** Some versions add a second unit if the price closes lower while still in the trade. Adding raises the average gain and the worst losses. Decide in advance; never add on impulse.
- If the index closes below its 200-day average during the trade, the trend filter has failed. Many traders exit then.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| RSI length | 2 (2–4) | How short the dip is | 3 or 4 gives fewer, deeper signals |
| *Entry threshold* | 5 (2–10) | How oversold before buying | 10 doubles the number of signals |
| *Trend average* | 200-day (100–200) | The uptrend filter | Removes the worst bear-market signals |
| *Exit average* | 5-day (3–10) | When the bounce is taken | Longer averages hold longer |
| RSI exit | 65–70 | Alternative exit | |
| *Maximum hold* | 10 sessions (5–15) | Time stop | Most trades end within 5 sessions |
| Catastrophe stop | Close below the 200-day, or 3 ATR | Limits rare large losses | Lowers the win rate; test it |
| Position size | 20–50% (index), 5–10% (stock) | Exposure per signal | |

## 5. Variations

- **Connors' original rules.** In *Short Term Trading Strategies That Work* (2008), Connors and Alvarez test the 2-day RSI with the 200-day filter and the 5-day exit. A chapter there is titled "Stops Hurt".
- **Cumulative RSI.** Add the last two days of 2-day RSI values and buy when the sum is below 35. This waits for a dip of two days or more.
- **Double 7s.** Buy when the index closes at a 7-day low, above its 200-day average. Sell when it closes at a 7-day high. It is the same idea without RSI.
- **The short side.** Sell short below the 200-day average when the 2-day RSI is above 95. On stored data the long side was stronger (section 8).
- **ETF versions.** Connors and Alvarez's *High Probability ETF Trading* (2009) applies similar rules to many ETFs, including bond and sector ETFs.

## 6. Worked examples

### Nifty 50, May 2024 (India): it worked

| Step | Date | Value |
|---|---|---|
| Signal | 30 May 2024 | Close 22,488.65; 2-day RSI 4.1; 200-day average about 21,010 |
| Entry | Close, 30 May 2024 | 22,488.65 |
| Exit | 3 Jun 2024 | First close above the 5-day average: 23,263.90 |
| Result | 2 sessions | +3.45% |

### Nifty 50, January 2026 (India): it failed

The 2-day RSI fell to 4.6 on 8 January 2026, with the index at 25,876.85. It was above its 200-day average of about 25,040. The index did not close above its 5-day average until 28 January, 12 sessions later.

```series
title: Nifty 50 — an RSI(2) signal that failed, January 2026
from: 2025-11-01
to: 2026-03-31
line: india:NIFTY50 | Nifty 50
line: india:NIFTY50@sma200 | 200-day average
line: india:NIFTY50@rsi2 | 2-day RSI | pane2
mark: 2026-01-08 | RSI(2) 4.6
caption: The dip kept going. The exit came 12 sessions later at a small loss, and the index then fell much further.
```

| Step | Date | Value |
|---|---|---|
| Entry | Close, 8 Jan 2026 | 25,876.85 |
| Worst close during the trade | | 3.2% below the entry |
| Exit | 28 Jan 2026 | 25,342.75: −2.06% |

A 10-session time stop would have sold on 23 January at 25,048.65. That loss, 3.2%, was worse than waiting for the exit. After the exit, the index fell to 22,330 by the end of March 2026, about 15% below its January high. The rule was out by then, because the close was below the 200-day average.

### Adani Enterprises, January 2023 (India): a single stock with no stop

On 23 January 2023 Adani Enterprises closed at 3,436.35. Its 2-day RSI was 3.7. The close was well above the 200-day average of about 3,030, so every condition was met.

```series
title: Adani Enterprises — an RSI(2) signal before a collapse, January 2023
from: 2022-11-01
to: 2023-03-31
line: india:ADANIENT.NS | Adani Enterprises
line: india:ADANIENT.NS@sma200 | 200-day average
line: india:ADANIENT.NS@rsi2 | 2-day RSI | pane2
mark: 2023-01-23 | RSI(2) 3.7, above the 200-day
caption: A short-seller's report on the group came out the next day. The stock lost more than half its value within two weeks.
```

| Step | Date | Value |
|---|---|---|
| Entry | Close, 23 Jan 2023 | 3,436.35 |
| Close below the 200-day average | 27 Jan 2023 | 2,761.45: −19.6% |
| Lowest close | 2 Feb 2023 | 1,565.25: −54.4% |
| Exit on a close above the 5-day average | 7 Feb 2023 | 1,802.95: −47.5% |

The report by Hindenburg Research appeared on 24 January 2023. A catastrophe stop on a close below the 200-day average would have lost 19.6%. With no stop, the trade lost 47.5%. One such trade can erase dozens of small wins. This is why the rule is safer on an index.

## 7. Common mistakes

- **Trading it on single stocks at index size.** A stock can fall 20% overnight on news. Size each stock trade for that.
- **Ignoring results dates.** A stock that is "oversold" the day before results is a bet on the results.
- **Adding stops that are too tight.** A 2% stop on a dip-buying trade sells exactly the dips the rule is meant to buy. If you use a stop, make it wide.
- **Dropping the trend filter.** Below the 200-day average, dips in India became weaker after 2017 (section 8).
- **Over-tuning the thresholds.** RSI below 3 or below 7 will each look best in some period. Pick a round value and keep it.
- **Forgetting costs.** The average gain per trade is about half a percent. Costs of 0.2% take a large share of it.

## 8. What the evidence says

**Published research.** Short-term reversal is well documented in stocks (Jegadeesh 1990; Lehmann 1990), with Nagel (2012) linking it to liquidity provision. Connors and Alvarez published many tests of the RSI rule on US indices and stocks; those are their own backtests.

**Event study on stored data: indices.** Each day, I checked whether the close was above the 200-day average and where the 2-day RSI closed. I then measured the next 5 sessions' return, and the return to the first close above the 5-day average. The S&P 500 ETF data are price only, without dividends. Signals on consecutive days count separately.

| Index, period | Group | Days | Average 5-day return | Up after 5 days | Average return to the exit | Exit in profit |
|---|---|---|---|---|---|---|
| S&P 500 ETF, 1993–2026 | All days above the 200-day | 6,197 | +0.20% | 59% | | |
| | RSI(2) below 10 | 451 | +0.66% | 66% | +0.64% | 77% |
| | RSI(2) below 5 | 200 | +0.56% | 65% | +0.62% | 78% |
| Nifty 50, 2007–2026 | All days above the 200-day | 3,193 | +0.21% | 57% | | |
| | RSI(2) below 10 | 324 | +0.41% | 57% | +0.42% | 68% |
| | RSI(2) below 5 | 173 | +0.62% | 60% | +0.49% | 67% |

By period, for RSI(2) below 5 above the 200-day:

| Index | Earlier period | Average return to exit | Exit in profit | Later period | Average return to exit | Exit in profit |
|---|---|---|---|---|---|---|
| S&P 500 ETF | 1993–2009 (70 days) | +1.20% | 86% | 2010–2026 (130 days) | +0.31% | 73% |
| Nifty 50 | 2008–2016 (77 days) | +0.51% | 62% | 2017–2026 (96 days) | +0.49% | 71% |

The trend filter mattered in India. Since 2017, the same signal on the Nifty 50 below the long-term average was followed, on average, by a slight loss over the next week (−0.07%).

**Event study: single stocks.** The same signal on liquid stocks (US since 2004, India since 2004, today's stock lists):

| Market | Group | Signal days | Average 5-day return | Up after 5 days | Fell 10%+ within 5 days | Average return to the exit |
|---|---|---|---|---|---|---|
| US | All days above the 200-day | 4,847,530 | +0.15% | 52% | 6.4% | |
| US | RSI(2) below 5 | 207,271 | +0.47% | 55% | 7.1% | +0.51% |
| India | All days above the 200-day | 1,263,382 | +0.35% | 50% | 8.1% | |
| India | RSI(2) below 5 | 63,859 | +0.77% | 55% | 9.8% | +0.78% |

"Fell 10%+" means the low of any of the next 5 sessions was 10% or more below the signal close.

**What this says.** The signal added about 0.3 to 0.5 percentage points over 5 days, in both indices and stocks. On the S&P 500 ETF it was much stronger before 2010 than after. In single stocks the average looks similar. But 7% to 10% of stock signals saw a fall of a tenth or more within days. Index signals had no such tail: the worst 5-day loss after a Nifty 50 signal was 4.2%.

**Caveats.** Signal days overlap, so the samples are smaller than they look. The stock lists are today's (survivorship bias), which flatters dip-buying. No costs are included.

## 9. Building and testing it yourself

**Data.** Daily closes are enough for the index version. For stocks, add highs and lows (for stops), results dates, and delisted stocks.

**Look-ahead traps.**
- Buying "at the close" on a signal computed from that close assumes you can act in the last minutes. If you cannot, test entry at the next open.
- Compute RSI and averages only from data up to the signal day.

**Survivorship.** Dip-buying in today's surviving stocks looks better than it was. Stocks that kept falling and were delisted are missing.

**Costs (India, approximate).** For Nifty ETFs, brokerage near zero at discount brokers, small exchange charges, and a bid-ask spread of a few hundredths of a percent in the most liquid ones. For Nifty futures, a small STT on the sell side and exchange charges; margin is required. For stocks in delivery, about 0.25% to 0.35% per round trip. At 30 to 50 trades a year, costs add up.

**Parameters to test.** The entry threshold, 5 or 10. The exit average, from 3 to 10 days. The trend filter on or off, and the catastrophe stop on or off. Look for a broad area of good results, not one best point.

**What a good test reports.** Number of trades, average trade after costs, win rate, the worst trade, the worst month, time in the market, and results by period.

```
for each day t:
    if close[t] > sma(close, 200)[t] and rsi(close, 2)[t] < entry_threshold:
        buy at close[t]
        hold until: close > sma(close, 5)
                    or held 10 sessions
                    or (optional) close < sma(close, 200)
```

## 10. Checklist

- [ ] Is the instrument an index ETF or future, or a large, liquid stock?
- [ ] Is the close above the 200-day average?
- [ ] Is the 2-day RSI below my threshold at the close?
- [ ] For a stock: are results or other scheduled news due in the next 5 sessions?
- [ ] Is my position sized for a 10% to 20% overnight drop?
- [ ] Do I know my exit (first close above the 5-day) and my time stop?
- [ ] Have I decided, before the trade, whether I use a catastrophe stop?

## Further reading

- Larry Connors and Cesar Alvarez, *Short Term Trading Strategies That Work* (TradingMarkets, 2008).
- Larry Connors and Cesar Alvarez, *High Probability ETF Trading* (2009).
- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the original RSI.
- Narasimhan Jegadeesh, "Evidence of Predictable Behavior of Security Returns", *Journal of Finance* (1990).
- Bruce Lehmann, "Fads, Martingales, and Market Efficiency", *Quarterly Journal of Economics* (1990).
- Stefan Nagel, "Evaporating Liquidity", *Review of Financial Studies* (2012).
