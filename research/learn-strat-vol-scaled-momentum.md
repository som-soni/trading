# Volatility-scaled momentum — rank by return per unit of risk, hold 20, rotate monthly

**In short**

- Each month-end, rank liquid stocks by their past-year return divided by how much they swung to get there. Hold the 20 best scores.
- Give each holding money in inverse proportion to its recent volatility, so a calm stock gets a bigger slice than a wild one.
- Sell only when a stock drops out of the top 20 or stops qualifying. There is no stop and no target.
- In our own sort of Indian and US stocks since 2012, the scaled list was calmer and had fewer blow-ups than the plain momentum list. It did not reliably earn more.
- Costs and the choice of benchmark decide whether it is worth running. Judge it against the small-cap segment it actually holds.

---

This guide builds on [Cross-sectional momentum](learn-strat-xs-momentum.md). Read that first for why momentum works, who is on the other side, and why it crashes. Here we change two things: how stocks are ranked, and how money is split between them.

## 1. The idea

At the end of June 2024, two Indian stocks had almost the same 12-month record. Trent, the retailer, had risen 213%. RVNL, the railway builder, had risen 211%. Both returns are measured from 18 May 2023 to 29 May 2024, skipping the latest month.

```series
title: Trent and RVNL — the same gain, two different paths
from: 2023-05-18
to: 2024-05-29
rebase: 100
line: india:TRENT.NS | Trent
line: india:RVNL.NS | RVNL
caption: Trent rose 213.4% and RVNL 210.9% over the window used for the June 2024 ranking. Trent's worst fall on the way was 7.7%; RVNL's was 27.8%.
```

A plain momentum rank treats them as equals: 53rd and 56th of 710 qualifying stocks. But Trent got there in a steady climb. RVNL got there in lurches, with a 28% fall in the middle. Its average daily move was 3.5%, against 2.0% for Trent.

Divide each return by that daily volatility and the picture changes. Trent's score puts it 18th, inside a top-20 portfolio. RVNL drops to 96th, far outside it. That is **volatility-scaled momentum**: return per unit of risk, close to a past-year Sharpe ratio.

```series
title: The same two stocks, measured by their falls from a peak
from: 2023-05-18
to: 2024-05-29
line: india:TRENT.NS@dd | Trent, fall from its high
line: india:RVNL.NS@dd | RVNL, fall from its high
caption: The drawdown line shows how far each stock was below its running high. Trent rarely sat far below its peak; RVNL spent months well below it.
```

**Why rank this way.** A stock that rose steadily has had a stream of small pieces of good news, absorbed slowly. Research on "continuous information" (§5) finds that kind of momentum persists better. A stock that rose in a few jumps may have had one event that is already fully priced. The scaled rank also avoids the most erratic names, which are the ones most likely to collapse.

**Why weight by inverse volatility.** If every holding gets the same money, the wildest few stocks drive most of the portfolio's swings. Giving each stock money in proportion to 1 ÷ its volatility makes each one contribute roughly the same risk. Calm stocks get more; wild stocks get less.

**Who is on the other side.** The same people as in plain momentum: investors who sell winners early, and value buyers who sell because a stock looks expensive. The scaled version adds one more. Traders chasing the biggest, fastest movers ignore the steady risers this rank prefers.

## 2. When it works and when it doesn't

**It works best in long, orderly bull markets.** Leadership is steady and many stocks trend calmly. Indian examples are 2017, 2021 and 2023. The top 20 then holds steady risers for months, and turnover stays moderate.

**It fails at sharp turns, like all momentum.** The scaled rank picks calmer stocks, but they are still last year's winners. When a crowded theme breaks, they fall together (§6). Volatility measured over the past year does not warn you about a crash that has not happened yet.

**It struggles in broad sell-offs because the trend filter empties the list.** Only stocks above their 200-day average qualify. In our India sort there were four month-ends with fewer than 40 qualifying stocks. They were July and August 2013, February 2016 and March 2020. The rules in §3 say what to do then.

