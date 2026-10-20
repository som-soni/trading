# Supply and demand — zones, and why price levels matter

**In short**

- Price moves when one side runs out of people to trade with. Support and resistance mark where the price *reacted*; a zone marks where a decisive move *started*.
- A demand zone is the short pause a strong rally started from. A supply zone is the pause a strong fall started from. Find the move first, draw only the pause, and draw its edges by one fixed rule.
- Broken resistance often becomes support, and broken support often becomes resistance. This is called role reversal.
- Old highs above the price are overhead supply: holders waiting to sell at breakeven. Stocks near their 52-week high have little of it.
- Decide in advance what kills a zone, usually a close beyond its far edge. Zones are a reading aid, not a proven edge; their real use is placing stops and capping targets.

This guide explains what supply and demand mean on a chart, how to find and score zones, and when a level changes sides. A base is a demand zone being built; see [Bases](learn-bases.md). For the drawn chart shapes, see [Chart patterns](learn-chart-patterns.md). How to draw and grade support and resistance levels step by step is in [Support and resistance](learn-support-resistance.md).

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

**Levels and zones answer different questions.** Support and resistance ask where the price has turned before. A zone asks where a strong move began. They use different evidence, so they are not rivals.

| | Support / resistance | Demand / supply zone |
|---|---|---|
| The evidence | Earlier turns, swing highs and lows, range edges | A short, tight pause followed by a fast move away |
| Needs repeated touches? | No, but each turn adds weight | No: the move away makes it notable before any retest |
| Drawn as | A line or a narrow band | A box around the pause |

The two often overlap. A price where a stock bounced twice may also be the pause a sharp rally started from. Then both readings point to the same place.

One caution about the words. "Demand zone" does not prove that large buyers are hiding there. A chart records trades that happened, not who made them or why. The names describe price behaviour; treat them as shorthand, not as a report on big funds.

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

That band is a **demand zone**: the starting point of a strong move up. It is the pause where a decline stopped and buyers took everything that was for sale. The rally that followed shows that buying outran selling once the pause ended.

```pattern
demand-zone
```

You identify a zone by the way the price *left* it, not by the pause itself:

1. **Find the move away first.** Look for a fast, large rally: wide green bars, little overlap between them, each close above the last. Measure it against the stock's normal daily range, its ATR (average true range). Two or three bars that carry the price two ATRs or more beyond the pause are decisive. A close above a nearby swing high adds weight. If the price only drifted away, there is little reason to expect buyers still waiting there.
2. **Trace it back to the pause.** Mark only the short, tight stretch right before the price took off. Leave out the decline before it and the rally after it. Zone traders call it a *drop-base-rally* when a decline came first, and a *rally-base-rally* when a rally did. The name describes the move straight into the pause: a pullback inside an uptrend is still a drop. Short and tight is better than long and loose. If no compact stretch stands out, skip the chart rather than stretch a box to fit.
3. **Draw the edges by one rule.** The **proximal** edge is the one the price meets first on its way back; for a demand zone that is the top. The **distal** edge is the far side; for a demand zone, the bottom. One common rule takes the pause's whole high-to-low range. Another takes the highest candle body for the proximal edge and the lowest wick for the distal edge, which gives a tighter box. Pick one and keep it.
4. **Judge freshness.** Each return to the zone may use up some of the orders waiting there. Write down every retest and how the price responded. After four or more retests, treat it as an ordinary support or resistance level, not a fresh zone. A zone the price has closed through is gone, so do not keep buying as it falls.

One area makes one zone. Price sometimes builds a second small pause inside a zone while retesting it. That is the same area seen again, so widen the first box to cover it and count its retests once.
5. **Judge location.** The zone should sit inside a chart you would want to own anyway: a higher low in an uptrend, or a base inside a Stage 2 advance. The same shape at the bottom of a collapsing downtrend is an attempt to catch a falling knife.

**Why the edge rule matters.** In ICICI Bank's case, the full range of the four mid-May sessions runs from ₹375.20 to ₹386.80. The tightest part of the pause, the last three sessions before the rally, gives a body-to-wick box of ₹375.80 to ₹382.50.

