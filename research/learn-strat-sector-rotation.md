# Sector rotation — hold the strongest parts of the market, and move when leadership changes

**In short**

- Divide the market into sectors (banks, IT, energy, pharma …), rank them every month, and hold the strongest two or three through index funds or ETFs.
- There are two ways to rank: by **relative strength** (which sectors have risen most) or by the **business cycle** (which sectors tend to lead in the current phase of the economy).
- With only 9–12 sectors to choose from, the edge is small and noisy. In the US, ranking the nine original SPDR sectors by past return showed no edge over 1999–2026 in the study here. In India, a sector sort built from stocks did a little better, mostly by avoiding the weakest sectors.
- Big rotations, like energy in 2021–2022 or Indian IT in 2020–2021, are easy to see afterwards. A rule catches part of them and also gets caught at the turn.
- Use it as a filter for where to look for stocks, or as a slow, low-cost allocation. Do not expect a large edge from sector ETFs alone.

---

## 1. The idea

At the end of March 2021, the US energy sector ETF (XLE) had risen 63.8% in six months. Financials (XLF) had risen 41.5%, industrials (XLI) 27.9%. They were the top three of the nine original sector funds. A sector-rotation rule would have held those three.

```series
title: US energy against the S&P 500, 2020–2023
from: 2020-06-01
to: 2023-06-30
line: us:XLE / us:SPY | Energy ETF ÷ S&P 500 ETF
mark: 2021-03-31 | energy ranked 1st of 9 on 6-month return
mark: 2022-11-07 | ratio peak
caption: The ratio bottomed on 6 November 2020 and nearly tripled to its peak two years later. A 6-month ranking had energy at the top by March 2021, well after the low and well before the peak.
```

Energy kept leading for more than eighteen months. Over calendar 2022 the S&P 500 ETF fell 19.5%. Energy rose 57.6%. A rule that came late still caught a large part of the move, though not smoothly (§6).

That is the case for **sector rotation**: money flows between parts of the market in waves that last months, not days. The guide on [sectors and groups](learn-sectors-groups.md) explains how sectors are defined and why stocks in one group move together.

**Why it can work.** A sector shares one set of drivers: oil prices for energy, interest rates for banks, the dollar and US tech budgets for Indian IT. When a driver changes, it changes slowly, and investors take months to re-price the whole group. Large funds also move money between sectors gradually, so their buying spreads over weeks.

**Who is on the other side.** Investors who hold every sector at index weight and never move. Fund managers who must stay close to their benchmark. And value buyers adding to the weakest sectors because they look cheap. When the rotation ends, the late momentum buyer is on the wrong side.

**Two ways to choose sectors.**

1. **By relative strength:** rank sectors by their past return and hold the strongest. It needs no forecast. It reacts after a move has started.
2. **By the business cycle:** decide which phase the economy is in, and hold the sectors that have tended to lead in that phase. It tries to move earlier, but depends on reading the cycle correctly. The [business-cycle guide](learn-macro-cycle.md) has the phase map.

## 2. When it works and when it doesn't

**It works when one driver dominates for a long time.** Oil and inflation in 2021–2022. Lower rates and digital demand for IT in 2020–2021. A policy push for railways and defence in India in 2022–2024. These themes lasted long enough for a slow ranking to catch them.

**It fails at sharp turns in the driver.** At the end of December 2021, the US leaders were technology, consumer discretionary and utilities. Rates then rose fast, and over 2022 technology fell 28.4% and consumer discretionary 36.8%. Energy, ranked near the bottom on 6-month return, rose 57.6% (§6).

**It struggles when sectors move together.** In a broad sell-off or a broad rally, the gaps between sectors are small. The ranking then changes on noise.

**The business-cycle map is a tendency, not a timetable.** Phases are clear only in hindsight. One dominant theme (US technology since 2010) can override the map for years. Stock markets also move to the next phase's leaders before the economy gets there.

**India versus US.** India's official sector indices are heavily weighted to a few large companies. Nifty Bank is dominated by a handful of private banks, and Nifty IT by its largest names. Its sector ETFs are fewer and often thinly traded. On the other hand, Indian rotations have often been strong and policy-driven (PSU banks, defence, railways, power). An equal-weight view of each sector, built from many stocks, can show a rotation that the cap-weighted index hides.

## 3. The rules

### Universe and filters

- **US:** the nine original SPDR sector ETFs (XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY), plus real estate (XLRE) and communication (XLC) if you accept shorter histories.
- **India:** sector index funds or ETFs with a daily traded value of at least ₹1 crore. Nifty Bank, IT, Pharma, FMCG, Auto, Metal, PSU Bank, Energy, Infrastructure and Realty indices all have tracking products. Check each product's liquidity before including it.
- Use total-return or dividend-adjusted data where possible. Utilities and staples pay much higher dividends than technology, so price-only data biases the ranking.