**Stock types.** With a liquidity floor rather than a size floor, an Indian version ends up holding mostly small and mid caps. That is where most of the big 12-month winners are. It means the portfolio rises and falls with the small-cap segment, which is the point of §3's benchmark rule.

**India versus US.** In India the scaled list and the plain list overlapped heavily: 16 of 20 names on average. In the US they differed more, about 12 of 20. The US universe has many more extreme, erratic movers for the scaling to remove (§8).

## 3. The rules

### Universe and filters

Listed operating companies only. Exclude ETFs, index funds, liquid and money-market funds, InvITs, REITs and other funds.

**Why this matters more here than in other strategies.** A liquid fund rises a little almost every day. Say it earned 7% over the year with daily moves of 0.03%. Its score is 7 ÷ 0.03, about 233. The top Indian stock in June 2024 scored 206. The fund would rank first.

Inverse-volatility weighting then makes it worse. Suppose 19 stocks have volatility near 50% a year and the fund about 0.3%.

| Holding | Volatility | 1 ÷ volatility |
|---|---|---|
| The fund | 0.3% | about 333 |
| 19 stocks | 50% each | 2 each, 38 in all |
| Fund's weight | | 333 ÷ (333 + 38), about 90% |

Nine-tenths of the "momentum portfolio" would sit in a cash-like instrument. Any measure that divides by volatility has this trap. Filter by instrument type, not by name alone.

On each rebalance date, a stock qualifies only if all of these hold:

| Filter | India | US |
|---|---|---|
| Minimum price | none needed beyond the turnover floor (optional ₹20–50) | $10 |
| 20-day average traded value (close × volume) | at least ₹10 crore a day | at least $20 million a day |
| Trend | close above its own 200-day simple moving average | same |
| History | at least 273 sessions of prices, plus a small margin | same |

The history rule covers 252 sessions of returns plus the 21-session skip. Missing a few days is fine. Missing weeks is not; require at least about 240 valid daily returns in the window.

### Setup

The setup is the score, computed after the close on the last trading session of the month.

- **R(12-1)** = close 21 sessions ago ÷ close 273 sessions ago − 1. This is the 12-month return, skipping the latest month.
- **σ** = standard deviation of the daily returns over the same 252 sessions, also ending 21 sessions ago.
- **Score** = R(12-1) ÷ σ.

σ is not annualised. Multiplying every stock's σ by the same number does not change the order, so it does not matter for ranking. A negative return gives a negative score; such stocks are rare after the trend filter, and they rank at the bottom anyway.

The **buy list** is the 20 highest scores among qualifying stocks.

### Entry

- Trade at the close of the rebalance session (a closing auction order, or limit orders near the close). If you rank after the close, trade the next session instead and test it the same way.
- Buy every name on the buy list that you do not hold.
- Do not wait for a pullback or a breakout. The rank is the entry.

### Initial stop

None. Risk is controlled by holding 20 stocks, by the inverse-volatility weights and by the monthly re-rank. A stock that falls hard loses its rank and is sold at the next rebalance.

### Exits

- **Rank exit:** at each rebalance, sell any holding that is not in the new top 20.
- **Eligibility exit:** sell any holding that fails a filter: it closed below its 200-day average, or its turnover fell under the floor.
- No profit target, no trailing stop, no time limit. A winner stays as long as it stays in the top 20.

There is no buffer in this version (some momentum books keep a stock until it drops below, say, the top 40). A buffer cuts turnover, and it is the first variation worth testing (§4).

### Position size

For each of the 20 names:

- **σ63** = annualised standard deviation of daily returns over the last 63 sessions (about three months).
- Raw weight = 1 ÷ σ63.
- Final weight = raw weight ÷ the sum of the 20 raw weights, so the weights add up to 100%.

The portfolio is fully invested: no cash, no leverage. Note the two volatility windows. The score uses a year of returns ending a month ago. The weight uses the latest three months, because sizing should reflect current risk.

### Managing the trade

