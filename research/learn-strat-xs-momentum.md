# Cross-sectional momentum — rank the market, hold the strongest, rotate monthly

**In short**

- Rank a fixed list of liquid stocks by their return over the past year, skipping the latest month. Buy the top tenth, hold for a month, then rank again.
- It is one of the best-documented effects in finance: past winners have tended to keep beating past losers for several months.
- The edge is small per month and comes with sharp losses, called momentum crashes, when a beaten-down market rebounds fast.
- In India the effect was clearly visible in a sort of the 300 most-traded stocks since 2009. In the US it was weak over the same years.
- Costs, taxes and turnover decide whether a retail version keeps the edge. Test them before trusting the idea.

---

## 1. The idea

At the end of March 2023, take the 300 most-traded Indian stocks. Rank them by how much each rose from March 2022 to February 2023, ignoring March itself. The top of the list held names like APAR Industries (up 257%) and Mazagon Dock (up 198%). Nobody needed a story about these companies. They were simply the strongest stocks in the market.

```series
title: Mazagon Dock — top of the momentum list in March 2023
from: 2022-03-01
to: 2024-03-31
line: india:MAZDOCK.NS | Mazagon Dock | log
line: india:MAZDOCK.NS / india:NIFTY500 | Mazagon Dock ÷ Nifty 500 | pane2
mark: 2023-03-31 | ranked 2nd of 300 on 12-1 momentum
caption: A stock already up about 200% in a year was a buy under the rule, not a sell. Over the next six months it rose another 231%.
```

Over the next six months the ten strongest names rose 74.5% on average (median 44.4%). The 300 stocks as a whole rose 33.8% on average (median 26.0%). That is **cross-sectional momentum**. "Cross-sectional" means each stock is compared with the other stocks on the same date. It is not compared with its own past.

**Why it can work.** Investors are slow to update. Good news (an order book, a margin upgrade, a new policy) reaches the price over months, not days. Analysts revise forecasts in small steps. Many fund managers buy only after a trend is well established. Each of these adds to a move that has already started.

**Who is on the other side.** Mostly investors who sell winners too early and hold losers too long. Behavioural research calls this the disposition effect. Also value buyers who sell a stock because it looks expensive after a big rise. When the trend ends, the momentum buyer is the one left holding.

**What it is not.** It is not a swing trade on one chart. There is no setup, no breakout and no chart stop. The whole decision is a rank, refreshed on a calendar. The swing trader's version, buying leaders out of bases, is in [the RS leaders guide](learn-strat-rs-leaders.md). The ranking measure itself is explained in [the relative strength guide](learn-price-rs.md).

## 2. When it works and when it doesn't

**It works best in steady trends.** Long bull markets with clear leadership suit it. In India those were 2010–2013 and 2017. Later ones were 2021 and 2023. The winners stay winners, and the portfolio rides them.

**It fails at sharp turns.** The worst months come when a market that has fallen a long way rebounds violently. The past losers are then the most beaten-down, high-beta stocks, and they jump the most. The past winners are often defensive stocks that held up in the fall, and they lag.

| Month | Market | What happened | Top tenth by momentum | All stocks | Bottom tenth |
|---|---|---|---|---|---|
| April 2009 | India, 300 most-traded | Rebound from the March 2009 low | +0.7% | +17.8% | +33.7% |
| May 2009 | India, 300 most-traded | Election result rally | +13.9% | +43.6% | +69.0% |
| October 2024 – February 2025 | India, 300 most-traded | Broad correction after a momentum boom | −29.2% | −23.3% | −21.1% |

All figures are equal-weight averages, before costs. Method in §8.

**It also struggles when leadership is crowded.** By September 2024 the Indian momentum list was full of railway, defence and PSU stocks that had risen 200–350% in a year. When the market turned, those fell hardest (§6).

**India versus US.** In the sort in §8, momentum was clearly profitable in India and weak in the US since 2005. The US result agrees with the published finding that US momentum returns have been lower since 2000. Indian markets have more retail participation, more small and mid caps, and more stocks moving on policy themes. Each of these may help momentum. None of it is guaranteed to last.

