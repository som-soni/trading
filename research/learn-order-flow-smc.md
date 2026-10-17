# Order flow, smart money concepts and liquidity — what the terms mean, and what holds up

**In short**

- Order flow is the stream of buy and sell orders behind every price bar. You see it in the order book, the list of trades, footprint charts and volume profiles. A daily chart shows none of it.
- To a trader, "liquidity" often means resting orders: stop-losses and breakout orders bunched just beyond obvious highs, lows and round numbers. A large trader needs those orders to fill a big position.
- Smart money concepts (SMC) is a newer vocabulary for older ideas. A liquidity sweep is Wyckoff's spring. An order block is a demand or supply zone. A fair value gap is a gap. A change of character is Dow theory's first lower low.
- Research on order flow is real: over seconds to days, order imbalance moves prices, and stop orders bunched at round numbers can speed up a move. SMC as a trading system has no published evidence behind it.
- On liquid Indian and US stocks since 2012, daily "sweeps" and "fair value gaps" did not predict the following weeks better than an ordinary day did. Learn the words, then test any rule before you trust it.

This guide follows [Supply and demand](learn-supply-demand.md), which explains why price levels matter. Here we look underneath those levels, at the orders themselves. Then we translate the vocabulary from trading videos into plain words.

One warning about a word. "Liquidity" here means orders waiting at a price, or how easily you can trade without moving it. It does not mean the money that central banks create. That meaning is in [Liquidity and credit](learn-macro-liquidity-credit.md).

---

## 1. Order flow — the auction behind every bar

### Who crosses the spread

Here is an invented order book for a stock trading near ₹500. Each row is a price where people have placed limit orders and are waiting.

*Synthetic example — invented numbers to show how the tool reads. Not market data.*

| Level | Buyers waiting (shares) | Bid price | Ask price | Sellers waiting (shares) |
|---|---|---|---|---|
| 1 | 1,200 | ₹499.90 | ₹500.00 | 800 |
| 2 | 2,500 | ₹499.85 | ₹500.05 | 1,500 |
| 3 | 900 | ₹499.80 | ₹500.10 | 6,000 |
| 4 | 3,100 | ₹499.75 | ₹500.15 | 1,100 |
| 5 | 1,800 | ₹499.70 | ₹500.20 | 2,000 |

The best bid is ₹499.90 and the best ask is ₹500.00. The gap between them is the bid-ask spread. Nothing trades while both sides only wait.

Now someone sends a market buy order for 2,000 shares. It takes the 800 shares offered at ₹500.00. It then takes 1,200 of the 1,500 offered at ₹500.05. The last trade prints at ₹500.05, and the best ask is now ₹500.05.

That buyer is the **aggressor**: the trader who crossed the spread and accepted the other side's price. The sellers who were waiting are **passive**: they set a price and let others come to them.

Every trade has one buyer and one seller. What moves the price is which side is the aggressor, and how much is waiting at each price. [Volume](learn-price-volume.md) makes the same point for daily bars.

### The order book, or depth of market

The table above is the **order book**. Trading screens call it **depth of market (DOM)**: the waiting buy and sell orders at each price near the current one.

Look at level 3 on the ask side: 6,000 shares at ₹500.10. That is a wall of sellers. A buyer must take all of it before the price can rise past ₹500.10. Depth readers watch whether such walls get eaten, pulled or added to.

The book shows only orders people chose to show. Large traders often hide their size, and orders can be cancelled in a fraction of a second. So the book is a snapshot of intentions, not a promise.

### Time and sales — the trade log

**Time and sales**, often called "the tape", is the list of every trade as it happens: time, price and quantity. Many screens also mark whether the trade happened at the bid or at the ask. A trade at the ask means a buyer crossed the spread; a trade at the bid means a seller did.

*Synthetic example — invented numbers to show how the tool reads. Not market data.*