- Rebalance on the last trading session of every month. Sell the leavers, buy the entrants, and reset every holding to its new target weight.
- Do nothing between rebalances, except corporate actions and filter failures you choose to act on early.
- **If fewer than 20 stocks qualify,** hold the ones that do. As specified, they share the full capital: the inverse-volatility weights are rescaled to 100%, and the book holds cash only when nothing qualifies. A common variation keeps each empty slot in cash instead. That is safer, because the fully invested rule concentrates the book exactly when markets are weakest.
- **Benchmark.** Judge the book against the segment it trades. An Indian version holds mostly small and mid caps, so compare it with the Nifty Smallcap 250, not the Nifty 50 or Nifty 500. Against a large-cap index, the small-cap segment's own rallies look like skill, and its own crashes look like failure.

```series
title: Why the benchmark matters — a small-cap index fund against the Nifty 50
from: 2023-02-21
to: 2026-10-14
rebase: 100
line: india:HDFCSML250.NS | Nifty Smallcap 250 ETF
line: india:NIFTY50 | Nifty 50
band: 2024-09-27 2025-04-09 | small caps −22.5%
caption: The small-cap ETF rose 99.2% to 27 September 2024, while the Nifty 50 rose 46.9%. It then fell 22.5% to 9 April 2025, against 14.4% for the Nifty 50. The ETF price includes reinvested dividends; the Nifty 50 line does not.
```

Any small-cap portfolio would have "beaten the market" by a wide margin in 2023–2024 without any selection skill. The question is whether the strategy beat other small caps.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Number held (top N) | 20 (10–50) | Concentration | Fewer names: bigger gaps from the benchmark, both ways. More names drift toward the segment index |
| Lookback | 252 sessions (126–252) | Speed of the signal | Published work finds 6–12 months all carry momentum; shorter means more turnover |
| Skip | 21 sessions (0–21) | Avoids the one-month reversal | US research favours the skip; some index providers skip, others do not |
| Score volatility window | equal to the lookback | What "steady" means | Matching windows keep the score a clean return-per-risk ratio |
| Weight volatility window | 63 sessions (21–126) | How fast sizes react | Short windows react faster but jump around more |
| Rebalance | monthly (monthly to quarterly) | Turnover, freshness | Quarterly cuts costs; published work suggests a modest loss of signal |
| Turnover floor | ₹10 crore / $20 million a day (20-day average) | Liquidity, segment | A higher floor shifts the book toward larger caps |
| Trend filter | 200-day average, on (on/off) | Avoids falling stocks | Off: more names in sell-offs, more crash exposure |
| Minimum price | none in India / $10 in the US | Penny stocks | Low sensitivity once the turnover floor applies |
| Cost assumption | 0.5% per side (0.2–1%) | Realism | Load-bearing; see below |
| Hold buffer (variation) | none (top 30–40) | Turnover | Usually the largest single cost saving |

**Why costs are load-bearing.** In our sort about 38% of the Indian top-20 names changed each month. That is roughly 4–5 full portfolio turnovers a year. Take four turnovers as a round number. Each turnover means selling and buying, so costs are 4 × 2 × 0.5%.

| Turnovers a year | Sides per turnover | Cost per side | Cost a year |
|---|---|---|---|
| 4 | 2 | 0.5% | 4% |

That is a large share of any plausible edge, which is why the buffer and the rebalance frequency matter so much.

## 5. Variations

