# Intraday momentum and trend days — when the morning predicts the afternoon

**In short**

- In the US index, the return from the previous close to the end of the first half-hour has helped predict the direction of the last half-hour (Gao, Han, Li and Zhou, 2018).
- The effect is strongest on volatile, high-volume and news days, which are also the days when a trend day is most likely.
- A trend day opens near one end of its range and closes near the other; only about one day in five looks like that, and most days are range days.
- Intraday trading is hard after costs: SEBI found that about 7 in 10 individual intraday traders in India's cash market lost money in 2022–23.
- If you trade intraday at all, trade few days, small size, liquid index futures or large stocks, and exit by the close on your own terms.

This guide belongs to the intraday group, with [opening-range breakouts](learn-strat-orb.md) and [VWAP strategies](learn-strat-vwap.md). Charts here use daily prices; intraday data is not shown. The intraday tables are illustrative: invented numbers that show the mechanics, not recorded trades.

## 1. The idea

### An example first

On 4 June 2024 India counted the votes of its general election. The Nifty 50 opened only 0.4% below the previous close, at what turned out to be the day's high. As the counts showed the ruling party short of a majority, the index fell through the day. At the low it was 8.2% below the open; it closed 5.6% below the open.

```series
title: Nifty 50 — the election-results day, 4 June 2024
from: 2024-05-01
to: 2024-07-15
line: india:^NSEI | Nifty 50
line: india:INDIAVIX | India VIX | right
mark: 2024-06-04 | Opened at the high, closed 5.6% lower
caption: On 4 June 2024 the Nifty opened at the day's high, fell as far as 8.2% below the open, and closed 5.6% below it. It had recovered the whole loss three sessions later.
```

The day had no big gap: the news arrived during the session, not overnight. The open was the high, and the close was in the lower third of a very wide range. This is a **trend day**: one side pushes all day, and the other side never gets control back.

On a day like this, the direction of the morning was the direction of the afternoon. The research in this guide asks whether that is true often enough to trade.

### The intraday momentum finding

Lei Gao, Yufeng Han, Sophia Zhengzi Li and Guofu Zhou studied the SPDR S&P 500 ETF (SPY) over 1993–2013. They split each day into half-hour periods. The first period's return was measured from the previous day's close to 10.00 am, so it includes the overnight gap. That first return helped predict the return of the last half-hour, 3.30 pm to 4.00 pm, in the same direction.

| Illustrative day | Previous close | Price at 10.00 am | First half-hour return | Signal for 3.30 pm |
|---|---|---|---|---|
| A | 500.0 | 503.5 | +0.7% | Buy at 3.30 pm, sell at the close |
| B | 500.0 | 497.0 | −0.6% | Sell short at 3.30 pm, buy back at the close |
| C | 500.0 | 500.4 | +0.08% | Too small; many versions skip it |

The predictability was stronger on more volatile days, on days with more trading volume, during recessions, and on days of major economic news. The effect is small per day: most of the day's movement is not predicted.

### Why it can work

Two explanations are offered in the research, and both may be true.

- **Late-informed or slow traders.** Some investors trade early on news; others react only later in the day, or must finish orders before the close. Their trading pushes in the same direction as the morning.
- **Hedging flows.** Banks that have sold options, and leveraged ETFs that must rebalance daily, often need to trade in the direction of the day's move near the close. Baltussen, Da, Lammers and Martens (2021) linked intraday momentum across many futures markets to this hedging demand.

### Who is on the other side

In the last half-hour, the other side is mostly traders and market makers who sell into the rally (or buy the fall) because they think the move has gone far enough. Large hedgers are not trying to make a profit on that trade; they are reducing their own risk. That makes them a steady, predictable source of orders, which is the kind of counterparty a small trader can stand beside.

## 2. When it works and when it doesn't

### Trend days and range days

| Type of day | Open | Close | What works |
|---|---|---|---|
| Trend day | Near one end of the day's range | Near the other end | Trading with the morning's direction; holding to the close |
| Range day | Anywhere | Back near the middle, often near the open | Fading moves to the edges; taking quick profits |
| Reversal day | Near one end, after a gap | Near the other end, against the gap | Neither, until the turn is clear |

