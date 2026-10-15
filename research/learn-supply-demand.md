# Supply and demand — zones, and why price levels matter

**In short**

- Price moves when one side runs out of people to trade with. A level on a chart marks where, last time, one side took everything the other offered.
- A demand zone is the short pause a strong rally started from. A supply zone is the pause a strong fall started from. Judge a zone by how fast the price left it, and use it at most once or twice.
- Broken resistance often becomes support, and broken support often becomes resistance. This is called role reversal.
- Old highs above the price are overhead supply: holders waiting to sell at breakeven. Stocks near their 52-week high have little of it.
- Zones are a reading aid, not a proven edge. Their real use is deciding where a stop goes and where a target is asking too much.

This guide explains what supply and demand mean on a chart, how to find and score zones, and when a level changes sides. A base is a demand zone being built; see [learn-bases](learn-bases.md). For the drawn chart shapes, see [learn-chart-patterns](learn-chart-patterns.md).

---

## 1. How prices move

In February 2022 Salesforce broke below about $210, a price where buyers had stepped in twice in the previous nine months. Within seven weeks it bounced back to $221. That was just above the old floor, and there it stopped. By May it had fallen to $164.

```series
title: Salesforce — an old floor that became a ceiling, 2022
from: 2021-03-01
to: 2022-06-30
tf: D
line: us:CRM | Salesforce
line: us:CRM@sma50 | 50-day average
mark: 2021-05-12 | buyers step in near 210
mark: 2022-01-26 | and again near 211
mark: 2022-02-11 | closes below the floor
mark: 2022-03-29 | bounce stops at 221
caption: The level where buyers had absorbed all the selling twice became the level where sellers met the bounce.
```

Price does not move because of opinions. It moves because, at the current price, one side runs out of people to trade with. In a rally, buyers keep paying the sellers' asking price until no one is left offering stock cheaply. The rally stops where enough sellers appear to fill all the buy orders.

Every level on a chart says the same thing: *at this price, last time, one side took everything the other side offered.* Support is where all the selling was bought. Resistance is where all the buying was met by sellers. A **zone** is the more honest way to draw this, because it happens across a band of prices, not at one exact price.

Two kinds of trader behaviour keep old levels relevant:

- **Trapped positions.** Someone who bought near the top before a fall is sitting on a loss. They are waiting to "get out at breakeven", so their selling waits at the old level. Someone who sold near the bottom before a rise regrets it and waits to buy back.
- **Anchoring.** Even traders with no position see the same prior high, prior low and round number, and place orders around them. The level works partly because everyone expects it to.

## 2. Demand zones — where buyers are waiting

In early May 2019, ICICI Bank fell about 8% in two weeks, to ₹376. For four sessions in mid-May it traded in a narrow band, between about ₹376 and ₹387. On 20 May it jumped to ₹407.70, on almost twice its average volume. A week later it touched ₹439.20.

The price came back to that band only in late August, three months later. On 23 August 2019 the low was ₹385.80, inside the zone, and the close was back above it at ₹395.40. It dipped to ₹384 once more in September, then jumped to ₹446 within two sessions.

```series
title: ICICI Bank — a demand zone and its retests, 2019
from: 2019-03-15
to: 2019-10-31
tf: D
line: india:ICICIBANK.NS | ICICI Bank
line: india:ICICIBANK.NS@vol | Volume | pane2 bars
mark: 2019-05-14 | the base, ₹376–387
mark: 2019-05-20 | the rally leaves the zone
mark: 2019-08-23 | first retest holds
mark: 2019-09-19 | second retest holds
caption: A short, tight pause, then a fast move away on heavy volume. When the price returned months later, buyers were still there.
```

That band is a **demand zone**: the starting point of a strong move up. It is the pause where a decline stopped and big buyers bought everything that was for sale. The rally that followed shows that they still wanted more shares than they got.

```pattern
demand-zone
```

You identify a zone by the way the price *left* it, not by the pause itself:

