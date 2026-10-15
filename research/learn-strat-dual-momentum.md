# Dual momentum — own the strongest asset, and step aside when nothing beats cash

**In short**

- Once a month, compare a few broad assets by their 12-month return. Hold the strongest one, but only if it has beaten cash. Otherwise hold bonds or a liquid fund.
- The two checks are **relative momentum** (which asset is stronger) and **absolute momentum** (is it beating cash at all). Gary Antonacci named the combination dual momentum.
- Its value is avoiding most of a long bear market, as in 2000–2002 and 2008. Its cost is whipsaw: selling near a low and buying back higher after a quick rebound.
- In India, a version that chooses between the Nifty, gold and a liquid fund would have held gold through the 2020 crash and most of 2025. It also switched 32 times between January 2010 and September 2025.
- It is a slow, rules-only allocation for the core of a portfolio, not a trading strategy for single stocks.

---

## 1. The idea

At the end of July 2019, the Nifty 50 (with dividends) had returned −0.6% over twelve months. Gold had returned 15.7%. A liquid fund had returned 4.1%. A dual-momentum investor sold the Nifty and bought gold.

Eight months later, at the end of March 2020, the Nifty had fallen 21.8% from that switch. Gold had risen 24.6%. The investor stayed in gold until February 2021, when the Nifty's 12-month return passed gold's again.

```series
title: India — Nifty 50 with dividends, gold and a liquid fund
from: 2010-01-01
to: 2025-09-30
rebase: 100
line: india:NIFTY50_TR | Nifty 50 total return
line: india:GOLD | Gold (INR)
line: india:CASH_FUND | Liquid fund
band: 2019-07-31 2021-02-26 | the rule held gold
caption: The three choices of an India version, restated to 100 in January 2010. Gold and the Nifty took turns leading; the liquid fund rose slowly and steadily.
```

**Relative momentum** picks the stronger of two or more assets. It is the same idea as [cross-sectional momentum](learn-strat-xs-momentum.md), applied to a handful of asset classes instead of hundreds of stocks.

**Absolute momentum** (also called time-series momentum) asks a different question: has this asset beaten cash over the past year? If the best asset has not, the rule holds a safe asset instead. Moskowitz, Ooi and Pedersen (2012) documented it across many futures markets.

**Why it can work.** Big bear markets in stocks usually come with a slow economic decline. Prices fall for months before the worst part. A 12-month rule notices the decline late, but often before the deepest losses. Trends across whole asset classes also persist, for the same reasons as stock trends: slow reaction to news, and investors who follow performance.

**Who is on the other side.** Investors who hold stocks through any decline, and those who buy every dip. In a long bear market they absorb the losses the rule avoids. In a quick V-shaped fall, they win and the rule loses.

## 2. When it works and when it doesn't

**It works in long, grinding bear markets.** The US in 2000–2002 is the classic case. The US in 2008–2009 is the other. In both, the 12-month return fell below cash early enough to avoid much of the fall.

**It fails in fast falls with fast recoveries.** India in March 2020 is the example. The Nifty's 12-month return dropped below cash only after the crash. By the time it turned positive again, the Nifty had already risen 31.6% from the exit (§6).

**It fails in sideways, choppy markets.** When the 12-month return hovers near the cash return, the signal flips back and forth. Each flip costs money and often lands on the wrong side.

**It needs a safe asset that is actually safe.** In 2022 US bonds fell with stocks, because interest rates rose fast. The rule moved into bonds and lost money there too (§6).

| Market condition | What the rule does | Typical outcome |
|---|---|---|
| Long bull market | Stays in equities | Matches the market, minus a little for occasional false exits |
| Slow bear market (12+ months) | Exits after the first part of the fall | Avoids much of the loss |
| Crash and quick recovery (under 6 months) | Exits near the low, re-enters higher | Loses against buy-and-hold |
| Sideways market | Several switches | Small losses from whipsaw |
| Stocks and bonds falling together | Moves to bonds, which also fall | No protection unless cash is the safe asset |

**India notes.** India has had no long bear market since 2008–2009 in the stored data. Its falls in 2011 and 2015–2016 were shorter. So were those in 2020 and late 2024. So the absolute check mostly cost money over 2010–2025 (§8).

Gold has been a strong alternative in rupees, partly because the rupee weakened against the dollar over the period. That makes the relative check between Nifty and gold more useful in India than the absolute check alone.

## 3. The rules

### Universe and filters

Pick a small menu of broad, cheap, liquid instruments. Two standard menus:

| Role | US version (Antonacci's GEM) | India version |
|---|---|---|
| Home equities | S&P 500 fund | Nifty 50 index fund or ETF |
| Second risky asset | International stocks (MSCI ACWI ex-US or EAFE fund) | Gold ETF (or a Nasdaq 100 fund in rupees) |
| Safe asset | US aggregate bond fund | Liquid fund or overnight fund |
| Cash yardstick | 3-month Treasury bill | Liquid fund return |

Use total-return data (dividends and coupons included) for every comparison. A price-only index understates equities by the dividend yield.

### Setup

On the last trading day of each month:

1. Compute each asset's **12-month total return**: value today ÷ value 12 months ago − 1.
2. **Absolute check:** is the home equity's 12-month return above the cash yardstick's 12-month return?
3. **Relative check:** if yes, which of the risky assets has the highest 12-month return?

### Entry

- If the absolute check passes, hold the risky asset with the highest 12-month return.
- If it fails, hold the safe asset.
- India version with gold: if the Nifty fails the absolute check but gold beats cash, hold gold; if both fail, hold the liquid fund.
- Switch on the first session of the new month, with a limit order near the price or through a fund's normal purchase.

### Initial stop

None. The monthly signal is the only exit. A daily stop would turn a slow allocation rule into a different strategy.

### Exits

- **Signal exit:** sell when a different asset wins at the month-end check.
- **Optional buffer:** switch only when the new winner beats the current holding by at least 1–2 percentage points of 12-month return. That reduces flips when two assets are almost tied.
- No profit target and no time limit.

### Position size

- 100% of the money assigned to this strategy goes into one asset at a time.
- Decide in advance what share of total wealth follows the rule. Many people use it for the core 30–70% of their long-term money, not all of it.

### Managing the trade

- Check once a month, on a fixed day. Do not look at the signal in mid-month.
- Keep a log of each switch, the 12-month returns that caused it, and the cost.
- In a taxable account, note the holding period before a switch. In India, selling equity held under 12 months creates short-term gains.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Lookback | 12 months (range 6–12) | Signal speed | Shorter lookbacks switch more often; Antonacci uses 12 |
| Check frequency | Monthly | Turnover | Weekly checks add switches without a clear gain |
| Cash yardstick | 3-month T-bill (US); liquid fund (India) | Absolute check threshold | Some versions use zero instead of cash |
| Risky assets | 2 (home, international or gold) | Diversity of choices | More assets add choices and more switching |
| Safe asset | Aggregate bonds (US); liquid fund (India) | Where money waits | Long bonds can fall in a rate shock; cash cannot |
| Switch buffer | 0–2 percentage points | Whipsaw | Small buffers cut flips with little loss of signal |
| Share of wealth | 30–70% | Overall impact | A personal choice, not a test result |

## 5. Variations

- **Antonacci's Global Equity Momentum (GEM).** From *Dual Momentum Investing* (2014). S&P 500 against MSCI ACWI ex-US for the relative check; S&P 500 against Treasury bills for the absolute check; US aggregate bonds as the safe asset; 12-month lookback, monthly.
- **Antonacci's earlier paper.** "Risk Premia Harvesting Through Dual Momentum" applies the same two checks within pairs of asset classes: equities, credit, real estate and economic stress (gold and Treasuries).
- **Time-series momentum.** Moskowitz, Ooi and Pedersen (2012) apply only the absolute check, to each of many futures markets, with position sizes scaled by volatility.
- **Faber's moving-average rule.** Mebane Faber (2007) holds each asset class only while its price is above its 10-month average. It is a close cousin of the absolute check.
- **Blended lookbacks.** Some practitioners average the 1-, 3-, 6- and 12-month returns, to react faster. Faster rules exit sooner in crashes and switch more in chop.
- **India menus.** Nifty 50 against a Nasdaq 100 fund in rupees, with a liquid fund as the safe asset. Or Nifty 50 against the Nifty Midcap 150. Both follow the same logic; test them before trusting them.

```series
title: US, 2007–2010 — S&P 500, international stocks and 7–10 year Treasuries
from: 2007-06-01
to: 2010-06-30
rebase: 100
line: us:SP500_TR | S&P 500 total return
line: us:INTL | International stocks (EAFE fund)
line: us:BONDS | 7–10 year Treasuries
band: 2008-01-31 2009-10-30 | absolute check failed: in bonds
caption: The S&P 500's 12-month return fell below the T-bill's at the end of January 2008. The rule held Treasuries until the end of October 2009.
```

## 6. Worked examples

All returns are total returns from stored data, month-end to month-end, before costs and tax. The US uses a 7–10 year Treasury fund as the safe asset, a simpler stand-in for Antonacci's aggregate bond index.

### US 2008 — the case the rule is built for

| Month-end | S&P 500, 12 months | International | Treasuries | T-bills | Decision |
|---|---|---|---|---|---|
| December 2007 | +5.4% | +10.0% | +10.4% | +4.6% | Hold international |
| January 2008 | −2.4% | −0.1% | +14.5% | +4.4% | Absolute check fails: Treasuries |
| September 2009 | −6.8% | +0.4% | +7.7% | +0.2% | Stay in Treasuries |
| October 2009 | +9.9% | +23.7% | +8.5% | +0.1% | Back in: international |

1. **Exit:** at the end of January 2008, the S&P 500's 12-month return (−2.4%) was below the T-bill's (+4.4%).
2. **Held:** Treasuries for 21 months. They returned +9.3%.
3. **What was avoided:** over the same months the S&P 500 returned −21.5%. Inside that period it fell 51.5% from its May 2008 high to 9 March 2009.
4. **Re-entry:** at the end of October 2009, about 7 months after the low. The rule missed the first leg of the recovery, which is normal.

### US 2022 — the safe asset was not safe

1. **Exit:** at the end of April 2022 the S&P 500's 12-month return was +0.1%, just below the T-bill's +0.2%. The rule moved to Treasuries.
2. **Held:** Treasuries until the end of June 2023. They returned −3.5%, because rates rose fast.
3. **Missed:** the S&P 500 returned +9.7% over the same months, after a fall of 16.7% inside the period.
4. **Lesson:** when inflation is the problem, bonds can fall with stocks. Using T-bills as the safe asset would have avoided the bond loss.

### India 2019–2021 — the relative check earns its keep

1. **Switch to gold:** end of July 2019. Nifty 12-month return −0.6%, gold +15.7%, liquid fund +4.1%.
2. **Held through the crash:** from the switch to the end of March 2020, the Nifty fell 21.8% and gold rose 24.6%. The Nifty's worst fall in the period was 36.3%, peak to low.
3. **Switch back:** end of February 2021, when the Nifty's 12-month return (+30.9%) passed gold's (+7.7%).
4. **Result:** over the whole holding, gold returned +31.3% and the Nifty +32.8%. The rule gave up nothing in return and avoided the crash. Gold itself fell 18.4% from its August 2020 high during the holding, so it was not a smooth ride.

### India 2020 — the absolute check alone would have failed

Suppose an investor used only the absolute check (Nifty or liquid fund, no gold).

1. **Exit:** end of March 2020, after the crash. The 12-month return was −24.0%.
2. **Re-entry:** end of August 2020.
3. **Missed:** the Nifty rose 31.6% while the investor sat in the liquid fund, which earned 0.9%.

This is the textbook whipsaw. The exit came after the damage, and the re-entry came after the recovery.

## 7. Common mistakes

- **Using price indices.** Comparing a price index with a bond fund's total return biases the result against equities.
- **Checking the signal daily.** The rule is defined on month-end data. Daily checks invite exits on noise.
- **Treating long bonds as cash.** In a rate shock they can fall sharply. Know which safe asset you hold and why.
- **Too many assets.** Adding ten choices turns a simple rule into a fitted one, and adds switches.
- **Abandoning it after a whipsaw.** Whipsaws are the price of the crash protection. Expect several in a row.
- **Ignoring tax.** Each switch out of equity held under 12 months is a short-term gain in India.
- **Expecting it to beat a bull market.** In a long rise it will roughly match buy-and-hold at best.
- **Comparing assets in different currencies without thinking.** Gold in rupees includes the rupee's fall against the dollar. That is a real return for an Indian investor, but it is a currency bet as well as a gold bet.
- **Changing the menu after a bad year.** Swapping gold for another asset because gold lagged last year is fitting the rule to the past.

## 8. What the evidence says

**Published research.** Moskowitz, Ooi and Pedersen (2012) found time-series momentum in 58 futures and forward markets over about 25 years. Antonacci's book reports that GEM beat its components over 1974–2013 with lower drawdowns. Those are his own tests; he chose the rule with that history in view. Faber (2007) reported similar drawdown reductions for a 10-month moving-average rule on asset classes. The common finding: trend rules on broad assets reduce the worst losses more reliably than they raise returns.

**Event study: what happened after the absolute check failed.**

*Method.* Each month-end, compare the 12-month total return of the home index with cash. Then record the index's return over the next month. US: S&P 500 total return against accumulated 3-month T-bill yields, 1981 to September 2026. India: Nifty 50 total return (an index ETF) against a liquid ETF, 2010 to August 2025 (the liquid fund's stored series stops updating after that). No costs.