| Rule | Zone | 23 Aug low ₹385.80 | 19 Sep low ₹384.35 |
|---|---|---|---|
| Full range, four sessions | ₹375.20–386.80 | A retest | A retest |
| Highest body to lowest wick, three sessions | ₹375.80–382.50 | Never entered | Never entered |

Same chart, same pause, and two different stories about whether the zone was tested. Neither rule is the correct one. What matters is choosing before the price returns, so the box is not redrawn to fit what happened.

**Trading the retest.** Wait for evidence *inside* the zone: a hammer, a bullish engulfing bar or a tight shelf (see [Candlestick patterns](learn-candlestick-patterns.md)). Enter on that. Put the stop just under the zone: if the demand is real, the price should not trade through it.

Put the target just below the next supply above. The appeal is the reward compared with the risk. The stop is only a zone's width away, while the target is a whole swing's height away. The full trade is in [Pullback to support](learn-strat-pullback-support.md).

## 3. Supply zones — where sellers are waiting

```pattern
supply-zone
```

This is the mirror image: the **starting point of a strong move down**. It is a pause near a high where sellers met all the buying in the rally. The fall that followed proves it. Everyone who bought during that pause is now trapped at a loss, and their selling at breakeven waits above the price.

The steps mirror the demand zone. Zone traders call it a *rally-base-drop* when an advance came before it, and a *drop-base-drop* inside a decline. For a supply zone the proximal edge is the bottom of the box and the distal edge the top. The same tests apply: a strong move away, little time spent in the zone, a fresh zone, and a location in a downtrend or under a failed high.

This is what William O'Neil calls **overhead supply**. It is the reason his rules prefer stocks near 52-week highs: a stock at new highs has *no one trapped above it*. No sellers are waiting there to get back what they paid. Each base left behind and each old swing high on the way up is a level where sellers may be waiting.

A rally that approaches one of these levels on fading volume is likely to meet selling. What uses up a supply zone is a push **through** it on rising volume. The trapped sellers have sold, and short sellers are forced to buy back their shares. The level has done its job, and it often changes sides.

## 4. Volume — supporting evidence, not a requirement

Find the zone from price first. Then look at volume as a separate check. A sharp move on ordinary volume can still mark a good zone; judge it against what is normal for that stock.

Compare a bar's volume with its recent past rather than with a fixed number. **Relative volume** is the bar's volume divided by the average of the previous 20 bars. A reading of 1.5 means half again as much as usual. ICICI Bank's 20 May 2019 rally day traded about 1.8 times its recent average.

| What you see | What it suggests |
|---|---|
| Volume expands on the move away | The move had real participation |
| Heavy volume inside the pause | A lot of trading or disagreement; volume alone does not show which side won |
| The price returns to the zone on shrinking volume | The pullback may lack force; it does not confirm a bounce |
| The price breaks through the zone on expanding volume | More evidence the zone is failing, especially on a close beyond it |
| Heavy volume, a long wick, little net progress | Absorption, exhaustion or a two-sided fight; read the context |

Every trade has a buyer and a seller, so volume cannot reveal who was the aggressor. Earnings, index changes and news produce outsized volume for reasons unrelated to any zone. A departure that gaps away from the pause usually has news behind it, so check what moved it.

## 5. When has a zone failed?

Decide what kills a zone before the price comes back. Otherwise it is too easy to widen the box after each move against you.

| What the price does at a demand zone | How to read it |
|---|---|
| Enters the zone but stays above the distal edge | Not failed; watch the response |
| Wicks below the distal edge, then closes back above | A possible rejection, not proof of strength |
| Closes decisively below the distal edge | Failed, under a close-based rule |

A supply zone is the mirror image: a close above its distal edge is the failure. There are three common conventions. A trade beyond the edge during the day kills the zone; or only a close beyond it does; or a close beyond it by a buffer, such as a fraction of the ATR. Swing traders usually use a daily close. None is universally right; using the same one every time is what counts.