| Time | Price | Shares | Who crossed the spread |
|---|---|---|---|
| 10:15:01 | ₹500.00 | 300 | Buyer (traded at the ask) |
| 10:15:01 | ₹500.00 | 500 | Buyer |
| 10:15:02 | ₹500.05 | 1,200 | Buyer |
| 10:15:04 | ₹500.00 | 400 | Seller (traded at the bid) |
| 10:15:05 | ₹500.00 | 600 | Seller |
| 10:15:07 | ₹500.05 | 900 | Buyer |

Buyers crossed the spread for 2,900 shares in these six seconds. Sellers crossed for 1,000. The difference is called delta.

### Footprint charts, delta and absorption

A **footprint chart** splits each bar by price. At every price it shows two numbers: shares sold to the bid (aggressive sellers) and shares bought at the ask (aggressive buyers). Read each cell as "sold × bought".

*Synthetic example — three invented five-minute bars. Not market data.*

| Price | Bar 1 (rises) | Bar 2 (stalls) | Bar 3 (falls, then recovers) |
|---|---|---|---|
| ₹500.25 | | 700 × 260 | |
| ₹500.20 | 120 × 640 | 950 × 820 | |
| ₹500.15 | 300 × 900 | 880 × 900 | 200 × 450 |
| ₹500.10 | 410 × 1,050 | 640 × 610 | 520 × 700 |
| ₹500.05 | 380 × 700 | 300 × 150 | 1,400 × 380 |
| ₹500.00 | 250 × 310 | | 4,800 × 350 |
| ₹499.95 | | | 900 × 120 |
| **Delta (bought − sold)** | **+2,140** | **−730** | **−5,820** |
| **Cumulative delta** | +2,140 | +1,410 | −4,410 |

**Delta** is aggressive buying minus aggressive selling within a bar. **Cumulative delta** adds it up bar after bar. In bar 1, buyers did most of the crossing, and the price rose. In bar 2, sellers did a little more, and the price stalled.

Bar 3 is the interesting one. Sellers hit the bid for 4,800 shares at ₹500.00, yet the price did not fall through it. Someone with large buy orders at ₹500.00 took everything. This is **absorption**: heavy aggressive selling that fails to move the price, because a large passive buyer soaks it up.

Absorption can be read either way. A buyer who absorbs and then holds the level is bullish. A buyer whose orders run out lets the price drop fast. The footprint shows the fight, not who wins.

### Icebergs and spoofing

An **iceberg order** shows only a small part of its size. When the visible part fills, the next part appears at the same price. In bar 3 above, a buyer showing 500 shares at a time at ₹500.00 could have been an iceberg. On NSE the same idea is called a disclosed quantity: you show only part of your order.

**Spoofing** is placing large orders you intend to cancel, to make others think demand or supply is there. It is illegal. The US Dodd-Frank Act names it explicitly, and SEBI treats it as market manipulation in India. A wall in the book that vanishes as price nears it may be spoofing, or may be an honest trader changing their mind. You cannot tell from the screen.

### Volume profile

A **volume profile** turns the chart sideways. It adds up the volume traded at each price over a period, such as a day or a month.

*Synthetic example — invented volumes over 20 sessions. Not market data.*

| Price band | Volume (lakh shares) | |
|---|---|---|
| ₹520–525 | 4 | |
| ₹515–520 | 9 | |
| ₹510–515 | 18 | Value area |
| ₹505–510 | 31 | Point of control |
| ₹500–505 | 22 | Value area |
| ₹495–500 | 11 | |
| ₹490–495 | 5 | |

The **point of control** is the price band with the most volume: here ₹505–510. The **value area** is the range around it that holds about 70% of the volume. Here that is ₹500–515, which holds 71% of the volume.

Profile traders read the value area as the price the market accepted. A move away from it on low volume is often pulled back. A move away that builds new volume at new prices suggests the market has accepted a new level. The idea comes from Market Profile, developed at the Chicago Board of Trade in the 1980s. [VWAP strategies](learn-strat-vwap.md) uses a related average.