**Suits:** a patient investor with a large enough account to hold 20–30 stocks. It does not suit someone who wants to watch every position daily.

## 3. The rules

### Universe and filters

- **India:** the 200–300 stocks with the highest average daily traded value over the past 63 sessions. The Nifty 200 is a ready-made version of this list.
- **US:** the 500–1,000 most-traded stocks, or the S&P 500.
- Price at least ₹50 (India) or $10 (US) on the ranking day.
- At least 13 months of price history, so the 12-month return exists.
- **India only:** exclude stocks under exchange surveillance (ASM or GSM lists) or in the trade-for-trade segment. Those carry trading restrictions and price bands that make exits hard.
- Exclude ETFs, funds and stocks with a pending merger or delisting.

### Setup

The setup is the rank. On the last trading day of each month, for every stock in the universe:

- **12-1 momentum** = close 21 sessions ago ÷ close 252 sessions ago − 1. It skips the latest month, because last month's winners tend to give back a little the next month.
- **Volatility-adjusted momentum** (optional) = 12-1 momentum ÷ the annualised standard deviation of daily returns over the past 252 sessions. It favours steady risers over erratic ones.
- Rank all stocks from best to worst. The **buy list** is the top 10% (or the top N, with N between 20 and 30).

### Entry

- Buy every name on the buy list that you do not already hold.
- Trade on the first session after the ranking day. Use limit orders near the open price, or the closing session, not market orders at the open.
- Do not wait for a pullback or a breakout. Waiting changes the strategy.

### Initial stop

The classic rule has **no price stop**. Risk is controlled by holding many stocks and by the monthly re-rank. A stock that falls hard drops out of the list and is sold at the next rebalance.

If you need a hard limit for comfort, use a wide one: sell a stock that closes 30% below its entry price between rebalances. Test it, because tight stops on a monthly strategy usually cost more than they save.

### Exits

- **Rank exit (the main one):** at each rebalance, sell any holding that is no longer in the top 20%. This buffer (buy in the top 10%, sell below the top 20%) cuts turnover sharply.
- **Universe exit:** sell a stock that leaves the liquidity universe or goes into surveillance.
- **Market-regime exit (optional):** when the broad index (Nifty 500 or S&P 500) closes a month below its 10-month average, stop buying new names. Some versions also move to cash or a liquid fund.
- There is no profit target. Big winners are kept for as long as they stay near the top.

### Position size

- **Equal weight:** each holding gets 1/N of the strategy's capital, reset at each rebalance (or only when a weight drifts beyond 1.5 times its target).
- **Inverse-volatility weight (optional):** weight each stock by 1 ÷ its 63-day volatility, so a calm stock gets more money than a wild one.
- **Strategy-level volatility scaling (optional):** scale total exposure so the portfolio's recent volatility is near a target, for example 15–20% a year. Never above 100% invested unless you are deliberately using leverage. This is the Barroso and Santa-Clara idea in §5.

### Managing the trade

- Rebalance on a fixed calendar day, every month. Write the date down in advance.
- Between rebalances, do nothing except the optional 30% stop and corporate-action checks.
- Keep 2–5% cash for costs and rounding.
- After a market fall of 20% or more, expect the momentum list to be full of defensive stocks. That is when crash risk is highest. Halve the exposure, or rely on the volatility scaling, until the market has recovered half its fall.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Universe size | India 200–300; US 500–1,000 | Liquidity and diversity of choices | Smaller lists are more liquid but give fewer extreme winners |
| Liquidity window | 63 sessions | Which stocks qualify | Robust; 50–126 sessions give similar lists |
| Minimum price | ₹50 / $10 | Removes penny stocks | Low sensitivity above these levels |
| Lookback | 252 sessions (12 months) | Speed of the signal | 6–12 months all work in the literature; shorter means more turnover |
| Skip period | 21 sessions (1 month) | Avoids the one-month reversal | The skip mattered in US research; in the India sort here it made little difference |
| Volatility window | 252 sessions | Volatility adjustment | 126–252 sessions; adjustment lowers the volatility of the picks |
| Buy threshold | Top 10% or top 20–30 names | Concentration | Fewer names means bigger edge and bigger swings |
| Hold threshold | Top 20% | Turnover buffer | The single biggest lever on costs |
| Rebalance | Monthly (21 sessions) | Turnover and freshness | Quarterly or six-monthly cuts costs; returns usually fall a little |
| Optional hard stop | 30% below entry | Single-stock disasters | Tighter stops usually hurt |
| Regime filter | Index below its 10-month average | Bear-market exposure | Reduces crash losses but misses the first months of a recovery |
| Volatility target | 15–20% a year | Overall risk | Cuts exposure in turbulent markets; needs a daily or weekly check |
| Cash buffer | 2–5% | Costs, rounding | Low sensitivity |