1. **Find the move away first.** Look for a fast, large rally: wide green bars and rising volume. If the price only drifted away, the big buyers probably got all the shares they wanted. Then there is no reason to expect more buyers waiting there.
2. **Mark the base the move started from.** Draw it from the pause's low to its high: the last small consolidation before the move. Zone traders call it a *drop-base-rally* when a decline came before it, and a *rally-base-rally* inside an uptrend. Short and tight is better than long and loose. When the selling is soaked up quickly, the buyer is bigger than the seller.
3. **Judge freshness.** Each time the price comes back to the zone, some of the waiting buy orders get filled and used up. The first retest (the first return to the zone) is the trade; the third is a coin flip. A zone the price has already broken through is gone, so do not keep buying as it falls.
4. **Judge location.** The zone should sit inside a chart you would want to own anyway: a higher low in an uptrend, or a base inside a Stage 2 advance. The same shape at the bottom of a collapsing downtrend is an attempt to catch a falling knife.

**Trading the retest.** Wait for evidence *inside* the zone: a hammer, a bullish engulfing bar or a tight shelf (see [learn-candlestick-patterns](learn-candlestick-patterns.md)). Enter on that. Put the stop just under the zone: if the demand is real, the price should not trade through it.

Put the target just below the next supply above. The appeal is the reward compared with the risk. The stop is only a zone's width away, while the target is a whole swing's height away. The full trade is in [learn-strat-pullback-support](learn-strat-pullback-support.md).

## 3. Supply zones — where sellers are waiting

```pattern
supply-zone
```

This is the mirror image: the **starting point of a strong move down**. It is a pause near a high where sellers met all the buying in the rally. The fall that followed proves it. Everyone who bought during that pause is now trapped at a loss, and their selling at breakeven waits above the price.

The same four tests apply: a strong move away, little time spent in the zone, a fresh zone, and a location in a downtrend or under a failed high.

This is what William O'Neil calls **overhead supply**. It is the reason his rules prefer stocks near 52-week highs: a stock at new highs has *no one trapped above it*. No sellers are waiting there to get back what they paid. Each base left behind and each old swing high on the way up is a level where sellers may be waiting.

A rally that approaches one of these levels on fading volume is likely to meet selling. What uses up a supply zone is a push **through** it on rising volume. The trapped sellers have sold, and short sellers are forced to buy back their shares. The level has done its job, and it often changes sides.

## 4. Role reversal — levels change sides

Salesforce in section 1 showed one direction: an old floor became a ceiling. The other direction is just as common. State Bank of India broke above about ₹614 in December 2023. In January 2024 it dipped under that level during the day, closed back above it, and then ran to about ₹725 (see [learn-strat-pullback-support](learn-strat-pullback-support.md)).

```pattern
role-reversal
```

This is called the polarity principle: **broken resistance becomes support; broken support becomes resistance.** Three groups change behaviour at once:

- buyers from the breakout buy more to defend their entry price;
- short sellers who sold at the old level buy back on dips;
- the sellers who created the level have no stock left to sell.

In practice:

- A shallow, quiet pullback to a broken pivot that holds is the **retest entry**: a second chance at a breakout, usually with a tighter stop.
- A close back *below* the level the price just climbed above is the failure signal. A breakout that cannot hold its pivot ran into supply after all. See [learn-strat-failed-breakouts](learn-strat-failed-breakouts.md).

## 5. Scoring a zone — a checklist

| Test | Strong zone | Weak zone |
|---|---|---|
| Departure (how the price left) | Fast, large, volume rises | Drifted away quietly |
| Time at the level | A few bars (the selling was bought quickly) | A long, slow grind (a range, not a zone) |
| Freshness | Not revisited since it formed | Hit two or three times already |
| Trend context | With the larger trend | Against it |
| Overlap with other levels | Overlaps a prior swing, a rising 50-day, a base top | Stands alone |
| Cleanliness | One clear pause | Messy, overlapping bars — no single starting point |

ICICI Bank's May 2019 zone scores well. It left fast on heavy volume after four tight sessions, and it was fresh at the first retest.

## 6. Using zones in a trade

Most swing methods do not draw boxes. But they use the same ideas under different names, and the zone vocabulary makes their rules easier to follow.

- **A base is a demand zone being built.** In the sideways stretch after an advance ([learn-bases](learn-bases.md)), buyers take the shares that profit-takers sell. The pivot is the price at which the last of those sellers is gone. The breakout works *because* the sellers above it were used up inside the base. That is why wide-and-loose bases, where the selling was never fully taken up, fail more often.
- **Do not buy directly under supply.** A buy-stop order just under a level full of trapped sellers is likely to lose money. A common rule is to skip an entry that sits within about 3% below an old high. For a pullback entry, wait for the price to *resume* its rise through the swing high the pullback started from, rather than buying the first touch of support.
- **Put targets just below supply, not inside it.** A measured-move target that sits above a fresh supply level expects the price to cut straight through it. Such targets often never get hit. Cap the target at the nearest old high that is at least one ATR above the entry.
- **Put stops under demand.** Handle lows, tight-area lows and prior swing lows are all demand. Just below them is where the trade's premise, that buyers are here, is proven wrong.
- **Strength means little supply above.** Rules such as "within 25% of the 52-week high" are really filters for overhead supply. The fewer trapped holders above the price, the less selling a rally has to get through.