### What a daily chart cannot show

A daily bar has five numbers: open, high, low, close and volume. It cannot show who crossed the spread, how much was waiting at each price, or where the volume traded inside the bar. Everything in this section needs intraday data, and most of it needs tick data (every single trade).

**India notes.**

- NSE shows five levels of the order book free on most trading screens. Some broker platforms offer twenty levels.
- Historical tick data is sold by the exchange and data vendors. It is costly for an individual.
- Order-flow tools for index and stock futures exist on several Indian platforms. Futures trade on one exchange, so one order book shows all the trading. A stock trades on both NSE and BSE.

## 2. "Liquidity" in the trader's sense

Imagine a stock that has twice bounced at ₹480. Traders who bought those bounces put their stop-loss at ₹478. Traders waiting to short a breakdown put sell orders there too. By now, thousands of sell orders wait just below ₹480.

To a fund that wants to buy a large position, that pile is useful. A big buyer needs sellers. Buying 5 lakh shares at once in a quiet market would push the price up against itself. But if the price dips to ₹478, all those stops turn into market sell orders. The fund can fill its buy order against them without paying up.

That pile of waiting orders is what SMC traders call **liquidity**. Stops of long holders sit below obvious lows; to a buyer they are a source of shares. Stops of short sellers sit above obvious highs; they are buy orders, which a large seller can sell into.

**Where the pools sit.** Just beyond places everyone can see:

- prior swing highs and lows, especially **equal highs or equal lows** (two or three turns at the same price);
- round numbers such as ₹1,000 or $50;
- the edges of a trading range, the prior day's high and low, and a 52-week high.

```pattern
equal-highs
```

**Three meanings of one word.** Keep them apart:

| Meaning | What it is | Where it is covered |
|---|---|---|
| Resting orders ("liquidity pools") | Stop and limit orders waiting beyond visible levels | This guide |
| Market liquidity | How easily you can trade without moving the price: spread and depth | This guide, section 1 |
| Macro liquidity | How much money central banks and banks create | [Liquidity and credit](learn-macro-liquidity-credit.md) |

## 3. Smart money concepts — the vocabulary, and the older names

Smart money concepts (SMC) is a set of chart terms popular in online trading videos. Much of the vocabulary was spread by a trader who teaches as "ICT", the Inner Circle Trader. Each term below is shown with a drawing, the idea in plain words, and the older idea it renames. The drawings are idealised, not market data.

### 3.1 Market structure — break of structure and change of character

```pattern
bos-choch
```

In an uptrend, each rally makes a higher high and each pullback a higher low. When a rally rises past the last swing high, SMC calls it a **break of structure (BOS)**. It says the trend is continuing.

The first time a decline instead falls below the last higher low, SMC calls it a **change of character (CHoCH)**. It is the first sign that the uptrend may be over.

**The older name.** This is Dow theory's swing structure, more than a century old. An uptrend is higher highs and higher lows; a lower high followed by a lower low is the warning. [Stages and trend in a stock](learn-price-stages.md) uses the same swing structure to place a stock in its larger trend.

The weak point is the definition of a swing. A swing high with two lower bars on each side gives many swings. One with ten bars on each side gives few. Fix the number before you label a chart.

### 3.2 Liquidity sweeps — stop hunts

```pattern
liquidity-sweep
```

A **liquidity sweep**, also called a stop hunt or liquidity grab, is a push beyond an obvious high or low that closes back inside. The push fills the stops waiting there. The close back inside shows that the move found no follow-through.

Here is a real one. On 2 January 2025 Trent made a high of ₹7,336, its highest in four weeks. The next day it traded up to ₹7,493, above that high, but closed at ₹7,308, back below it. Twenty sessions later the stock closed at ₹5,753, 21% lower.