### Setup

**Relative-strength version.** On the last trading day of each month:

1. Compute each sector's **6-month return** (range 3–12 months; a blend of 3, 6 and 12 is common).
2. Rank the sectors from best to worst.
3. **Absolute filter (optional):** a sector qualifies only if it closes above its 10-month average.

**Business-cycle version.** Define the phase with indicators you can check every month, for example:

| Phase | Testable condition (example) | Sectors to hold |
|---|---|---|
| Early recovery | PMI below 50 but up for 3 months; yield curve steepening | Discretionary, financials, industrials, small caps |
| Mid-cycle | PMI above 50; policy rate stable or rising slowly | Technology, industrials, communication |
| Late cycle | PMI falling from a high; inflation rising; policy rate rising | Energy, materials, then staples and health care |
| Recession | PMI below 50 and falling; policy rate being cut | Staples, health care, utilities, cash |

The exact thresholds are yours to choose and test. Write them down before testing, not after.

### Entry

- Buy the top 3 sectors (range 2–4), equal weight, on the first session of the new month.
- India: sector ETFs often trade away from their fair value. Use limit orders near the indicative NAV (iNAV) that the fund house publishes, or buy through an index fund at the day's NAV.
- If fewer than 3 sectors pass the absolute filter, put the empty slots in a liquid fund or T-bills.

### Initial stop

None in the classic version. The monthly re-rank is the exit. A sector ETF rarely falls fast enough for a single-day stop to help, except in a market crash.

### Exits

- **Rank exit:** sell a sector when it falls out of the top 5 (a buffer that cuts turnover). Replace it with the highest-ranked sector not held.
- **Absolute exit:** sell a sector that closes a month below its 10-month average, even if still in the top 5.
- **Business-cycle version:** sell when the phase changes by your written rules.

### Position size

- Equal weight across the held sectors: about one third each with three sectors.
- Cap any sector at 40% after drift. Rebalance to equal weight at each monthly check, or only when a weight is more than 5 percentage points off.

### Managing the trade

- One check a month, on a fixed day.
- Track how often the top three changes. If it changes nearly every month, the lookback is too short or the buffer too small.
- Use the result as a map for stock picking too: the strongest stocks in the top sectors are the swing trader's watchlist (see [the RS leaders guide](learn-strat-rs-leaders.md)).

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Number of sectors in the menu | 9–11 (US); 8–12 (India) | Choice | Fewer choices mean a noisier ranking |
| Lookback | 6 months (range 3–12) | Signal speed | In the US test here no lookback showed a reliable edge |
| Number held | 3 (range 2–4) | Concentration | Holding 1–2 adds risk; 5+ approaches the index |
| Hold buffer | Top 5 | Turnover | Large effect on costs |
| Absolute filter | Close above the 10-month average | Bear-market exposure | Cuts crash losses; adds whipsaw |
| Rebalance | Monthly | Turnover | Quarterly is cheaper and usually similar |
| Weight drift band | 5 percentage points | Rebalancing trades | Low sensitivity |
| Minimum ETF liquidity (India) | ₹1 crore a day | Execution | Thin ETFs can trade 0.5%+ away from NAV |

## 5. Variations

- **Industry momentum.** Moskowitz and Grinblatt (1999) found that ranking 20 US industries by past 6-month return predicted the next months well. They also found that much of individual stock momentum comes from industry momentum. Their industries were finer than today's 11 sectors.
- **Faber's sector rotation.** Mebane Faber (2010) ranked US sector portfolios by past return over periods such as 3–12 months and held the top third. He added a 10-month moving-average filter to cut drawdowns.
- **The business-cycle approach.** Sam Stovall's *Standard & Poor's Guide to Sector Investing* (1996) popularised the phase map. Fidelity and other fund houses publish their own versions.
- **Monetary conditions.** Conover, Jensen, Johnson and Mercer (2008) rotated between cyclical and defensive sectors according to whether the Federal Reserve was easing or tightening.
- **Relative-rotation graphs.** A chart method that plots each sector's relative strength against its rate of change, in four quadrants (leading, weakening, lagging, improving). It is a way to look at the same ranking, not a different signal.
- **Group screens.** Many stock traders skip sector funds altogether. They use the ranking only to find the strongest industry groups, then buy stocks inside them.

```series
title: Nifty IT against the Nifty 50, 2020–2023
from: 2020-01-01
to: 2023-06-30
line: india:^CNXIT / india:^NSEI | Nifty IT ÷ Nifty 50
mark: 2020-06-30 | IT 6-month return −5.7%
mark: 2021-12-31 | IT 6-month return +32.7%, ranked first
caption: IT rose 56% against the Nifty from mid-2020 to its peak on 30 December 2021. It was ranked first at the end of 2021, just before the ratio fell 32.7% to April 2023.
```

