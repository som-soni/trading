# Index changes and corporate news — trading the event calendar

**In short**
- When a stock joins a big index, index funds must buy it on one known day. That forced buying is the trade.
- The gain used to be large and reliable. It has shrunk a great deal as traders learned to front-run it.
- The tradable window today is mostly between the announcement and the day the change takes effect; after that, results are mixed.
- Splits, bonus issues, buybacks and block deals are events too. Each has a known mechanism, but none is a free lunch on its own.
- Treat every event trade as a small, planned bet with an exit date fixed in advance.

## 1. The idea

Start with one case. On 16 November 2020, after the US market closed, S&P Dow Jones Indices announced that Tesla would join the S&P 500. The change took effect before the open on 21 December 2020. That meant every fund tracking the index had to own Tesla by the close of Friday 18 December.

```series
title: Tesla, from the S&P 500 announcement to the inclusion (split-adjusted)
from: 2020-10-01
to: 2021-03-31
line: us:TSLA | Tesla | log
line: us:TSLA@vol | Volume | pane2 bars
mark: 2020-11-16 | Inclusion announced (after the close)
mark: 2020-12-18 | Last close before inclusion
caption: Tesla rose about 70% between the announcement close and the inclusion close. Volume on 18 December was more than five times its recent average. Over the next 60 sessions the stock fell while the S&P 500 rose.
```

Between those two closes Tesla rose about 70%, while the S&P 500 rose about 2%. On the last day, volume was 5.5 times its 50-day average. That was the index funds buying at the closing price, as their rules require. Sixty sessions later the stock was 6% below that close, while the index was up 5.6%.

This is the whole idea of an **index event trade**. A rule-bound buyer must trade a known quantity on a known day. It does not care about price. Other traders buy ahead of it and sell to it at the close. Their profit is a fee for supplying shares to a buyer that has no choice.

Who is on the other side? On the way up, it is the existing holders who sell too early. At the inclusion close, it is the index funds themselves. They accept a worse price because tracking the index exactly matters more to them than a few percent on one stock.