- **Plain 12-1 momentum (Jegadeesh and Titman, 1993).** Rank on the return alone, equal weight. It is the baseline this rule modifies. See [Cross-sectional momentum](learn-strat-xs-momentum.md).
- **Portfolio-level volatility scaling (Barroso and Santa-Clara, 2015, "Momentum Has Its Moments").** They kept the plain winners-minus-losers portfolio and changed only its size. When the portfolio's own recent volatility was high, they held less of it; when it was low, more. That reduced the crashes in their data.
- **The difference, precisely.** Barroso and Santa-Clara scale the *whole portfolio's exposure* by the *portfolio's* volatility, over time. This guide scales each *stock's score* by that *stock's* volatility, across stocks on one date. The first changes how much momentum you own; the second changes which stocks you own. They can be combined.
- **Dynamic momentum (Daniel and Moskowitz, 2016, "Momentum Crashes").** They showed crashes cluster after market falls, when volatility is high and the market rebounds. Their dynamic version cuts exposure when those conditions are forecast.
- **Volatility-managed portfolios (Moreira and Muir, 2017).** They scaled several factor portfolios, including momentum, by the inverse of their recent variance. It improved risk-adjusted returns in their sample. Later studies argued over how robust that is out of sample.
- **Residual momentum (Blitz, Huij and Martens, 2011).** Rank on the part of each stock's return not explained by broad market factors, divided by the volatility of that part. It is a close cousin of this rule, and they reported lower volatility than ordinary momentum.
- **Frog in the pan (Da, Gurun and Warachka, 2014).** Momentum built from many small daily gains persisted more than momentum built from a few large jumps. Dividing by volatility is a rough way to favour the first kind.
- **Index-provider versions.** MSCI's momentum indexes take 6- and 12-month price momentum, skipping the latest month and net of the local risk-free rate. Each is divided by the annualised volatility of weekly returns over three years, then the two are blended as z-scores. NSE's Nifty200 Momentum 30 divides 6- and 12-month returns by the volatility of daily returns over the past year. Both rebalance far less often than monthly. Check each methodology document for current details.

## 6. Worked examples

All examples use Indian stocks, split-adjusted closes, and the rules in §3. Returns are before costs.

### The ranking on 28 June 2024

710 stocks qualified. The return window ran from 18 May 2023 to 29 May 2024.

| Stock | R(12-1) | Daily σ | Score | Plain rank | Scaled rank |
|---|---|---|---|---|---|
| Transformers and Rectifiers | +873% | 4.24% | 206 | 1 | 1 |
| Anand Rathi Wealth | +388% | 2.25% | 173 | 14 | 2 |
| Cochin Shipyard | +639% | 4.19% | 152 | 2 | 4 |
| Hindustan Aeronautics | +227% | 2.03% | 112 | 47 | 14 |
| IRFC | +432% | 3.94% | 110 | 8 | 15 |
| Trent | +213% | 2.01% | 106 | 53 | 18 |
| RVNL | +211% | 3.51% | 60 | 56 | 96 |

The score is the return divided by daily σ, both in percent: 873 ÷ 4.24 ≈ 206.

1. **Steady stocks move up.** Anand Rathi had about 60% of Cochin Shipyard's return, but only about half its volatility. It ranked second.
2. **Big but erratic gains still count.** IRFC rose 432% with a high σ and ranked 15th. The score rewards return as well as calm.
3. **The lists still overlap.** On this date 15 of the plain top 20 were also in the scaled top 20.

### Inverse-volatility weights for five of the holdings

| Stock | σ63 (annualised) | 1 ÷ σ63 | Weight within these five |
|---|---|---|---|
| Trent | 30.2% | 3.31 | 30.4% |
| Anand Rathi Wealth | 35.4% | 2.83 | 26.0% |
| Hindustan Aeronautics | 55.9% | 1.79 | 16.4% |
| Transformers and Rectifiers | 57.8% | 1.73 | 15.9% |
| Cochin Shipyard | 81.3% | 1.23 | 11.3% |
| Sum | | 10.89 | 100% |

Each weight is 1 ÷ σ63 divided by 10.89. Trent gets almost three times Cochin Shipyard's money, because it moved less than half as much. Across all 20 holdings that month, weights ran from 8.6% (Trent) down to 3.0% (Premier Explosives).

### What a month-end rebalance looks like

This table compares the scaled top 20 on 31 May 2024 with the one on 28 June 2024. It illustrates the mechanics only; it is not a result.