| | US: check passes | US: check fails | India: check passes | India: check fails |
|---|---|---|---|---|
| Share of months | 77% | 23% | 76% | 24% |
| Next-month return, average | +1.11% | +0.58% | +0.54% | +2.53% |
| Next-month return, median | +1.43% | +0.84% | +0.43% | +2.34% |
| Months worse than −5% | 6% | 20% | 8% | 9% |

*What it shows.* In the US, months after a failed check were weaker on average and much more likely to bring a big loss. That is the protection the rule is built for. In India over 2010–2025 the opposite held: months after a failed check were the best on average. India's falls in this period were short, so the rule tended to exit near lows.

A longer Indian check, with an approximate total return built from the Sensex price index and a flat 6.5% cash rate, covers 1998–2010. There the check failed in mid-2000 and stayed off until late 2002, while the Sensex fell about 29%. It failed again in June 2008 and stayed off for a year. In that year the Sensex fell 47.4% peak to low before recovering. The rule's protection showed up in India too, but only in the long bear markets.

**Event study: Nifty against gold.** Each month-end from 2010 to August 2025, the asset with the higher 12-month return was compared with the other over the next month. The US check of S&P 500 against international stocks was similar.

| Check | Period | Leader beat the laggard | Average margin | t |
|---|---|---|---|---|
| Nifty against gold | 2010 – August 2025 | 48% of months | +0.05% | 0.1 |
| S&P 500 against international stocks | 2002–2026 | 53% of months | +0.18% | 1.3 |