```series
title: Trent — a push above a four-week high that closed back below, January 2025
from: 2024-11-01
to: 2025-03-14
tf: D
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma50 | 50-day average
line: india:TRENT.NS@vol | Volume | pane2 bars
mark: 2025-01-02 | high ₹7,336
mark: 2025-01-03 | above it to ₹7,493, close ₹7,308
mark: 2025-01-31 | ₹5,753
caption: The day's high cleared the prior four-week high, but the close did not. The fall that followed came with a weak Indian market in January.
```

Now the contrast: a breakout that held. On 2 January 2024 Sun Pharma closed at ₹1,296, above its four-week high of ₹1,272. Volume was about 1.7 times its 50-day average. It never closed back below that level over the next three months. By 29 February it closed at ₹1,578, about 22% higher.

```series
title: Sun Pharma — a close above a four-week high that held, January 2024
from: 2023-11-01
to: 2024-03-28
tf: D
line: india:SUNPHARMA.NS | Sun Pharma | log
line: india:SUNPHARMA.NS@sma50 | 50-day average
line: india:SUNPHARMA.NS@vol | Volume | pane2 bars
mark: 2024-01-02 | close ₹1,296, above ₹1,272
mark: 2024-02-29 | ₹1,578
caption: Both stocks took out the stops above a recent high. One closed above the level and kept going; the other closed back below it and fell.
```

The difference between the two was the close. Only the close tells a sweep from a breakout, and only afterwards. Section 4 measures whether the close-back-inside day predicts anything across thousands of cases.

**The older names.** Wyckoff called a push below support that recovers a **spring**, and a push above resistance that fails an **upthrust**. Chart readers call them bear traps and bull traps. The full trade on the short side is in [Failed breakouts and bull traps](learn-strat-failed-breakouts.md).

### 3.3 Order blocks

```pattern
order-block
```

An **order block** is the last opposite-colour candle before a strong move. For a bullish block, it is the last down candle before a rally that breaks a prior high. SMC traders mark that candle's range and expect buyers to return there. The story is that large buyers placed orders in that candle and still have some unfilled.

**The older name.** This is a **demand zone**: the short pause a strong rally left from. A bearish order block is a supply zone. [Supply and demand](learn-supply-demand.md) explains how to judge one. Look for a fast departure, little time at the level, and a fresh, first return.

The catch is that every rally has a last down candle. So after the fact, every turn on every chart has an order block under it. A rule is only useful if you can apply it before the price returns, and count the blocks that failed.

### 3.4 Fair value gaps

```pattern
fair-value-gap
```

A **fair value gap (FVG)**, or imbalance, is a three-bar pattern left by a fast move. In a bullish one, the third bar's low is above the first bar's high. The middle bar moved so fast that, across the range between them, little trading happened. SMC traders expect the price to return into that range, and often to buy there.

**The older name.** A classical **gap** is a jump between one bar's range and the next. The fair value gap widens the idea to a fast bar that ran through a range in one go. The old saying "gaps get filled" becomes "fair value gaps get filled". [Gap fills and gap trading](learn-strat-gap-fills.md) covers the classical version.

### 3.5 Premium and discount

Take a swing from ₹400 up to ₹500. Its midpoint is ₹450. SMC calls prices above the midpoint **premium** and prices below it **discount**. The rule of thumb is to buy only in discount, after a pullback, and to sell only in premium.

**The older name.** This is the 50% retracement, one of the oldest pullback rules. [Retracements and measured moves](learn-strat-retracements.md) covers it, along with the Fibonacci levels some SMC traders add.

### 3.6 Inducement, and "smart money" against "retail"

**Inducement** is a small, obvious level that draws traders in early. Think of a minor pullback low inside a larger move. Traders buy it and put stops under it; the price then sweeps those stops before the real move starts. It is a liquidity sweep on a smaller scale.

The whole vocabulary rests on one story: large "smart money" players hunt the stops of small "retail" traders. Parts of that story are true. Large orders need someone on the other side, and stops do cluster at obvious levels.