## 5. Variations

- **Jegadeesh and Titman (1993)** — the original study. They ranked on 3–12 months of past return and held for 3–12 months, and found the 12-month lookback with a short hold among the strongest.
- **Carhart (1997)** — added a momentum factor (winners minus losers, 12-1) to explain fund returns. Most "momentum factor" data you will find follows this definition.
- **Novy-Marx (2012)** — found that the return from 7–12 months ago predicted better than the most recent 6 months. It suggests the older part of the lookback carries much of the signal.
- **Barroso and Santa-Clara (2015)** — scaled the momentum portfolio by its own recent volatility. That cut the size of the crashes considerably in their US data.
- **Daniel and Moskowitz (2016)** — showed when crashes happen (after market falls, during sharp rebounds) and proposed a dynamic version that reduces exposure then.
- **Gray and Vogel, *Quantitative Momentum* (2016)** — rank on 12-1 momentum, then prefer stocks whose gains came in many small steps rather than a few jumps (the "frog-in-the-pan" idea of Da, Gurun and Warachka). Rebalanced quarterly.
- **Andreas Clenow, *Stocks on the Move* (2015)** — ranks S&P 500 stocks by the slope of an exponential regression over 90 days times its R² (how straight the trend is). Sizes positions by ATR. Buys only when the S&P 500 is above its 200-day average.
- **Index versions.** MSCI and NSE publish momentum indices. ETFs and index funds track them, so you can own the idea without running it yourself.

### The NSE Nifty 200 Momentum 30

The best-known Indian implementation. As NSE describes it at launch (check the current methodology document, since NSE revises details):

1. **Universe:** the Nifty 200.
2. **Two raw scores:** the 6-month and the 12-month price return, each divided by the annualised standard deviation of daily returns over the past year.
3. **Standardise:** each score becomes a z-score across the eligible stocks. The two z-scores are averaged with equal weights.
4. **Normalise:** a positive average z becomes 1 + z. A negative one becomes 1 ÷ (1 − z). This keeps every score positive and squeezes the weak end.
5. **Select:** the 30 stocks with the highest normalised score.
6. **Weight:** free-float market cap times the normalised score. One stock is capped at 5%, or five times its weight in a plain cap-weighted version, whichever is lower.
7. **Rebalance:** every six months (June and December), with checks against SEBI's ETF concentration limits in between.

Three differences from the textbook rule matter. The index does not skip the latest month, as far as the published description goes. It rebalances twice a year, not monthly. And it weights by size, so large caps get more money than an equal-weight portfolio would give them.

```series
title: A Nifty 200 Momentum 30 ETF against the Nifty 50
from: 2022-08-19
to: 2026-10-13
rebase: 100
line: india:MOMENTUM.NS | Nifty 200 Momentum 30 ETF
line: india:NIFTY50 | Nifty 50
band: 2024-09-27 2025-04-09 | ETF −30.8%
caption: The ETF rose 82.7% from 19 August 2022 to 27 September 2024, against 47.4% for the Nifty 50. It then fell 30.8% to 9 April 2025, while the Nifty 50 fell 14.4%. Over the whole period it gained 41.0%, the Nifty 50 28.0%. The ETF price includes reinvested dividends; the Nifty 50 line does not.
```