Neither relative check predicted the next month reliably. What the gold switch delivered in 2020 and 2025 came from avoiding equity falls, not from a steady monthly edge.

**What is unknown.** Whether the next Indian bear market is long (where the rule helps) or short (where it hurts). Whether gold will keep its role as India's alternative asset. And whether a rule chosen with known history in view will work as well in the future.

## 9. Building and testing it yourself

**Data.**

- Total-return series for each asset: index ETFs or index funds that reinvest dividends, or a published total-return index.
- A cash series: T-bill yields accumulated daily (US), or a liquid fund's NAV history (India).
- At least 20 years of data, to include more than one bear market. India's ETF histories start around 2009, so a longer test needs a price index with an added dividend estimate. Say so in your results.

**Look-ahead traps.**

- Use month-end values only. The decision on the last day of the month is executed on the first day of the next.
- Fund NAVs in India are published in the evening. A switch decided on the month's last NAV is executed at the next day's NAV.

**Costs and tax (India, approximate).**

- Index ETFs: brokerage, STT of 0.001% on the sell side for equity ETFs, stamp duty, and the bid-ask spread.
- Index funds: no STT on purchase, an exit load if sold within a short period, and the fund's expense ratio.
- Gold ETFs and liquid funds: no STT. Their gains are taxed under the debt or "other asset" rules, which have changed several times; check the current rules.
- Equity held under 12 months: short-term gains at 20%; over 12 months, 12.5% above an annual exemption (rules from July 2024).

**What to test.**

- Lookbacks of 6, 9 and 12 months, and a blend of them.
- The safe asset: cash against bonds.
- A switch buffer of 0, 1 and 2 percentage points.
- Monthly against quarterly checks.

**What a good test reports.** Return, volatility and the worst drawdown for the rule and for each asset held alone. The number of switches, and the share that were whipsaws (re-entry at a higher price than the exit). The worst year relative to buy-and-hold. Results split into periods with and without a long bear market.

```
every month-end t:
    r = 12-month total return of each asset (value[t] / value[t-12 months] - 1)
    if r[home equity] > r[cash]:
        pick = the risky asset with the highest r
    elif india_version and r[gold] > r[cash]:
        pick = gold
    else:
        pick = safe asset
    if pick != current and (r[pick] - r[current] > buffer or current is not risky):
        switch to pick at t+1
```

## 10. Checklist

- [ ] All series are total return, from the same data source if possible
- [ ] The check uses month-end values; the trade happens on the next session
- [ ] Absolute check: home equity's 12-month return against cash
- [ ] Relative check: the strongest risky asset, with the buffer applied
- [ ] The safe asset is chosen for the likely risk (cash if inflation and rates are the danger)
- [ ] Tax impact of the switch is known before placing the order
- [ ] The switch, the numbers behind it and the cost are logged
- [ ] I accept that the next switch may be a whipsaw, and will follow it anyway
- [ ] The next month-end check date is in the calendar

## Further reading

- Gary Antonacci, *Dual Momentum Investing: An Innovative Strategy for Higher Returns with Lower Risk*, McGraw-Hill, 2014.
- Gary Antonacci, "Risk Premia Harvesting Through Dual Momentum", *Journal of Management & Entrepreneurship*, 2017 (working paper from 2012).
- Tobias Moskowitz, Yao Hua Ooi and Lasse Pedersen, "Time Series Momentum", *Journal of Financial Economics*, 2012.
- Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management*, 2007.
- Related guides: [cross-sectional momentum](learn-strat-xs-momentum.md), [sector rotation](learn-strat-sector-rotation.md), [the market's trend](learn-health-trend.md), [interest rates](learn-macro-rates.md), [commodities and gold](learn-macro-commodities.md).