The same logic covers other corporate events. A **stock split** or a **bonus issue** (India's term for free extra shares to existing holders) changes the share count, not the business. A **buyback** is the company itself buying shares. A **block deal** is one large holder selling to another in a single trade.

Each of these creates a known buyer or seller. The question for a trader is always the same: who must trade, when, and has the price already moved to meet them?

## 2. When it works and when it doesn't

**It works best when the forced flow is large relative to normal trading.** Passive funds own a large share of S&P 500 stocks. In India, passive money tracking the Nifty 50 and Sensex has grown fast since 2018. A stock entering the Nifty 50 from outside it can see buying worth several days of its normal turnover.

**It works least when everyone expects the change.** For the Nifty, the rules are public and brokers publish likely additions weeks ahead. Much of the move then happens before the announcement. For the S&P 500, a committee decides, so announcements still surprise. That is why US announcement-day jumps are larger than most Indian ones.

**The market around the event matters more than the event.** Trent and Bharat Electronics joined the Nifty 50 at the end of September 2024. The Indian market then fell for months. The inclusion did not protect either stock (see section 6).

**India and the US differ in mechanics:**

| | US (S&P 500) | India (Nifty 50, Sensex) |
|---|---|---|
| Who decides | A committee, with published rules plus judgement | Rule-based ranking by free-float market cap, reviewed by a committee |
| Regular reviews | Quarterly, effective after the third Friday of Mar, Jun, Sep, Dec | Nifty: twice a year, effective after the last trading day of Mar and Sep. Sensex: Jun and Dec |
| Notice | Usually about two weeks; less for unscheduled changes | About four weeks |
| Surprise at announcement | Often high | Usually low; candidates are widely forecast |
| Other big rebalances | Russell (June), Nasdaq-100 (December) | MSCI and FTSE reviews, which move foreign money (FII flows) |
| Swing shorting | Possible in the cash market | Only through futures and options; cash shorts must close the same day |

**Free-float market cap** means the market value of the shares that actually trade, leaving out promoter and government holdings. In India a stock must also be in the futures and options (F&O) segment to join the Nifty 50.

## 3. The rules

These rules cover the core trade: buying an index addition between announcement and inclusion. Section 5 covers the other events.

### Universe and filters

- The stock is named as an addition to a major index (S&P 500, Nasdaq-100, Nifty 50, Sensex, Nifty Next 50) in an official announcement.
- The expected passive buying is large: the estimated index-fund demand is at least `min demand` days of the stock's average daily traded value. Index providers and brokers publish estimates; you can also take the index's tracked assets times the stock's expected weight.
- India: the stock is not in a price band of 5% or less. A tight **circuit limit** (the exchange's daily price cap) can stop you exiting.
- No earnings report falls between entry and the planned exit, unless you accept that risk on purpose.

### Setup

- The announcement is public, and the effective date is known.
- The stock has not already risen more than `max pre-run` in the 20 sessions before the announcement. A big pre-run means the trade has been taken already.
- The broad market is in an uptrend: the index closes above its 50-day average. See [Trend health](learn-health-trend.md).

### Entry

- Buy at the open of the first session after the announcement, with a limit order no more than `max gap` above the prior close.
- If the stock gaps up by more than that, skip it or wait for the first pullback that holds above the announcement-day low.

### Initial stop

- A close below the low of the first session after the announcement, or `stop ATR` × ATR below entry, whichever is closer.
- The stop is wide on purpose. Event trades are short, so the exit date does most of the risk control.

### Exits

- **Planned exit:** sell at the close of the last session before the change takes effect. Use a market-on-close order in the US. In India the official close is the average price of the last half hour; you can also sell at that price in the post-close session.
- **Early exit:** sell if the stock gains more than `early take` before the last day. Many of the late buyers will be selling into the same close.
- **Invalidation:** sell if the index provider changes or delays the addition.
- Do not hold past the inclusion close by default. Holding longer is a separate trade with its own reason.

### Position size

- Risk `risk %` of the account per trade, measured from entry to stop.
- Cap the position at `max position` of the account. Event trades bunch together at review dates, so several may share one exit day.
- See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Watch for news that would dominate the index flow: results, guidance, a block sale by a large holder.
- Raise the stop to break-even once the gain reaches 1R. **1R** is the distance from entry to the initial stop.
- On the last day, do not try to beat the close. The closing volume is there so that you can exit.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| `min demand` | 2–10 days of turnover | Size of forced buying versus normal trading | Higher means fewer, cleaner trades |
| `max pre-run` | 15–30% in 20 sessions | Skips stocks already bid up in anticipation | Matters most in India, where additions are forecast |
| `max gap` | 3–8% | How far above the prior close you will pay | US announcement gaps are often larger than this |
| `stop ATR` | 1.5–2.5 × ATR(14) | Distance to the initial stop | Too tight gets hit by normal event-week swings |
| `early take` | 10–25% | Early profit-take before the last day | Optional; test with and without |
| `risk %` | 0.25–0.75% | Account risk per trade | Keep small: outcomes are lumpy |
| `max position` | 5–10% | Cap on one position | Several events often share a date |
| Market filter | Index above its 50-day average | Avoids fighting a falling market | Cheap to test |

## 5. Variations

**Front-running the announcement (anticipation).** Rank stocks by the index's own rules and buy the most likely additions weeks before the review. For the Nifty this is common practice among Indian brokers. The risk is that the stock is not chosen. Your exit is then a loss on a stock bought for one reason only.

**Fading the inclusion.** After the inclusion close, the forced buyer is gone. Harris and Gurel (1986) found that much of the early price gain reversed within weeks. Lynch and Mendenhall (1997) found a run-up to the effective date and a partial reversal after it.

A fade sells or shorts at the inclusion close. In India a swing short needs futures, so only F&O stocks qualify. The 2024 Palantir case in section 6 shows why this is risky: a stock in a strong trend can keep rising.

**Deletions.** A stock leaving an index is sold by the same funds. Chen, Noronha and Singal (2004) found the effect asymmetric: additions kept part of their gain, while deletions tended to recover. Buying a deleted stock after the effective date is the mirror trade. It needs a liquid stock and a strong stomach.

**Stock splits and bonus issues.** A 2-for-1 split doubles the share count and halves the price. In India a 1:1 bonus issue does the same. Nothing about the business changes. Ikenberry, Rankine and Stice (1996) still found that US stocks drifted higher for a year after splits.

The usual reading is that managers split when they expect good times. Treat a split as a mild positive signal inside a trend strategy, not as a trade on its own. The record date and the ex-date are fixed in advance, and Indian bonus issues often draw retail buying before the ex-date.

**Buybacks.** In the US, most buybacks are made in the open market over months. Ikenberry, Lakonishok and Vermaelen (1995) found that stocks drifted higher for years after a buyback announcement, mostly in cheap stocks. Later work, such as Fu and Huang (2016), found that this drift largely disappeared after the early 2000s.

**Buyback tender offers in India.** Here the company offers to buy a fixed number of shares at a fixed price, usually above the market. A small shareholder (holding up to ₹2 lakh of the stock on the record date) gets a reserved part of the offer. The trade is to buy before the record date and tender.

The catch is the **acceptance ratio**: only part of your shares may be bought back, and the rest fall back to the market price. Since 1 October 2024, buyback proceeds are taxed as a dividend in the holder's hands. That has made the trade much less attractive for most people.

**Block and bulk deals in India.** A **block deal** is a single large trade done in a separate window, at a price close to the market price, with a minimum size set by SEBI. A **bulk deal** is any trade of more than 0.5% of a company's shares, disclosed by the exchange the same day.

A promoter or private-equity fund selling a big stake usually does it at a discount, and the stock often drops on the day. Practitioners watch what happens next. If the stock holds above the block price over the following sessions, the supply has been absorbed. This is a heuristic, not a documented edge.

## 6. Worked examples

All prices are split-adjusted daily closes.

### Example 1 — Tesla, S&P 500, 2020 (the classic, then a reversal)

| Step | Date | What happened |
|---|---|---|
| Announcement | 16 Nov 2020, after the close | Close that day: 136.0 |
| Entry under the rules | 17 Nov 2020 | Opened 12.8% higher, above the gap limit; wait for a pullback |
| Inclusion close | 18 Dec 2020 | Close 231.7, volume 5.5 times average |
| 60 sessions later | March 2021 | 6.0% below the inclusion close; S&P 500 up 5.6% |

From close to close, the announcement-to-inclusion window gave about 70%. The gap filter kept you out on the first morning. Even a buyer at the 17 November close of 147.20 made about 57% by the inclusion close. The stock then underperformed the index over the following three months. Selling at the inclusion close, as the rules say, was the right exit.

### Example 2 — Palantir, S&P 500, 2024 (why fading is dangerous)

```series
title: Palantir around its S&P 500 inclusion, 2024
from: 2024-08-01
to: 2024-12-31
line: us:PLTR | Palantir | log
line: us:SPX | S&P 500 | right
mark: 2024-09-06 | Announced
mark: 2024-09-20 | Inclusion close
caption: Palantir rose about 23% into the inclusion close. It did not reverse; it roughly doubled over the next 60 sessions.
```

Palantir closed at 30.33 on 6 September 2024, the day of the announcement. It closed at 37.20 on 20 September, the last session before inclusion. The rules would have taken that window and sold. A trader fading the inclusion would have been run over: 60 sessions later the stock was up about 104% from the inclusion close. The fade works on average in older studies, but a single fade in a strong trend can be a large loss.

### Example 3 — Trent and Bharat Electronics, Nifty 50, September 2024 (India; the market wins)

```series
title: Trent around its Nifty 50 inclusion, 2024
from: 2024-07-01
to: 2025-01-31
line: india:TRENT.NS | Trent | log
line: india:NIFTY500 | Nifty 500 | right
mark: 2024-09-27 | Last close before inclusion
caption: Trent rose into the end of September, then fell with the Indian market from October.
```

Trent and Bharat Electronics replaced two stocks in the Nifty 50 from 30 September 2024. The change was announced in late August. On 27 September, the last session before the change, both stocks traded huge volume. Trent traded 12 times its 50-day average volume, and Bharat Electronics 8.4 times.

| Stock | Last 20 sessions before inclusion | Next 20 sessions | Nifty 500, next 20 sessions |
|---|---|---|---|
| Trent | +9.4% | −6.7% | −7.5% |
| Bharat Electronics | −2.0% | −8.0% | −7.5% |

Trent's pre-inclusion run was real but modest. Bharat Electronics fell into its own inclusion. Both then fell with the market. This is the typical Indian pattern: the change was forecast for weeks, so there was little surprise left. The lesson: in India, the announcement is rarely the edge, and the market filter matters.

### Example 4 — Eternal (formerly Zomato) and Jio Financial, Nifty 50, March 2025 (India; a weak run-in, then strength)

Both joined the Nifty 50 from 28 March 2025, after a late-February announcement. Both fell in the 20 sessions before inclusion, while the Nifty 500 rose. Both then beat the index.

| Stock | Last 20 sessions before inclusion | Next 20 sessions | Next 60 sessions | Nifty 500, next 20 / 60 |
|---|---|---|---|---|
| Eternal | −8.6% | +12.7% | +28.6% | +2.9% / +9.9% |
| Jio Financial | −0.2% | +15.3% | +38.4% | +2.9% / +9.9% |

The announcement-to-inclusion trade lost money here. The stocks were in downtrends when the window opened, and the market filter was negative in early March 2025. The rules would have skipped both. The strength afterwards came with a market recovery, not from the index event.

### Example 5 — CrowdStrike, S&P 500, 2024 (event risk you cannot plan for)

CrowdStrike joined the S&P 500 from 24 June 2024, announced on 7 June. It rose 9.0% from the announcement close to the inclusion close, against 2.2% for the index.

Four weeks later, on 19 July 2024, a faulty update from the company crashed Windows computers worldwide. The stock fell 11% that day. Over the 20 sessions after inclusion it fell 30.7%. Selling at the inclusion close avoided all of it. Holding on "because it is now in the index" did not help.

## 7. Common mistakes

- **Buying on the effective day.** By then the forced buyer has bought. You are buying from the people who front-ran it.
- **Assuming inclusion means quality.** An index adds large companies. It does not promise that the stock will rise.
- **Ignoring the pre-run.** In India especially, likely additions are bid up before the announcement. The rest of the move may be small.
- **Holding through results.** An earnings report inside the window swamps the index effect.
- **Treating a split or bonus as good news.** The share count changed; the business did not.
- **Tendering in a buyback without checking the acceptance ratio and tax.** The bought-back part may be small, and the rest is worth the market price.
- **Chasing a block-deal drop.** A large holder may have more to sell. Wait for the stock to hold above the block price.

## 8. What the evidence says

**The index effect was real and large.** Shleifer (1986) found that stocks added to the S&P 500 rose by about 3% on the announcement. He read this as evidence that demand curves for stocks slope down. Harris and Gurel (1986) found that much of the gain was temporary. After 1989, S&P announced changes several days before they took effect. Lynch and Mendenhall (1997) showed that this created a run-up to the effective date and a partial fall after it.

**It has largely disappeared in the US.** Greenwood and Sammon (2022) studied the average abnormal return on S&P 500 additions. They document that it fell from several percent in the 1990s to under 1% in the 2010s. Their explanations include better liquidity, more traders ready to supply shares, and more predictable additions. Patel and Welch (2017) report that the long-run price effect has faded too. Petajisto (2011) estimated the cost this effect imposed on index funds while it lasted.

**Our own small check shows the same mix.** The table below covers well-known additions from 2020 to 2025, measured from stored daily closes. It is a handful of cases, not a study.

| Stock | Index | Announcement to inclusion close | Same window, benchmark | Inclusion close to +60 sessions | Benchmark, +60 |
|---|---|---|---|---|---|
| Tesla | S&P 500, Dec 2020 | +70.3% | +2.3% | −6.0% | +5.6% |
| Uber | S&P 500, Dec 2023 | +7.9% | +2.7% | +25.5% | +9.1% |
| Super Micro | S&P 500, Mar 2024 | +18.0% | −0.4% | −28.2% | +5.0% |
| Dell | S&P 500, Mar 2024 | −14.1% | −0.4% | +23.0% | +5.0% |
| CrowdStrike | S&P 500, Jun 2024 | +9.0% | +2.2% | −29.4% | +3.1% |
| KKR | S&P 500, Jun 2024 | +11.1% | +2.2% | +17.6% | +3.1% |
| Palantir | S&P 500, Sep 2024 | +22.7% | +5.4% | +103.6% | +6.5% |
| Coinbase | S&P 500, May 2025 | +28.6% | +2.0% | +22.7% | +8.5% |

Method: the announcement window runs from the close on the announcement day to the last close before the change took effect. The benchmark is the S&P 500 price index. Each inclusion date was confirmed by a volume spike on the last session before the change.

Seven of eight additions beat the index in the announcement window. After inclusion, outcomes scatter widely in both directions. With eight cases, this shows the shape of the effect, not its size.

**India has less clean evidence in English-language journals.** Nifty changes are forecast, so the announcement carries less news. The effect, where it exists, should show up before the announcement. Treat any claimed edge in Indian index trades as something to test yourself.

**Splits and buybacks: early drift, later fading.** The split drift (Ikenberry, Rankine and Stice, 1996) and the buyback drift (Ikenberry, Lakonishok and Vermaelen, 1995) are well documented for their samples. Later studies find them weaker after the early 2000s. No study we know of supports block-deal trading as a rule-based edge.

## 9. Building and testing it yourself

**Data you need:**
- A dated list of index changes: announcement date, effective date, additions and deletions. S&P and NSE Indices publish press releases; build the list from them. Price data alone cannot tell you the dates.
- Daily prices with volume, adjusted for splits and bonuses, for every stock that was ever added or deleted, including those later delisted.
- For India: the semi-annual review announcements, and F&O membership on each date.

**Look-ahead traps:**
- The announcement time. US changes are announced after the close. Your first possible trade is the next open, not the announcement-day close.
- The index's own price data for the stock. Do not use a list of current index members to find past additions.
- Corporate actions. A bonus issue on an unadjusted price series looks like a 50% crash.

**Survivorship.** Today's index members are the winners. Stocks that were added and later dropped or delisted must stay in the sample.

**Costs (approximate).** In the US, commissions are near zero. The real cost is the spread and the slippage at a crowded close. In India, a delivery trade pays brokerage (often zero to ₹20 per order), STT of 0.1% on each side, stamp duty of 0.015% on the buy, and exchange and GST charges. A round trip comes to roughly 0.25–0.35% before slippage. On a trade that aims for a few percent, that matters.

**What to test:**
- Entry at the next open after announcement against entry after the first pullback.
- Exit at the inclusion close against exits 5 and 20 sessions later.
- The pre-run filter and the market filter, one at a time.
- Report results by year. The effect has changed over time, so the average across all years can mislead.

```
for each addition event e (announcement date A, effective date E):
    if pre_run(stock, 20 sessions before A) > MAX_PRE_RUN: skip
    if index_close(A) < sma50(index, A): skip
    entry = open(next session after A)
    if entry > close(A) * (1 + MAX_GAP_CHASE): skip
    stop  = min(low(next session after A), entry - STOP_ATR * atr14(A))
    walk sessions from entry to the last session before E:
        if close < stop: exit at next open; break
        if close >= entry * (1 + TAKE_EARLY): exit at close; break
    else: exit at close of the last session before E
    record return, return of index over same dates, year, market
```

**A good test reports:** the number of events per year, the average and median excess return over the index, the spread of outcomes, and how much each filter changes the result. With few events, one Tesla can make a whole decade look good. Look at the median as well as the mean.

## 10. Checklist

- [ ] The change is officially announced, and I know the effective date.
- [ ] Expected passive buying is large compared with normal turnover.
- [ ] The stock has not already run up more than my pre-run limit.
- [ ] The broad market is above its 50-day average.
- [ ] No results or other scheduled news fall inside the holding window.
- [ ] India: the stock is liquid and not in a tight price band.
- [ ] Entry, stop and the planned exit date are written down before I buy.
- [ ] I will sell at the last close before the change, unless I have a separate reason to hold.

## Further reading

- Andrei Shleifer, "Do Demand Curves for Stocks Slope Down?", *Journal of Finance*, 1986.
- Lawrence Harris and Eitan Gurel, "Price and Volume Effects Associated with Changes in the S&P 500 List: New Evidence for the Existence of Price Pressures", *Journal of Finance*, 1986.
- Anthony Lynch and Richard Mendenhall, "New Evidence on Stock Price Effects Associated with Changes in the S&P 500 Index", *Journal of Business*, 1997.
- Honghui Chen, Gregory Noronha and Vijay Singal, "The Price Response to S&P 500 Index Additions and Deletions: Evidence of Asymmetry and a New Explanation", *Journal of Finance*, 2004.
- Antti Petajisto, "The Index Premium and Its Hidden Cost for Index Funds", *Journal of Empirical Finance*, 2011.
- Robin Greenwood and Marco Sammon, "The Disappearing Index Effect", NBER Working Paper, 2022.
- David Ikenberry, Josef Lakonishok and Theo Vermaelen, "Market Underreaction to Open Market Share Repurchases", *Journal of Financial Economics*, 1995.
- David Ikenberry, Graeme Rankine and Earl Stice, "What Do Stock Splits Really Signal?", *Journal of Financial and Quantitative Analysis*, 1996.
- Nimesh Patel and Ivo Welch, "Extended Stock Returns in Response to S&P 500 Index Changes", *Review of Asset Pricing Studies*, 2017.
- Fangjian Fu and Sheng Huang, "The Persistence of Long-Run Abnormal Returns Following Stock Repurchases and Offerings", *Management Science*, 2016.
- Related guides: [Trend health](learn-health-trend.md), [Position sizing](learn-risk-sizing.md), [Stops and exits](learn-risk-stops-exits.md), [Earnings](learn-fund-earnings.md).