The chart shows the strategy's character in one picture. It led strongly for two years, then gave back much of its lead in seven months.

## 6. Worked examples

All three use the rules in §3 on the 300 most-traded Indian stocks. They hold for six months, the way the NSE index does, to keep the arithmetic short. Prices are split-adjusted closes, before costs.

### A success: ranked on 31 March 2023

| Stock | 12-1 momentum | Return to 29 September 2023 |
|---|---|---|
| APAR Industries | +257% | +119% |
| Mazagon Dock | +198% | +231% |
| BLS International | +162% | +51% |
| CIE Automotive | +150% | +37% |
| Kirloskar Oil Engines | +137% | +36% |
| Karur Vysya Bank | +123% | +28% |
| Varun Beverages | +108% | +36% |
| Data Patterns | +94% | +53% |
| Kalyan Jewellers | +93% | +116% |
| Finolex Cables | +90% | +38% |

1. **Setup:** ranked at the March 2023 month-end. The Nifty 500 had fallen through 2022 and was close to its low.
2. **Entry:** all ten bought at the first session of April, equal weight.
3. **Stop:** none hit. No name fell 30% below entry.
4. **Result:** average +74.5%, median +44.4%. The whole list of 300 averaged +33.8%; the Nifty 500 rose 18.8%. Every one of the ten rose.

### A failure: ranked on 30 September 2024

| Stock | 12-1 momentum | Return to 28 February 2025 |
|---|---|---|
| Inox Wind | +350% | −37% |
| IFCI | +302% | −38% |
| Oil India | +289% | −41% |
| HUDCO | +286% | −32% |
| RVNL | +267% | −38% |
| Trent | +248% | −36% |
| Cochin Shipyard | +246% | −27% |
| NBCC | +218% | −39% |
| Godfrey Phillips | +217% | −26% |
| Suzlon | +206% | −38% |

1. **Setup:** the list was crowded with PSU, railway, shipbuilding and power-equipment stocks, several up three times or more in a year. That crowding is a warning, not a rule violation.
2. **Entry:** bought at the start of October 2024.
3. **Stop:** every one of the ten closed at least 30% below its entry close at some point before the end of February. The optional stop would have sold all of them, at roughly the loss they ended with anyway.
4. **Result:** average −35.0%. The 300 stocks averaged −23.3% and the Nifty 500 fell 18.0%.
5. **Would a monthly re-rank have helped?** Very little. Nine of the ten were still in the top 20% at the end of December 2024, three months into the fall. Only at the end of January 2025 did most of them drop out. A 12-month signal is slow by design.

```series
title: RVNL — a momentum leader that reversed
from: 2023-06-01
to: 2025-06-30
line: india:RVNL.NS | RVNL | log
line: india:RVNL.NS / india:NIFTY500 | RVNL ÷ Nifty 500 | pane2
mark: 2024-09-30 | ranked 5th of 300
caption: Ranked near the top after rising 267% in a year (12-1). It fell 38% over the next five months.
```

### A momentum crash: April and May 2009

The Nifty 500 fell 64.3% from January 2008 to 9 March 2009. At the end of March 2009 the "winners" were the stocks that had fallen least: consumer staples, drug makers and a few odd small names. In April the top tenth rose 0.7% on average while the bottom tenth rose 33.7%. In May the gap was larger: +13.9% against +69.0%.

Two months wiped out several years of the strategy's typical edge. That is what Daniel and Moskowitz describe for the US in 1932 and 2009. The rule in §3 to cut exposure after a 20% fall exists for this case.

## 7. Common mistakes