But on a chart, the story is an interpretation, not an observation. A daily bar does not say who traded. A push above a high may be a fund filling a sell order, or many small traders chasing a breakout, or a news headline. Without account-level data, nobody can tell. Calling every reversal a stop hunt explains everything after the fact and predicts nothing.

**The vocabulary at a glance.**

| SMC term | What it describes | The older name |
|---|---|---|
| Break of structure (BOS) | Price passes the last swing point with the trend | Higher high in Dow theory |
| Change of character (CHoCH) | First break of the last swing against the trend | First lower low; trend change in Dow theory |
| Liquidity sweep, stop hunt | Push beyond a high or low that closes back inside | Wyckoff's spring or upthrust; bull or bear trap |
| Liquidity pool, equal highs or lows | Resting stops beyond visible levels | Support and resistance; stop clusters |
| Order block | Last opposite candle before a strong move | Demand or supply zone |
| Fair value gap, imbalance | Three-bar gap left by a fast move | Gap; "gaps get filled" |
| Premium and discount | Above or below the 50% of a swing | 50% retracement |
| Inducement | A minor level that traps early traders | A small failed breakout or breakdown |

## 4. What the evidence says

### Published research on order flow

The study of how orders turn into prices is called **market microstructure**, and it is a serious field.

- **Informed trading.** Albert Kyle's 1985 model shows how a trader with private information trades gradually, hiding among ordinary orders. Prices move in proportion to the net order flow, because market makers learn from it.
- **Order imbalance and returns.** Chordia and Subrahmanyam (2004) found that daily order imbalance in US stocks, more buyer-started than seller-started trades, was followed by positive returns the next day. They traced it to large traders splitting orders over several days.
- **The order book and price changes.** Cont, Kukanov and Stoikov (2014) found that over seconds, price changes are explained mainly by the imbalance between orders arriving at the best bid and the best ask. The thinner the book, the bigger the effect.
- **Stops at round numbers.** Carol Osler studied currency orders at a large bank. She found that take-profit orders cluster at round numbers, and stop-loss orders cluster just beyond them (2003). When stop clusters are triggered, prices move faster in the same direction, a price cascade (2005).

So the core ideas hold: order imbalance moves prices, and stops gather beyond obvious levels. But these effects are short-lived. Most are measured over seconds to a day, with tick data, and the edge mostly goes to those with the fastest access and lowest costs.

### Smart money concepts as a system

There is little or no peer-reviewed research on SMC as a trading method. Its sources are mostly practitioner courses and online videos. Rules differ from one teacher to the next, and many are not specified tightly enough to test. That does not make the ideas wrong. It means any claims about how well they work come from the people selling them.

### An event study on daily data

We tested the two SMC patterns that can be defined on daily bars: the sweep and the fair value gap.

> **Method note.** Daily prices for today's NSE and US stock lists, 2012 to September 2026. A stock-day counts if the 20-day average traded value is at least ₹10 crore or $20 million and the close is at least ₹50 or $5. That leaves 1,726 Indian and 3,479 US stocks. A **sweep of the highs** is a day whose high is above the highest high of the prior 20 sessions but whose close is below it. A **breakout** is a day that closes above that level. The low side is the mirror. A **bullish fair value gap** is a day whose low is above the high of the day two sessions earlier. It is **filled** when a later low trades back to that earlier high. Returns run from the event day's close. "Against the day's median" subtracts the median return of all qualifying stocks from the same day. Caveats: today's stock lists leave out delisted companies (survivorship bias); the windows overlap; no costs.

**Sweeps.** India first:

| India, 2012–2026 | Days | 5-day median return | 5 days, against the day's median | 20-day median return | 20 days, against the day's median | Higher after 20 days |
|---|---|---|---|---|---|---|
| All qualifying days | 1,352,073 | +0.01% | 0.00% | +0.34% | 0.00% | 51.5% |
| Sweep of the highs (close back below) | 92,830 | −0.16% | −0.12% | +0.37% | −0.03% | 51.5% |
| Breakout (close above the high) | 81,825 | −0.08% | −0.13% | +0.44% | −0.02% | 52.3% |
| Sweep of the lows (close back above) | 56,560 | +0.32% | +0.02% | +0.42% | −0.03% | 51.9% |
| Breakdown (close below the low) | 61,345 | +0.50% | +0.24% | +0.61% | +0.09% | 52.7% |

| US, 2012–2026 | Days | 5-day median return | 5 days, against the day's median | 20-day median return | 20 days, against the day's median | Higher after 20 days |
|---|---|---|---|---|---|---|
| All qualifying days | 4,302,075 | +0.23% | 0.00% | +0.71% | 0.00% | 53.6% |
| Sweep of the highs (close back below) | 281,066 | +0.17% | +0.01% | +0.60% | +0.04% | 53.4% |
| Breakout (close above the high) | 314,802 | +0.06% | −0.03% | +0.46% | −0.04% | 52.6% |
| Sweep of the lows (close back above) | 199,876 | +0.36% | +0.03% | +1.02% | +0.01% | 54.8% |
| Breakdown (close below the low) | 229,131 | +0.44% | +0.07% | +1.17% | +0.08% | 55.3% |

What this shows:

- **A sweep of the highs was not a sell signal.** In India it lagged the typical stock by about a tenth of a percent over five days. After 20 days the gap was gone. In the US there was no gap at all.
- **A sweep looked no different from a real breakout.** Both groups ended up close to the market. Trent's fall and Sun Pharma's rise in section 3.2 are single cases, not a rule.
- **A sweep of the lows was not a special buy signal.** Stocks that closed *below* the low bounced a little more than those that swept it and closed back above. That is ordinary short-term rebound after a fall.
- Requiring a weak close, in the lower half of the day's range, did not change these results.

**Fair value gaps.**

| Bullish fair value gaps | India | US |
|---|---|---|
| Gaps found | 162,339 | 642,280 |
| Share of all qualifying days | 12.0% | 14.9% |
| Median gap size, % of the close | 1.18% | 0.89% |
| Filled within 5 sessions | 48.3% | 50.8% |
| A level as far below the close, reached within 5 sessions | 47.1% | 50.1% |
| Filled within 20 sessions | 70.5% | 72.2% |
| A level as far below the close, reached within 20 sessions | 68.3% | 69.3% |
| Filled within 60 sessions | 81.4% | 83.0% |
| A level as far below the close, reached within 60 sessions | 79.7% | 80.2% |
| 20-day return against the day's median | −0.10% | −0.01% |

The comparison rows ask a simple question. Pick any day and a price as far below the close as the gap's far edge was. How often did the stock trade down to it?

- **Fair value gaps are everywhere.** One trading day in seven or eight leaves one on a daily chart.
- **Most get filled, but so does any nearby level.** About 70% were filled within 20 sessions, only two to three points more than an arbitrary level the same distance away.
- **Large gaps, 2% or more of the price, filled more often than chance.** Within 20 sessions, 56.9% of them filled in India against 49.8% for an equally distant level; in the US, 55.9% against 44.8%. Part of this may simply be that stocks with big gaps are more volatile, so they reach every level more often.
- **Gaps did not point the way.** The 20-day return after a bullish gap was close to the typical stock's.

**Round numbers.** Osler's work on round numbers used currency order books. We did not test it on daily stock data, because a daily high or low is too coarse to show a cluster of orders a few paise away.

**What is unknown.** Whether these patterns work better on intraday charts, with volume or order-flow filters, or in certain market conditions. Practitioners say they do. Those claims have not been published in a form anyone can check. [Backtesting honestly](learn-test-backtesting.md) explains how to test one yourself.

## 5. What daily charts can and cannot do