| Action | Stock | Rank in May → June | Why |
|---|---|---|---|
| Sell | Websol Energy System | 1 → not eligible | 20-day turnover fell to ₹7.7 crore, below the floor |
| Sell | Electrosteel Castings | 7 → 30 | out of the top 20 |
| Sell | Schneider Electric Infrastructure | 9 → 22 | out of the top 20 |
| Sell | Zomato (now Eternal) | 17 → 35 | out of the top 20 |
| Sell | HUDCO | 18 → 27 | out of the top 20 |
| Sell | Kalyan Jewellers | 19 → 26 | out of the top 20 |
| Sell | MRPL | 20 → 82 | out of the top 20 |
| Buy | Cupid | not eligible → 3 | turnover rose above the floor |
| Buy | RattanIndia Power | 164 → 10 | new entrant |
| Buy | Jupiter Wagons | 29 → 11 | new entrant |
| Buy | TVS Holdings | 38 → 13 | new entrant |
| Buy | Hindustan Aeronautics | 22 → 14 | new entrant |
| Buy | Power Finance Corporation | 25 → 17 | new entrant |
| Buy | Titagarh Rail Systems | 73 → 20 | new entrant |
| Reweight | the other 13 | still in the top 20 | each reset to its new 1 ÷ σ63 weight |

Seven of 20 names changed in one month. The reweighting matters too. Trent's target fell from 9.8% to 8.6% as more calm stocks joined. REC's fell from 4.9% to 3.6% because its recent volatility rose.

### A failure: the list of 30 September 2024

The scaled top 20 at the end of September 2024 was full of power, railway and capital-goods names. It included Websol Energy, Transformers and Rectifiers, RVNL, Inox Wind and Suzlon. Then small caps broke.

| Holding the 30 September list unchanged to 28 February 2025 | Return |
|---|---|
| The 20 names, equal weight | −28.9% |
| The 20 names, inverse-volatility weights | −29.2% |
| The median name | −37.5% |
| All 698 qualifying stocks, equal weight | −24.7% |
| Nifty Smallcap 250 ETF | −24.5% |
| Nifty 50 | −14.3% |

17 of the 20 names fell. The calmer, scaled picks gave no protection when the whole theme reversed.

In practice the monthly re-rank sold them in stages, not all at once:

| Month-end | Original 20 still in the top 20 | Stocks qualifying at all |
|---|---|---|
| 31 October 2024 | 8 | 491 |
| 31 December 2024 | 6 | 414 |
| 31 January 2025 | 5 | 233 |
| 28 February 2025 | 2 | 90 |

Against the Nifty 50, the list looks like a disaster. Against small caps, it was a few points worse than its own segment. That is the benchmark rule in action. Note also the last column: by February only 90 stocks were above their 200-day average with enough turnover, so the book was choosing from a much thinner list.

## 7. Common mistakes

- **Letting funds into the universe.** A liquid fund or a low-volatility ETF breaks both the score and the weights (§3). Filter by instrument type.
- **Measuring σ over a different window from the return.** The score should compare a return with the volatility of the same period.
- **Using the latest prices in the score.** The return and σ both end 21 sessions ago. Only the weight uses the latest three months.
- **Judging it against the Nifty 50.** A small-cap-heavy book needs a small-cap benchmark.
- **Ignoring circuit limits.** A small cap frozen at its price band cannot be traded on rebalance day (§9).
- **Assuming lower volatility means lower crash risk.** The past year's volatility says little about a sudden theme reversal (§6).
- **Under-costing.** Monthly rotation through small caps at 0.5% a side is several percent a year.
- **Tweaking until the backtest shines.** With top N, two windows, a floor and a filter, there are many knobs. Fix most of them in advance.

## 8. What the evidence says

**Published research.**

- Momentum is one of the most widely documented return patterns across markets (Jegadeesh and Titman, 1993; Asness, Moskowitz and Pedersen, 2013).
- Momentum has rare, severe crashes, concentrated in rebounds after market falls (Daniel and Moskowitz, 2016).
- Scaling the momentum portfolio by its own volatility reduced those crashes in US data (Barroso and Santa-Clara, 2015).
- Momentum from steady, continuous gains persisted more than momentum from a few jumps (Da, Gurun and Warachka, 2014).
- Ranking on volatility-adjusted or residual returns produced momentum portfolios with lower volatility (Blitz, Huij and Martens, 2011).