- **Ranking on the latest data, trading at the same close.** You cannot trade at a price you used to rank. Rank after the close, trade the next session.
- **Ranking on today's index members.** A 2015 test that uses today's Nifty 200 only contains stocks that later did well enough to be in it. That inflates results.
- **Chasing a single stock.** The edge is a portfolio average. One stock from the list is close to a coin toss.
- **Rebalancing too often.** Weekly re-ranking of a 12-month signal mostly creates costs.
- **No buffer.** Selling everything that slips from the top 10% to the 11th percentile doubles turnover for no benefit.
- **Quitting after a crash.** The strategy's losses come in bunches. Decide in advance what drawdown you will accept, and size for it.
- **Ignoring crowding.** When the whole list is one theme, it behaves like one position. Cap a sector at about a third of the portfolio.
- **Ignoring tax.** In India, gains on holdings under 12 months are short-term and taxed at a higher rate. A strategy with 30% monthly turnover is almost all short-term.

## 8. What the evidence says

**Published research.**

- Jegadeesh and Titman (1993): US winners minus losers earned roughly 1% a month over 1965–1989, before costs.
- Asness, Moskowitz and Pedersen (2013): momentum appears across stock markets worldwide and in other asset classes.
- Daniel and Moskowitz (2016): momentum has rare, very large losses concentrated in market rebounds.
- Barroso and Santa-Clara (2015): volatility scaling reduced those losses in their data.
- Indian studies (for example Sehgal and Balakrishnan, and later work on NSE stocks) have generally found a momentum effect over 3–12 month horizons, with the usual caveats about costs and small stocks.

**Event study: momentum deciles, India and US.**

*Method.* On each month-end, take the most-traded stocks (India: 300, from January 2009; US: 1,000, from January 2005). Use the average traded value over 63 sessions. Require a minimum price of ₹50 or $10, and at least 13 months of history. Rank by 12-1 momentum, split into tenths, and record each tenth's equal-weight return over the next month. Survivors only: the stored data covers today's listed stocks, so firms that delisted after a collapse are missing. No costs.

| Next-month average return | India (213 months) | US (261 months) |
|---|---|---|
| Bottom tenth | +0.91% | +0.31% |
| Middle (5th tenth) | +1.39% | +0.75% |
| Top tenth | +2.28% | +0.95% |
| All stocks | +1.51% | +0.70% |
| Top minus bottom | +1.38% (t 2.7) | +0.65% (t 1.6) |
| Months the top beat the bottom | 65% | 58% |
| Top tenth minus all stocks | +0.78% (t 2.6) | +0.25% (t 1.0) |

The t figure is a rough measure of how far a result stands out from chance. About 2 or more is usually taken as meaningful.

*What it shows.* In India the returns rose almost steadily from the bottom tenth to the top. In the US the pattern ran in the same direction but was weak. The latest month on its own (a one-month reversal) did not show a clear pattern in India. In the US, both last month's best and worst tenths lagged the middle.

*Crashes.* The worst months for top minus bottom were the 2009 rebounds in both markets. In India: −32.0% in April 2009 and −55.1% in May 2009. In the US: −33.7% in April 2009, and −27.6% in July 2026.

*Volatility adjustment.* Choosing the 30 stocks with the best volatility-adjusted score did about as well as the plain top 30. In India it was +0.81% a month above all stocks against +0.77%. In the US it was +0.35% against +0.13%. Neither US figure is reliable (t 1.0 and 0.3). The adjusted picks were calmer: their average annual volatility was 51% against 75% for the raw top 30 in the US.

*Turnover.* About a third of a top-30 list changed every month:

| Monthly turnover | Raw | Adjusted |
|---|---|---|
| India | 31% | 32% |
| US | 34% | 41% |

A top-20% hold buffer cuts that substantially.

**What is unknown.** Whether India's stronger effect continues as more money follows momentum indices. Whether the 2009-type crash repeats in the same form. And how much survivorship bias inflates the top tenth's figures; it may also inflate the bottom tenth, so the spread is less affected.

## 9. Building and testing it yourself

**Data.** Daily closes adjusted for splits and bonuses, daily volume, and ideally the historical index membership. You also need the list of stocks that delisted, with their final prices. Free sources rarely have that, which is why most home-made tests are survivors only.

**Look-ahead traps.**

- Rank on the close of day *t*, trade at the open or close of *t*+1.
- Build the liquidity universe from data up to *t* only.
- Use the index membership that applied on *t*, not today's.