You can approximate some of this from daily open, high, low, close and volume:

| What you want to know | Daily approximation | What it misses |
|---|---|---|
| Did buyers or sellers control the day? | Close location: (close − low) ÷ (high − low) | Who crossed the spread, and when |
| Was a level rejected? | A long wick beyond the level, and a close back inside | Whether stops were really there |
| Was the push heavy? | Volume on the sweep day against the 50-day average | Whether the volume came at the extreme or elsewhere in the bar |
| Was there a fast move? | Gaps and three-bar gaps | Where the volume traded inside the bar |
| Where did trading concentrate? | A volume profile built from daily closes | The real distribution inside each day |

Real order flow needs intraday data: footprint and delta need every trade with its side. Depth of market needs the live order book. Neither exists in daily data, however it is drawn.

## 6. What can go wrong

- **Hindsight labels.** Every swing has a last opposite candle, a gap and a sweep somewhere nearby. After the fact, each turn looks like a textbook order block. Write the level down before the price returns, and count the misses.
- **Too many zones.** Mark every block, gap and pool on several timeframes, and some zone will sit under every price. Then the chart explains everything and predicts nothing. Limit yourself to one or two levels that matter.
- **Rules that cannot be tested.** "Price will return to the order block, unless it is a breaker block" can never be wrong. If you cannot write a rule as a condition a computer could check, you cannot know whether it works.
- **Paying for tick data before you have an edge.** Footprint charts and data feeds cost money every month. Test simple daily rules first. Buy the detail when you know which question it answers.
- **Treating every move as manipulation.** Ordinary order flow, a fund buying over days or stops being triggered, is not market abuse. Spoofing and other manipulation are crimes, and they are rarely visible on your chart. Believing in a hidden hand makes losses feel personal and stops you checking your own rules.
- **Using the story instead of the stop.** "They swept the lows, so now it goes up" is not a reason to widen a stop. A sweep that keeps going is a breakdown. See [Stops and exits](learn-risk-stops-exits.md).

## 7. Checklist

- [ ] I can say what each term means in plain words, and which older idea it renames.
- [ ] I know which meaning of "liquidity" I am using: resting orders, ease of trading, or central-bank money.
- [ ] My level was marked before the price reached it, with a fixed rule for what counts as a swing.
- [ ] For a sweep, I wait for the **close** back inside the level; for a breakout, for the close beyond it.
- [ ] My stop sits beyond the sweep's extreme, and I accept it if the price goes there.
- [ ] I have one or two levels on the chart, not ten.
- [ ] I know which parts of my method need intraday data, and I am not pretending a daily chart shows them.
- [ ] Before I use a rule with money, I have tested it, with costs, on data it was not designed on.

## Further reading

- Larry Harris, *Trading and Exchanges: Market Microstructure for Practitioners* (2003) — the standard guide to order types, order books and who trades with whom.
- Albert S. Kyle, "Continuous Auctions and Insider Trading", *Econometrica* 53 (1985).
- Tarun Chordia and Avanidhar Subrahmanyam, "Order Imbalance and Individual Stock Returns: Theory and Evidence", *Journal of Financial Economics* 72 (2004).
- Rama Cont, Arseniy Kukanov and Sasha Stoikov, "The Price Impact of Order Book Events", *Journal of Financial Econometrics* 12 (2014).
- Carol L. Osler, "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", *Journal of Finance* 58 (2003).
- Carol L. Osler, "Stop-Loss Orders and Price Cascades in Currency Markets", *Journal of International Money and Finance* 24 (2005).
- James F. Dalton, Eric T. Jones and Robert B. Dalton, *Mind Over Markets* (1990; updated 2013) — Market Profile, value areas and the point of control.
- Richard D. Wyckoff, *The Richard D. Wyckoff Method of Trading and Investing in Stocks* (course, 1931; later reprints) — springs, upthrusts and absorption, in their original form.