How common are trend days? The table uses daily data from 2015 to 2025. A trend day is defined as one where the open was in the top or bottom fifth of the day's range and the close in the opposite fifth.

| Instrument | Trend days, share of all days |
|---|---|
| SPY (S&P 500 ETF) | 20.6% |
| QQQ (Nasdaq 100 ETF) | 22.5% |
| Nifty 50 | 23.6% |
| Nifty Bank | 21.1% |
| Liquid US stocks | 18.0% |
| Liquid Indian stocks | 17.5% |

About four days in five are not trend days. A strategy that assumes every day trends will lose on most days.

### Signs of a trend day, early

None of these is reliable on its own; together they raise the odds.

- **News**: a central-bank decision, an election result, major data (inflation, jobs), or company results for a stock.
- **The open is near an extreme**: by mid-morning, the price has not come back to the open.
- **The range expands**: the price breaks clearly out of the first half-hour's range and does not return to it (see [opening-range breakouts](learn-strat-orb.md)).
- **VWAP slopes steadily**, and the price stays on one side of it (see [VWAP strategies](learn-strat-vwap.md)).
- **Breadth is one-sided**: most stocks in the index move the same way during the session.
- **Volatility is high**: the VIX or India VIX is already elevated.

### Does the gap predict the day?

Many traders assume a gap up means a strong day. On daily data it does not: the overnight gap and the open-to-close return were essentially unrelated.

| Instrument, 2015–2025 | Correlation of the gap with the open-to-close return | Days with a gap of 1% or more | Of those, share where the close was beyond the open in the gap's direction |
|---|---|---|---|
| SPY | 0.02 | 253 | 54.5% |
| QQQ | −0.01 | 398 | 52.8% |
| Nifty 50 | −0.04 | 169 | 46.7% |
| Nifty Bank | −0.05 | 295 | 46.1% |

This does not contradict Gao and co-authors. Their signal is the gap plus the first half-hour, and it predicts only the last half-hour, not the whole day. The table shows why that distinction matters: the middle of the day can go either way.

### India and US notes

- **Sessions**: India's cash and equity futures markets trade 9.15 am to 3.30 pm IST; the last half-hour is 3.00 pm to 3.30 pm. The US session is 9.30 am to 4.00 pm Eastern time.
- **India's closing price**: NSE sets the official close of a stock as the volume-weighted average price of the last 30 minutes, not the last trade. A last-half-hour strategy must measure its exit at the price it actually trades, not the official close.
- **Auto square-off**: brokers close intraday cash positions (MIS) themselves near the close, usually 3.15–3.25 pm. A last-half-hour strategy in Indian stocks would have only a few minutes; index futures held as normal positions do not have this problem.
- **Margins**: since SEBI's peak-margin rules (phased in during 2020–21), brokers must collect margin upfront. Intraday leverage in cash stocks is limited to roughly five times for the most liquid stocks. Futures need the full exchange margin even intraday.
- **Tax**: in India, profits from intraday equity trading are treated as speculative business income and taxed at your slab rate. Futures and options are treated as non-speculative business income.
- **US**: four or more day trades in five business days in a margin account make you a "pattern day trader", which needs at least $25,000 of equity. FINRA has proposed changing this rule; check the current version.

## 3. The rules

Two strategies follow: the published index signal, and a trend-day continuation trade.

### Universe and filters

- **Strategy A (index timing)**: one liquid index instrument. In the US, SPY or the E-mini S&P 500 future; in India, the Nifty or Bank Nifty future (current month).
- **Strategy B (trend-day continuation)**: index futures, or stocks with average daily turnover of at least ₹100 crore or $100 million and a price of at least ₹100 or $10.

### Strategy A — first half-hour predicts last half-hour

**Setup.**
- r1 = price at the end of the first half-hour ÷ previous session's close − 1. In the US, measure at 10.00 am; in India, at 9.45 am.
- Trade only if |r1| (the size, ignoring sign) is at least 0.25%.
- Optional filter: trade only on high-volatility days, for example when the previous day's VIX or India VIX was above its 1-year median.

**Entry.**
- At the start of the last half-hour (3.30 pm in the US, 3.00 pm in India), buy if r1 is positive, sell short if negative.
- Use a market or marketable limit order; the trade is about timing, not price.