A failed zone is not the same as a trade stop. A stop also has to allow for volatility, slippage and position size. It may sit at the zone's edge or some way beyond it, depending on the method (see [Stops and exits](learn-risk-stops-exits.md)).

The timeframe matters too. A zone on a weekly chart and a zone on a daily chart are different things. Label each zone with its timeframe and the date it formed.

## 6. Role reversal — levels change sides

Salesforce in section 1 showed one direction: an old floor became a ceiling. The other direction is just as common. State Bank of India broke above about ₹614 in December 2023. In January 2024 it dipped under that level during the day, closed back above it, and then ran to about ₹725 (see [Pullback to support](learn-strat-pullback-support.md)).

```pattern
role-reversal
```

This is called the polarity principle: **broken resistance becomes support; broken support becomes resistance.** Three groups change behaviour at once:

- buyers from the breakout buy more to defend their entry price;
- short sellers who sold at the old level buy back on dips;
- the sellers who created the level have no stock left to sell.

In practice:

- A shallow, quiet pullback to a broken pivot that holds is the **retest entry**: a second chance at a breakout, usually with a tighter stop.
- A close back *below* the level the price just climbed above is the failure signal. A breakout that cannot hold its pivot ran into supply after all. See [Failed breakouts and bull traps](learn-strat-failed-breakouts.md).

## 7. Scoring a zone — a checklist

| Test | Strong zone | Weak zone |
|---|---|---|
| Departure (how the price left) | Several ATRs in a few bars, little overlap | Drifted away quietly |
| Structure | The move broke a nearby swing high or low | Stayed inside the old range |
| Time at the level | A few bars (the selling was bought quickly) | A long, slow grind (a range, not a zone) |
| Width | Narrow compared with the ATR | Wide enough to make the stop distance awkward |
| Volume | Relative volume checked and recorded | Not looked at |
| Freshness | Not revisited since it formed | Hit two or three times already |
| Trend context | With the larger trend | Against it |
| Overlap with other levels | Overlaps a prior swing, a rising 50-day, a base top | Stands alone |
| Events | No earnings or news behind the move, or noted if there was | Unknown |

ICICI Bank's May 2019 zone scores well. It left fast on heavy volume after a few tight sessions, and it was fresh at the first retest. Its first burst stopped short of the April high of ₹411, though, so it misses on structure.

The checklist keeps your reviews consistent. It is not a proven predictor: ticking more boxes does not guarantee a winning trade (see section 9).

## 8. Using zones in a trade

Most swing methods do not draw boxes. But they use the same ideas under different names, and the zone vocabulary makes their rules easier to follow.

- **A base is a demand zone being built.** In the sideways stretch after an advance ([Bases](learn-bases.md)), buyers take the shares that profit-takers sell. The pivot is the price at which the last of those sellers is gone. The breakout works *because* the sellers above it were used up inside the base. That is why wide-and-loose bases, where the selling was never fully taken up, fail more often.
- **Do not buy directly under supply.** A buy-stop order just under a level full of trapped sellers is likely to lose money. A common rule is to skip an entry that sits within about 3% below an old high. For a pullback entry, wait for the price to *resume* its rise through the swing high the pullback started from, rather than buying the first touch of support.
- **Put targets just below supply, not inside it.** A measured-move target that sits above a fresh supply level expects the price to cut straight through it. Such targets often never get hit. Cap the target at the nearest old high that is at least one ATR above the entry.
- **Put stops under demand.** Handle lows, tight-area lows and prior swing lows are all demand. Just below them is where the trade's premise, that buyers are here, is proven wrong.
- **Strength means little supply above.** Rules such as "within 25% of the 52-week high" are really filters for overhead supply. The fewer trapped holders above the price, the less selling a rally has to get through.

## 9. What the evidence says

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