## 6. Worked examples

Prices are month-end closes; US ETF prices exclude dividends. Each example ranks on 6-month return and holds the top 3.

### US, March 2021 — catching a long rotation

| Sector | 6-month return to 31 March 2021 | Next 3 months |
|---|---|---|
| Energy (XLE) | +63.8% | +9.8% |
| Financials (XLF) | +41.5% | +7.8% |
| Industrials (XLI) | +27.9% | +4.0% |
| Average of all nine | | +5.8% |

1. **Setup:** three cyclical sectors at the top, after the November 2020 vaccine news.
2. **Entry:** equal weight on 1 April 2021.
3. **Result over 3 months:** +7.2% on average against +5.8% for all nine. Energy ranked in the top three at 18 of the 22 month-ends from March 2021 to December 2022. It also fell to last place twice (August and December 2021), so even a buffered rule sold it and bought it back.

### US, December 2021 — caught at the turn

| Sector | 6-month return to 31 December 2021 | Next 3 months | Calendar 2022 |
|---|---|---|---|
| Technology (XLK) | +17.8% | −8.6% | −28.4% |
| Consumer discretionary (XLY) | +14.5% | −9.5% | −36.8% |
| Utilities (XLU) | +13.2% | +4.0% | |
| Energy (XLE), ranked in the bottom three | | +37.7% | +57.6% |
| Average of all nine | | +1.3% | |

1. **Setup:** two growth sectors and one defensive one at the top.
2. **What changed:** the Federal Reserve turned to fast rate rises. Growth stocks, whose value depends most on distant profits, fell hardest.
3. **Result over 3 months:** −4.7% on average for the three, against +1.3% for all nine. The rule moved into energy only after energy had already risen sharply.

### India, June 2020 — a defensive sector leads out of the crash

| Index | 6 months to 30 June 2020 | Next 3 months |
|---|---|---|
| Nifty Pharma | +24.2% | +17.9% |
| Nifty IT | −5.7% | +35.2% |
| Nifty Bank | −33.6% | +0.4% |
| Nifty 50 | −15.3% | +9.2% |

1. **Setup:** pharma was the only one of the three sector indices with a positive 6-month return.
2. **Entry:** pharma (and, with a top-two rule, IT).
3. **Result:** pharma beat the Nifty by 8.7 percentage points over the next 3 months. IT, ranked second, did even better. Banks, ranked last, went nowhere.

### India, December 2021 — the leader that reversed

1. **Setup:** Nifty IT had risen 32.7% in six months, against 10.4% for the Nifty 50. It ranked first.
2. **Entry:** start of January 2022.
3. **Result:** over the next six months IT fell 28.1%; the Nifty 50 fell 9.1%. The ratio chart in §5 shows the turn came within days of the ranking.

## 7. Common mistakes

- **Expecting a big edge from a short list.** With 9–11 choices, chance swamps any small advantage for years at a time.
- **Ranking on price only.** It biases against high-dividend sectors such as utilities and staples.
- **Chasing last month's winner.** A 1-month ranking changed the top three in almost every month in the US test, with no gain.
- **Mixing levels.** Comparing a cap-weighted Nifty Bank with an equal-weight "metals" basket is not comparing like with like.
- **Trusting the cycle map too much.** Write down testable rules for each phase, or the "phase" will be decided after looking at prices.
- **Ignoring ETF spreads in India.** A sector ETF that trades ₹20 lakh a day can cost more to enter than a month's expected edge.
- **Concentration.** Three sectors that share one driver (banks, NBFCs and real estate all depend on rates) are one bet.

## 8. What the evidence says

**Published research.** Moskowitz and Grinblatt (1999) found strong industry momentum in US data over 1963–1995. They used 20 industries. Faber (2010) reported that holding the top third of US sectors by past return beat an equal-weight sector portfolio over a long history, with large swings. Studies of the business-cycle map find that sector returns do differ by phase on average. They also find the phases hard to identify in real time.

**Event study: sector ranks and the next month.**

*Method.*

- US: the nine original SPDR sector ETFs, month-end closes, 1999–2026, price only.
- India: 11 sectors built as equal-weight averages of the 300 most-traded stocks each month. The Indian data runs 2008–2026. The stocks are chosen at the start of each month by 63-day traded value.

Sector labels are today's; stocks that delisted are missing. Each month, sectors were ranked on past return; the table shows the top three's average next-month return minus the average of all sectors. No costs.