**Initial stop.** A protective stop at 0.5% from entry for an index. It is rarely hit in 30 minutes; it is there for a sudden shock.

**Exit.** At the close: a market-on-close order in the US; in India, a market order in the last minute before 3.30 pm.

### Strategy B — trend-day continuation

**Setup (checked at the end of the first 90 minutes).**
- The open is in the bottom 20% of the range so far (for a long) or the top 20% (for a short).
- The price is in the top 20% of the range so far (long) or the bottom 20% (short).
- The range so far is at least 0.75 times the 14-day ATR.
- The price has stayed on the trend side of session VWAP for the last 60 minutes.

**Entry.**
- Wait for a pullback towards VWAP, and buy (or sell) when the price resumes in the trend's direction: a 5-minute bar trades beyond the previous bar's high (long) or low (short).
- No new entries in the last 60 minutes.

**Initial stop.** Beyond VWAP by 0.25 ATR, or beyond the pullback's extreme, whichever is further from the entry.

**Exits.**
- Hold to the close: exit 10 minutes before the end of the session, by 3.15 pm in India.
- Invalidation: a 15-minute bar closes on the wrong side of VWAP.
- Optional trailing stop: the low (long) or high (short) of the last completed 30-minute bar.

### Position size

Risk 0.25–0.5% of equity per trade. Shares or lots = risk amount ÷ (entry − stop). In futures you cannot buy a fraction of a lot. If one lot risks more than your limit, the trade is too big for your account: skip it. See [position sizing](learn-risk-sizing.md).

### Managing the trade

- Take at most one Strategy A trade and two Strategy B trades per day.
- Stop trading for the day after a loss of 1% of equity.
- Do not hold an intraday trade overnight because it is losing. Exit as planned.
- Keep a record of every trade: signal, fill, exit, costs. Compare it with your test (see [the trade journal](learn-process-journal.md)).

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| A: first-period length | 30 min (15–60) | How much of the morning forms the signal | The published work uses 30 minutes. |
| A: minimum size of r1 | 0.25% (0–0.5%) | Ignores flat mornings | Higher = fewer, stronger signals. |
| A: volatility filter | VIX above its 1-year median | Trades only in livelier markets | The published effect is larger on volatile days. |
| A: entry time | Start of the last half-hour | Holding period | Earlier entries add noise from the midday. |
| A: protective stop | 0.5% (0.3–1%) | Shock protection | Rarely hit. |
| B: setup time | 90 min after the open (60–120) | How early a trend day is called | Earlier = more false trend days. |
| B: open and price position | Bottom and top 20% of the range | Trend-day test | — |
| B: range so far | 0.75 ATR (0.5–1.0) | Is the day already wide? | — |
| B: time on the trend side of VWAP | 60 min | Trend-day test | — |
| B: stop beyond VWAP | 0.25 ATR | Room for noise | — |
| B: no-entry window before close | 60 min | Late trades with no room | — |
| Exit time | 10 min before close; 3.15 pm IST for cash stocks | Square-off and overnight risk | — |
| Risk per trade | 0.25–0.5% of equity | Account volatility | — |
| Trades per day | 1 (A), 2 (B) | Over-trading | — |
| Daily loss limit | 1% of equity | Loss streaks | — |

## 5. Variations

- **Gao, Han, Li and Zhou (2018)**: also use the return of the second-to-last half-hour (3.00 pm to 3.30 pm) together with the first.
- **Baltussen, Da, Lammers and Martens (2021)**: study intraday momentum across many futures markets. They relate the strength of the effect to how much hedging dealers and leveraged funds must do on the day.
- **Noise boundaries**: a working paper by Carlo Zarattini, Andrew Aziz and Andrea Barbon (2024) on SPY trades a break of a band around the open, sized from recent intraday volatility. It is not peer-reviewed.
- **Market Profile day types**: James Dalton's *Mind Over Markets* classifies days as trend, normal, neutral and others, using the first hour's range (the "initial balance"). A trend day is one where the price extends far beyond the first hour's range in one direction.
- **Same-time-of-day patterns**: Heston, Korajczyk and Sadka (2010) found that a stock's return in a given half-hour tends to repeat at the same half-hour on following days. It is a different, cross-sectional effect, but shows that intraday timing patterns exist.