**A second event study: do zone retests hold?** Zones drawn by eye cannot be tested, so we fixed every rule in advance and drew them by machine. Then we asked what happened at each retest, and compared it with the same distances placed on a random day.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to October 2026. Zones exactly as in section 2: a move of one to three bars that carries the close at least 2 ATR past a pause of up to six small or indecisive bars, no wider than 1.5 ATR in all. Edges run from the highest body to the lowest wick, and a daily close beyond the distal edge ends the zone. A pause built inside a zone that is still active is merged into it. Only zones that formed while the stock was liquid: close at least ₹20 or $5, and 50-day average turnover at least ₹5 crore or $5 million. For each retest, a **bounce** is a close 2 ATR beyond the proximal edge before any close beyond the distal edge, within 60 sessions. The **placebo** puts the same edge and target distances, in ATRs, under the close of a random day in the same stock. Caveats: today's lists only (survivorship bias), no costs, many retests overlap.

| Zone retests | Retests | Bounced | Placebo bounced |
|---|---|---|---|
| India, demand | 46,274 | 41.4% | 42.0% |
| India, supply | 33,089 | 39.4% | 37.8% |
| US, demand | 153,914 | 43.5% | 43.2% |
| US, supply | 154,283 | 36.4% | 34.2% |

| Bounced minus placebo, by retest | First | Second | Third or later |
|---|---|---|---|
| India, demand | +1.2 pts | −1.0 pts | −2.7 pts |
| India, supply | +2.6 pts | +0.6 pts | +0.8 pts |
| US, demand | +0.1 pts | +0.3 pts | +0.5 pts |
| US, supply | +1.9 pts | +1.8 pts | +2.8 pts |

What this shows:

- **Demand zones held no more often than chance.** A retest of a mechanically drawn demand zone bounced as often as a random price with the same stop and target distances.
- **Supply zones did slightly better than chance**, by about two points. A rally into a supply zone was a little more likely to turn back than a random rally.
- **Freshness mattered a little, in India.** First retests of demand zones did better than later ones there. In raw numbers the gap looked large: 44.0% for first retests against 39.8% for the third or later. But most of it came from the distances, because the placebo fell almost as much.
- **The checklist did not help.** Zones ticking four or five of its boxes did no better against the placebo than those ticking fewer, and in the US slightly worse.

**Limits of zone trading.** Retail "supply and demand zone" trading is a way of looking at charts by judgement, not a measured edge. No public study shows that boxes drawn by the usual rules beat the market after costs, and our own test found almost nothing for demand zones. The evidence supports the weaker claims: prices react around old highs, lows and round numbers more often than chance, and stocks near their highs tend to do a little better.

- **Their real value is deciding where risk goes.** Zones tell you where a stop is just slightly off and where the whole idea is wrong. They also tell you when a target is asking too much.
- **Zones wear out.** The better known a level, the more traders place orders just ahead of it to get in first, which spreads the zone wider. Expect the price to react *around* zones, not at an exact price.
- **Beware hindsight.** On any chart, *some* box lines up with every turn. Score zones in advance with section 7 and write the level down before the retest. If you ever move an edge, write down why. Then see whether the chart proves you right.

## 10. Practising

A review routine, in order:

1. Start on the weekly chart. Mark the trend, the range edges and the major swing highs and lows.
2. Mark support and resistance separately, as places where the price reacted.
3. Find the decisive moves and trace each back to its pause. Skip any pause you cannot pin down.
4. Draw each box with your fixed edge rule, and label its timeframe and date.
5. Score it with the table in section 7: departure against the ATR, structure, relative volume, events.
6. Record whether it is fresh, and every retest since.
7. Write down what kills the zone before thinking about a trade.
8. Wait for the return and an entry signal. Set the stop, target and position size as separate decisions.

Then, on a stock you own or follow, list every old high above the current price. Ask how much selling a rally would have to get through.

## Further reading

- Richard Wyckoff's diagrams of accumulation and distribution — the 1930s original of every zone diagram. They cover how selling gets soaked up, "springs" (a quick dip below support that reverses) and tests.
- William O'Neil, *How to Make Money in Stocks* — overhead supply, and why stocks at new highs do better than bargains.
- Edwards and Magee, *Technical Analysis of Stock Trends* — the chapters on support, resistance and polarity; the oldest systematic statement of section 4.
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Carol Osler, "Support for Resistance: Technical Analysis and Intraday Exchange Rates", *Federal Reserve Bank of New York Economic Policy Review* (2000).