| Ranked on | US: top 3 minus all | US: top 3 won | India: top 3 minus all | India: bottom 3 minus all |
|---|---|---|---|---|
| 1 month | −0.10% (t −0.8) | 47% | | |
| 3 months | −0.01% (t −0.1) | 55% | +0.42% (t 2.0) | −0.22% (t −0.7) |
| 6 months | −0.04% (t −0.3) | 51% | +0.23% (t 1.2) | −0.52% (t −3.2) |
| 12 months | +0.08% (t 0.7) | 54% | +0.24% (t 1.1) | −0.22% (t −1.2) |

The t figure is a rough measure of how far a result stands out from chance; about 2 or more is usually taken as meaningful.

*What it shows.* In the US, ranking the nine sector ETFs by past return gave no edge in any lookback over 1999–2026. In India, the top three built from stocks did slightly better than average. The clearer result was at the bottom: the three weakest sectors over 6 months lagged by about half a percent a month. In both markets the top three changed often: in 68% of months (US) and 61% (India) on a 6-month ranking.

*Caveats.* Twenty-odd years of nine or eleven sectors is a small sample. The India test uses sector labels assigned today, and equal-weight baskets you could not buy as one fund. The US test ignores dividends, which slightly penalises utilities and staples.

**What is unknown.** Whether the strong industry momentum in older research still holds for broad sectors traded through ETFs, which many investors now use for exactly this purpose. Whether India's weakest-sector effect is large enough to survive costs in tradable products.

## 9. Building and testing it yourself

**Data.**

- Total-return series for each sector product, or the sector index plus its dividend yield.
- For India, also the sector indices' history before the ETFs existed, with the caution that you could not trade them then.
- A cash series for the absolute filter's empty slots.

**Look-ahead traps.**

- Sector definitions change. The US moved some large companies from technology to the new communication sector in 2018. Using today's definitions on old data mixes the two.
- Ranks use month-end closes; trades happen the next session.
- In a stock-built sector test, choose the basket's members with data up to the ranking date only.

**Costs (India, approximate).**

| Item | Approximate size |
|---|---|
| STT on equity ETF units | 0.001% on the sell side |
| Stamp duty | 0.015% on the buy |
| Brokerage | zero to 0.1% each side |
| ETF spread and distance from NAV | 0.05–0.5%, larger for thin ETFs |
| Expense ratio | 0.1–0.5% a year |

Index funds avoid the spread but trade only at the day's NAV, and may charge an exit load for short holdings.

**Parameters to test.**

| Parameter | Values |
|---|---|
| Lookback | 3, 6 and 12 months, and a blend |
| Sectors held | top 2, 3 and 4 |
| Hold buffer | top 4 and top 5 |
| Absolute filter | with and without |
| Rebalance | monthly and quarterly |

Look for a broad area that works, not one best cell.

**What a good test reports.** Return and drawdown against an equal-weight portfolio of all sectors (the fair benchmark, not the cap-weighted index). Turnover and costs. The share of months each sector was held. Results by sub-period, because sector themes come and go.

```
every month-end t:
    for each sector ETF s:
        r[s] = close[s, t] / close[s, t-6 months] - 1      # total return if available
        ok[s] = close[s, t] > average(month-end closes over the last 10 months)
    ranked = sectors sorted by r, best first
    keep holdings that are in ranked[0:5] and ok
    fill empty slots (up to 3) with the best-ranked ok sectors not held
    slots still empty -> liquid fund / T-bills
    trade at t+1, equal weight
```

## 10. Checklist

- [ ] The menu of sectors and products is fixed in advance
- [ ] Each product is liquid enough (India: ₹1 crore a day or more, or use an index fund)
- [ ] Ranking uses total-return data where possible, and month-end closes only
- [ ] The top 3 is checked against the absolute filter
- [ ] The three sectors do not all depend on the same driver
- [ ] The buffer (top 5) is applied before selling a holding
- [ ] For a cycle-based choice, the phase is decided by the written rules
- [ ] The result is also used as a map for stock selection, not only for ETFs

## Further reading

- Tobias Moskowitz and Mark Grinblatt, "Do Industries Explain Momentum?", *Journal of Finance*, 1999.
- Mebane Faber, "Relative Strength Strategies for Investing", Cambria Investment Management working paper, 2010.
- Sam Stovall, *Standard & Poor's Guide to Sector Investing*, McGraw-Hill, 1996.
- C. Mitchell Conover, Gerald Jensen, Robert Johnson and Jeffrey Mercer, "Sector Rotation and Monetary Conditions", *Journal of Investing*, 2008.
- Related guides: [sectors and groups](learn-sectors-groups.md), [the business cycle](learn-macro-cycle.md), [cross-sectional momentum](learn-strat-xs-momentum.md), [dual momentum](learn-strat-dual-momentum.md), [RS leaders](learn-strat-rs-leaders.md).