## 6. Worked examples

The daily open, high, low and close are real. What happened inside each day is not stored, so each example says what the daily bar proves and what it cannot show.

### Example 1 — Nifty 50, 4 June 2024 (India, a trend day without a gap)

Covered in section 1.

| | Value |
|---|---|
| Gap from the previous close | −0.4% |
| Open's position in the day's range | at the high |
| Low below the open | −8.2% |
| Close relative to the open | −5.6% |
| Close's position in the day's range | 32% up from the low |

The close was not in the bottom 20% of the range, because the index recovered from the low late in the day. So by the strict definition of section 2, this was not a trend day. That matters: the strongest down day in years still bounced 2.8% off its low, and a short held for the last part of the day may well have lost. The daily bar cannot tell when the low came.

### Example 2 — Adani Enterprises, 21 November 2024 (India, a trend day on news)

On 20 November 2024 (US time), US prosecutors announced charges against Gautam Adani, chairman of the Adani group. Indian markets were closed that day for state elections in Maharashtra. On 21 November Adani Enterprises opened 10% lower.

```series
title: Adani Enterprises — the indictment news of November 2024
from: 2024-10-15
to: 2024-12-31
line: india:ADANIENT.NS | Adani Enterprises
line: india:ADANIENT.NS@vol | Volume | pane2 bars
mark: 2024-11-21 | Opened 10% lower at the high, closed 14% below the open
caption: On 21 November 2024 Adani Enterprises opened 10% below the previous close, at the day's high, and closed 14% below the open, in the bottom 7% of the day's range.
```

| | Value |
|---|---|
| Gap from the previous close | −10.0% |
| Open's position in the day's range | at the high |
| Close relative to the open | −14.0% |
| Close's position in the day's range | bottom 7% |

This was a textbook trend day: open at the high, close near the low, with news strong enough to keep sellers coming all day. Strategy B's short setup would have been met at mid-morning, as long as the price was near its low by then. In India's cash market a short like this is allowed only intraday, and must be closed the same day. The daily bar cannot show where the price was at mid-morning, so the size of any gain is not known.

### Example 3 — SPY, 10 November 2022 (US, a trend day up)

On 10 November 2022 US consumer price inflation for October came in lower than expected. SPY opened 3.7% higher and closed 5.5% above the previous close.

```series
title: SPY — the inflation-report rally of 10 November 2022
from: 2022-10-01
to: 2022-12-15
line: us:SPY | SPY
line: us:VIX | VIX | right
mark: 2022-11-10 | Opened 3.7% up, closed at 96% of the range
caption: SPY opened 3.7% above the previous close on 10 November 2022 and closed 5.5% above it, at 96% of the day's range.
```

The first half-hour return, which includes the gap, was almost certainly strongly positive. Strategy A's signal was therefore a buy for the last half-hour. The close was in the top 4% of the day's range, so the price finished at or very near the day's high. That is consistent with a rising last half-hour, but the daily bar cannot prove it.

### Example 4 — SPY, 5 August 2024 (US, a panic open that did not trend)

SPY opened 4.0% lower on 5 August 2024, after weak US jobs data and a sharp fall in Japanese shares.

```series
title: SPY — a panic gap that reversed, August 2024
from: 2024-07-01
to: 2024-09-06
line: us:SPY | SPY
line: us:VIX | VIX | right
mark: 2024-08-05 | Gap down 4.0%, closed 1.1% above the open
caption: SPY opened 4.0% lower on 5 August 2024; its low was only 0.3% below the open, and it closed 1.1% above the open, in the middle of the day's range.
```

The first half-hour return was strongly negative, because it includes the gap. So Strategy A's signal was a short for the last half-hour. But the day itself was a recovery: the low came near the open, and the close was 1.4% above it. Strategy B's short setup was never met, because the price did not stay near the low. Whether Strategy A's short lost depends on the last half-hour alone, which the daily bar cannot show.

The lesson: a big gap is not a trend day. Panic opens often mark the day's extreme.

## 7. Common mistakes