**Event study: plain versus scaled top 20.**

*Method.* At each month-end, take stocks only, with funds excluded, that pass the filters in §3. Pick two lists of 20: the best plain 12-month returns and the best scaled scores. Record each list's average σ63 and its next-month returns.

| Sample | India | US |
|---|---|---|
| Turnover floor | ₹10 crore a day | $20 million a day |
| Minimum price | none | $10 |
| Month-ends | 172, January 2012 to August 2026 | 176, same years |
| Skipped | 4 months with under 40 qualifying stocks | none |
| Qualifying stocks, median month | 186 | 618 |


| Average per month | India plain | India scaled | US plain | US scaled |
|---|---|---|---|---|
| Names in both lists | 16.2 of 20 | 16.2 of 20 | 12.2 of 20 | 12.2 of 20 |
| σ63 of the picks (annualised) | 51.4% | 45.8% | 78.4% | 56.4% |
| Share of picks falling more than 20% next month | 4.4% | 3.9% | 11.1% | 6.7% |
| Same, all qualifying stocks | 2.5% | 2.5% | 2.2% | 2.2% |
| Next-month return of the list | +2.25% | +2.24% | +1.08% | +1.47% |
| Same, all qualifying stocks | +1.35% | +1.35% | +0.95% | +0.95% |
| Names replaced from the previous month | 40% | 38% | 38% | 43% |

*What it shows.* Scaling made the picks calmer in both markets, much more so in the US. It cut the share of next-month blow-ups, again mostly in the US. It did not change the Indian average return at all. In the US the scaled list did better, but the difference was not reliable (a t-statistic of about 1.4, where about 2 is the usual bar).

*Caveats.* The stock list is today's listed companies, so firms that collapsed and delisted are missing (survivorship bias). No costs. Monthly signals from 12-month windows overlap, so the months are not independent. These are list averages, not a portfolio with weights and costs.

**What is unknown.** Whether the scaled rank's calmer picks translate into a better portfolio after costs and taxes. Whether the US advantage survives. And whether momentum indexes, now widely held in India, have crowded these same names.

## 9. Building and testing it yourself

**Data.** Daily split- and bonus-adjusted closes and volumes. A list of instrument types, so funds and ETFs can be removed. Ideally, delisted stocks with their final prices; most free data lacks them.

**Look-ahead traps.**

- Rank on closes up to the rebalance date only, and trade at that close or later.
- Compute the 200-day average and turnover from data up to that date.
- Do not use today's index membership or today's instrument list to decide past eligibility, if you can avoid it.

**Costs in India (delivery trades, approximate — check current rates).**

| Item | Approximate size |
|---|---|
| STT | 0.1% on the buy and 0.1% on the sell |
| Stamp duty | 0.015% on the buy |
| Exchange and SEBI charges | a few thousandths of a percent each side |
| Brokerage | zero to a flat ₹20 per order at a discount broker |
| GST | 18% on brokerage and exchange charges |
| Slippage and impact, small and mid caps | 0.2–0.5% each side, more in thin names |

Settlement is T+1. Model 0.5% a side as a realistic all-in figure for monthly small- and mid-cap rotation, and test 1% as a stress case.

**Liquidity and size.** A ₹10 crore daily turnover floor is a floor, not a comfort zone. Keep each order to about 1–2% of a stock's average daily traded value. For the thinnest qualifying name that is ₹10–20 lakh. A ₹1 crore book with 5% weights fits easily; a ₹20 crore book does not, and needs a higher floor.

**Circuit limits.** Many Indian small caps have daily price bands of 5–20%. A stock locked at its upper band has no sellers, so you cannot buy it. One locked at its lower band has no buyers, so you cannot sell it.

Write the rule in advance: carry the unfilled order to the next session, and keep the cash (or the holding) until it trades. Do not swap in the 21st name. Also exclude stocks in surveillance or trade-for-trade segments.