## 7. What the evidence says

**Levels are where orders wait.** Carol Osler (2000) found that support and resistance levels published by currency firms interrupted intraday trends more often than arbitrary levels did. She later traced this to clusters of stop and take-profit orders near round numbers (Osler, 2003). Kavajecz and Odders-White (2004) found that support and resistance levels in US stocks line up with deep parts of the limit-order book.

**Nearness to the 52-week high.** George and Hwang (2004) found that US stocks near their 52-week high went on to outperform stocks far below it. Little overhead supply is one explanation; anchoring on the old high is another.

**An event study on stored data.** We checked whether the same pattern shows up in Indian and US stocks since 2010.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to July 2026. Every 20th session of every liquid stock: close at least ₹20 or $5, and 50-day average turnover at least ₹5 crore or $5 million. Distance below the 52-week high: 1 − close ÷ the highest high of the last 252 sessions. Outcome: the return over the next 60 sessions, and that return minus the median of all stocks on the same day. Caveats: today's lists only (survivorship bias), no costs, overlapping windows.

| Below the 52-week high | India: share higher | India: median vs the day's median | US: share higher | US: median vs the day's median |
|---|---|---|---|---|
| Less than 5% | 57.7% | +1.3% | 56.4% | +0.5% |
| 5–15% | 55.0% | +0.6% | 56.1% | 0.0% |
| 15–25% | 49.6% | −0.2% | 55.4% | 0.0% |
| 25–40% | 48.3% | −1.0% | 54.3% | −0.2% |
| 40–60% | 51.3% | −1.0% | 52.6% | −0.7% |
| 60% or more | 51.9% | −0.8% | 42.8% | −6.7% |

| Number of observations | India | US |
|---|---|---|
| Less than 5% below | 13,453 | 76,406 |
| 15–25% below | 21,650 | 64,486 |
| 60% or more below | 1,430 | 11,991 |

What this shows:

- **In India, stocks near their highs did better.** Those within 5% of the high beat the day's typical stock by about 1.3% over 60 sessions. Those 25% or more below it lagged.
- **In the US the effect was small** except at the extreme. Stocks 60% or more below their high did much worse than the rest.
- **It is a tilt, not a rule.** Even near the high, more than four stocks in ten were lower 60 sessions later.

**Limits of zone trading.** Retail "supply and demand zone" trading is a way of looking at charts by judgement, not a measured edge. No public study shows that boxes drawn by the usual rules beat the market after costs. The evidence supports the weaker claims: prices react around old highs, lows and round numbers more often than chance, and stocks near their highs tend to do a little better.

- **Their real value is deciding where risk goes.** Zones tell you where a stop is just slightly off and where the whole idea is wrong. They also tell you when a target is asking too much.
- **Zones wear out.** The better known a level, the more traders place orders just ahead of it to get in first, which spreads the zone wider. Expect the price to react *around* zones, not at an exact price.
- **Beware hindsight.** On any chart, *some* box lines up with every turn. Score zones in advance with section 5 and write the level down before the retest. Then see whether the chart proves you right.

## 8. Practising

1. On a few charts, find strong moves and mark the base each one started from. Score each zone with the table in section 5.
2. Write down the zone and your planned stop before the price returns. Then record whether the first retest held.
3. On a stock you own or follow, list every old high above the current price. Ask how much selling a rally would have to get through.

## Further reading

- Richard Wyckoff's diagrams of accumulation and distribution — the 1930s original of every zone diagram. They cover how selling gets soaked up, "springs" (a quick dip below support that reverses) and tests.
- William O'Neil, *How to Make Money in Stocks* — overhead supply, and why stocks at new highs do better than bargains.
- Edwards and Magee, *Technical Analysis of Stock Trends* — the chapters on support, resistance and polarity; the oldest systematic statement of section 4.
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Carol Osler, "Support for Resistance: Technical Analysis and Intraday Exchange Rates", *Federal Reserve Bank of New York Economic Policy Review* (2000).