- **Calling every big open a trend day.** Gap days have wider ranges but no reliable direction from the open (see the table in section 2).
- **Trading every day.** Most days are range days. Fewer, better trades cost less.
- **Using too much leverage.** Intraday margin lets positions grow far beyond your capital. A normal move against you then becomes a large loss.
- **Letting the broker close your trades.** Automatic square-off comes at a market price you did not choose, often with a fee.
- **Measuring the close wrongly in India.** The official close is an average of the last 30 minutes. Test with the prices you can actually trade at.
- **Assuming a published effect still works.** Effects in papers often weaken after publication, and costs in your market may be higher than in the paper.
- **Ignoring costs.** Strategy A holds for 30 minutes. An index rarely moves much in 30 minutes, so the cost of each round trip is large relative to the expected gain.

## 8. What the evidence says

### Published work

- **Gao, Han, Li and Zhou (2018, *Journal of Financial Economics*)**: the first half-hour return of SPY predicts the last half-hour return, 1993–2013. The effect was stronger on volatile days, high-volume days, news days and in recessions. It is statistically clear but economically small per trade.
- **Baltussen, Da, Lammers and Martens (2021, *Journal of Financial Economics*)**: intraday momentum across many futures markets, linked to hedging by option dealers and other hedgers.
- **Heston, Korajczyk and Sadka (2010, *Journal of Finance*)**: stocks' returns at a given half-hour repeat at the same half-hour on later days.
- **Day traders' results**:
  - Barber, Lee, Liu and Odean studied every day trade on the Taiwan Stock Exchange over many years. They found that very few day traders earned predictable profits after fees; the great majority lost.
  - Chague, De-Losso and Giovannetti studied Brazilians who day-traded index futures for 300 days or more; the great majority lost money.
  - SEBI (July 2024) studied individual intraday traders in India's equity cash segment: about 7 in 10 made a net loss in 2022–23, and the loss rate was higher among those who traded most often.
  - SEBI (September 2024) found that 93% of individual traders in equity futures and options lost money over the three years to March 2024.

The papers on intraday momentum show that a pattern exists in index returns. The studies of real traders show that most people who trade intraday lose. Both can be true: an edge in the data is small, and real traders give it up through costs, over-trading and leverage.

### Event study: day types and the gap, 2015–2025

**Method.**

- Data: daily open, high, low and close, 2015 to 2025, for SPY, QQQ, the Nifty 50 and Nifty Bank indices, and for liquid US and Indian stocks.
- A trend day: open in the top or bottom 20% of the day's range and close in the opposite 20%.
- The correlation is between the gap (open ÷ previous close − 1) and the open-to-close return.
- Liquid stocks: prior 20-day average turnover at least $50 million or ₹50 crore. Price at least $10 or ₹100.

**Sample.** The data behind each result:

| Universe | Size |
|---|---|
| Each index | about 2,700–2,800 days |
| US stocks | about 2.2 million stock-days |
| Indian stocks | about 466,000 stock-days |

| Instrument | Median day's range, % of previous close | Median size of the open-to-close move |
|---|---|---|
| SPY | 0.89% | 0.39% |
| QQQ | 1.21% | 0.54% |
| Nifty 50 | 0.92% | 0.42% |
| Nifty Bank | 1.25% | 0.54% |

The trend-day shares and the gap correlations are in section 2.

**What it shows.** Trend days are about one day in five, in both markets and in every year tested. The overnight gap tells you almost nothing about the rest of the day. A typical index day moves well under half a percent from open to close, which is the whole pool from which costs must be paid.

**Caveats.** Daily bars cannot test a half-hour signal; this study describes the days, not the strategy. Index opens are computed by the data provider and may differ slightly from the first traded price. The stock lists are today's members (survivorship bias).

### What is unknown

Whether the first-half-hour signal works in Indian index futures after costs is not established in published research that we can point to. The rule for India's official closing price also changes what "the last half-hour" means there. Test it yourself before you trust it.

## 9. Building and testing it yourself

### Data

- Intraday bars for the instrument you trade: 1-minute or 5-minute, with volume. For futures, join the contracts at each roll date and record which contract was traded.
- The previous session's close, from the same source, for r1.
- A calendar of news days (central-bank meetings, inflation and jobs data, results dates), known in advance.