**Tax.** In India, gains on shares held under 12 months are short-term capital gains (STCG), taxed at a higher rate than long-term gains. Monthly rotation makes almost every gain short-term. Model tax if you trade a personal account.

**US notes.** Commissions are near zero, but spreads and impact remain. Use the $20 million floor and the $10 price. The wash-sale rule disallows a loss if you buy the same stock back within 30 days; a name that is sold at a loss and re-enters the next month triggers it.

**Testing without fooling yourself.**

- Fix the core rule before testing. Then try a small grid: top N of 10, 20 and 30; buffer off and on; monthly and quarterly.
- Prefer a region where all neighbours work, not the best single cell.
- Choose parameters on one period, then look once at a later one.
- Compare plain and scaled ranks side by side. If scaling does not help in your data, the simpler rule wins.
- Report against the segment benchmark: return, volatility, worst drawdown and when, turnover, costs, tax, and the share of return from the top five names.

```
on the last trading session of each month t:
    eligible = operating companies (no funds, ETFs, InvITs, REITs) where
               close[t] >= min_price
               and mean(close * volume, last 20 sessions) >= floor     # ₹10 cr / $20M
               and close[t] > sma200[t]
               and at least 240 valid daily returns in t-272 .. t-21
    for each stock s in eligible:
        R[s]     = close[s, t-21] / close[s, t-273] - 1
        sigma[s] = stdev(daily returns of s over t-272 .. t-21)      # not annualised
        score[s] = R[s] / sigma[s]
    book = top 20 by score
    for each s in book:
        raw[s] = 1 / (stdev(daily returns, last 63 sessions) * sqrt(252))
    weight[s] = raw[s] / sum(raw)                                     # sums to 100%
    sell holdings not in book; buy new names; reset all to weight     # at the close of t
    charge 0.5% on every rupee traded
```

## 10. Checklist

- [ ] Funds, ETFs, liquid funds, InvITs and REITs are removed by instrument type
- [ ] Every stock passes the turnover floor, the 200-day filter and the history rule on the ranking date
- [ ] The return and σ both cover the same 252 sessions, ending 21 sessions ago
- [ ] The book is the top 20 scores; weights are 1 ÷ σ63, scaled to 100%
- [ ] I know what I do if fewer than 20 stocks qualify
- [ ] Orders are under about 2% of each stock's daily traded value
- [ ] Circuit-locked stocks are carried over, not replaced
- [ ] This month's turnover, costs and short-term tax are estimated
- [ ] I compare the book with the Nifty Smallcap 250 (or the US equivalent), not a large-cap index
- [ ] The next rebalance date is in the calendar

## Further reading

- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency", *Journal of Finance*, 1993.
- Pedro Barroso and Pedro Santa-Clara, "Momentum Has Its Moments", *Journal of Financial Economics*, 2015.
- Kent Daniel and Tobias Moskowitz, "Momentum Crashes", *Journal of Financial Economics*, 2016.
- Alan Moreira and Tyler Muir, "Volatility-Managed Portfolios", *Journal of Finance*, 2017.
- David Blitz, Joop Huij and Martin Martens, "Residual Momentum", *Journal of Empirical Finance*, 2011.
- Zhi Da, Umit Gurun and Mitch Warachka, "Frog in the Pan: Continuous Information and Momentum", *Review of Financial Studies*, 2014.
- Clifford Asness, Tobias Moskowitz and Lasse Pedersen, "Value and Momentum Everywhere", *Journal of Finance*, 2013.
- MSCI, Momentum Indexes Methodology (msci.com).
- NSE Indices, Nifty200 Momentum 30 index methodology (niftyindices.com).
- Related guides: [Cross-sectional momentum](learn-strat-xs-momentum.md), [Dual momentum](learn-strat-dual-momentum.md), [Position sizing](learn-risk-sizing.md), [Portfolio risk](learn-risk-portfolio.md), [Backtesting](learn-test-backtesting.md).