**Costs (India, delivery trades, approximate — check current rates).**

| Item | Approximate size |
|---|---|
| STT | 0.1% on the buy and 0.1% on the sell |
| Stamp duty | 0.015% on the buy |
| Exchange and SEBI charges | about 0.003–0.004% each side |
| Brokerage | zero to 0.1% each side, depending on the broker |
| GST | 18% on brokerage and exchange charges |
| Depository charge | a flat fee per stock sold, about ₹15–20 |
| Slippage | 0.1–0.3% each side for liquid stocks, more for mid caps |

A round trip is roughly 0.3–0.6% before tax. With 30% of the portfolio replaced every month, costs are close to 1–2% a year. In the US commissions are near zero, but spreads and market impact still apply.

**Tax.** In India, short-term gains (held under 12 months) are taxed at 20%, long-term gains at 12.5% above an annual exemption, under the rules from July 2024. Model tax in the test if you trade a personal account.

**Parameters to test, and how not to over-fit.**

- Test a small grid: lookback 6, 9 and 12 months; buy threshold top 10% and top 20%; rebalance monthly and quarterly.
- Prefer a parameter area where all neighbours work, not the single best cell.
- Split the history: choose parameters on 2009–2018, then look once at 2019 onwards.
- Check each market separately. A rule that works in India and fails in the US may still be fine for India, but you should know.

**What a good test reports.** Return and volatility against an equal-weight benchmark of the same universe. The worst month and the worst drawdown, and when they happened. Turnover and costs per year. Results with and without the regime filter. The share of the return that came from the top five holdings.

```
every month-end t:
    universe = 300 most-traded stocks (63-day traded value), price >= 50, history >= 13 months
    for each stock s in universe:
        mom[s] = close[s, t-21] / close[s, t-252] - 1
        vol[s] = stdev(daily returns over t-251..t) * sqrt(252)
        score[s] = mom[s] / vol[s]          # or mom[s] for the plain version
    rank = percentile of score
    sell holdings with rank < 80th percentile (or that left the universe)
    buy stocks with rank >= 90th percentile not already held
    weights = equal (or 1/vol), scaled so portfolio vol ≈ target, capped at 100%
    execute at t+1
```

## 10. Checklist

- [ ] The universe is defined by liquidity on the ranking date, not by today's index list
- [ ] The rank uses closes up to the ranking date only; orders go in the next session
- [ ] The latest month is skipped (or I have tested that skipping does not matter)
- [ ] The buy list is the top 10% (or top N), the hold buffer is the top 20%
- [ ] No sector is more than about a third of the portfolio
- [ ] Market check: did the index fall 20% or more recently? If so, exposure is reduced
- [ ] Surveillance and trade-for-trade stocks are removed (India)
- [ ] Costs and tax for this month's turnover are estimated
- [ ] The rebalance date for next month is in the calendar
- [ ] I know the worst drawdown I will sit through, and the position sizes fit it

## Further reading

- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency", *Journal of Finance*, 1993.
- Mark Carhart, "On Persistence in Mutual Fund Performance", *Journal of Finance*, 1997.
- Robert Novy-Marx, "Is Momentum Really Momentum?", *Journal of Financial Economics*, 2012.
- Clifford Asness, Tobias Moskowitz and Lasse Pedersen, "Value and Momentum Everywhere", *Journal of Finance*, 2013.
- Pedro Barroso and Pedro Santa-Clara, "Momentum Has Its Moments", *Journal of Financial Economics*, 2015.
- Kent Daniel and Tobias Moskowitz, "Momentum Crashes", *Journal of Financial Economics*, 2016.
- Wesley Gray and Jack Vogel, *Quantitative Momentum*, Wiley, 2016.
- Andreas Clenow, *Stocks on the Move*, 2015.
- NSE Indices, Nifty 200 Momentum 30 index methodology document (niftyindices.com).
- Related guides: [relative strength](learn-price-rs.md), [dual momentum](learn-strat-dual-momentum.md), [sector rotation](learn-strat-sector-rotation.md), [backtesting](learn-test-backtesting.md).