### Look-ahead traps

- r1 uses prices up to the end of the first half-hour only.
- A "trend day" label must use only the range so far, not the day's full range.
- A "volatile day" filter must use the previous day's volatility, or the morning's.
- Do not use the official closing price in India as an exit price unless you could have traded at it.

### Costs and slippage

Approximate charges for an intraday round trip in India:

| Cost | Cash stocks (intraday) | Index futures |
|---|---|---|
| Brokerage (discount broker) | ₹20 per order or 0.03%, whichever is lower | ₹20 per order |
| STT | 0.025% on the sell side | 0.02% on the sell side (since October 2024) |
| Exchange transaction charges | about 0.003% each side | about 0.002% each side |
| Stamp duty | 0.003% on the buy side | 0.002% on the buy side |
| GST | 18% on brokerage and exchange charges | 18% on brokerage and exchange charges |

Add slippage of at least one tick each side for index futures, more for stocks. Compare the total with the median open-to-close move in section 8: costs take a real share of it.

### What to test, and how

- Test Strategy A over the longest history you have, then split it by year, by volatility level and by news versus non-news days.
- Check whether the result survives a later entry (one bar late) and a worse fill (one more tick of slippage).
- For Strategy B, count how often the trend-day test at mid-morning was right by the close. If it is barely better than the base rate of about one in five, the setup adds nothing.
- Report trades, win rate, average win and loss, expectancy after costs, maximum drawdown and results by year. See [backtesting](learn-test-backtesting.md) and [reading a backtest](learn-test-reading.md).

### Core logic

```
# Strategy A
for each session:
    r1 = price_at(open + FIRST_MIN) / prev_close - 1
    if abs(r1) < R1_MIN: continue
    if VOL_FILTER and vix_yesterday < vix_median_252d: continue
    side = +1 if r1 > 0 else -1
    entry = price_at(close_time - 30 min) + side * slippage
    exit  = last tradable price before the close - side * slippage
    stop: if price moves STOP_PCT against side before the close, exit there
    pnl = side * (exit - entry) / entry - round_trip_costs

# Strategy B (long side)
at open + SETUP_MIN:
    rng = high_so_far - low_so_far
    if pos(open) <= 0.2 and pos(last) >= 0.8 and rng >= RANGE_ATR * atr14_yesterday \
       and above_vwap_for(60 min):
        arm: buy on a resumption bar after a pullback, until close - 60 min
```

## 10. Checklist

- [ ] Is today a news day or a high-volatility day? If not, is there a reason to trade at all?
- [ ] For Strategy A: is the first half-hour move large enough to pass the filter?
- [ ] For Strategy B: do the open, the price, the range and VWAP all agree it is a trend day?
- [ ] Is the size set from the stop, and within the margin your broker allows?
- [ ] Will I exit before the broker's square-off, at a price I choose?
- [ ] Does the expected gain clearly exceed the round-trip costs?
- [ ] Have I already hit today's loss limit or trade limit?

## Further reading

- Lei Gao, Yufeng Han, Sophia Zhengzi Li and Guofu Zhou, "Market Intraday Momentum", *Journal of Financial Economics* (2018).
- Guido Baltussen, Zhi Da, Sten Lammers and Martin Martens, "Hedging Demand and Market Intraday Momentum", *Journal of Financial Economics* (2021).
- Steven L. Heston, Robert A. Korajczyk and Ronnie Sadka, "Intraday Patterns in the Cross-section of Stock Returns", *Journal of Finance* (2010).
- Brad M. Barber, Yi-Tsung Lee, Yu-Jane Liu and Terrance Odean, "The Cross-Section of Speculator Skill: Evidence from Day Trading", *Journal of Financial Markets* (2014).
- Fernando Chague, Rodrigo De-Losso and Bruno Giovannetti, "Day Trading for a Living?" (working paper, 2019).
- James F. Dalton, Eric T. Jones and Robert B. Dahlquist, *Mind Over Markets* (1990; updated edition 2013).
- SEBI, study of profit and loss of individual intraday traders in the equity cash segment (July 2024).
- SEBI, study of profit and loss of individual traders in the equity derivatives segment (September 2024).
