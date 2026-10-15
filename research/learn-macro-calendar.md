# The macro event calendar — the dates that move whole markets

Learning material on the scheduled events that move whole markets in the US
and India: central banks, inflation and jobs data, budgets, elections,
earnings seasons, index rebalances and option expiries. It covers why they move prices, what
volatility does around them, and the rules a swing trader uses to avoid being caught on the
wrong side of a gap. Companions: [the rates guide](learn-macro-rates.md) and
[the inflation guide](learn-macro-inflation.md).

**Where this shows in the app.** The app tracks each stock's own earnings date:

- the **Chart** marks past results with an "E";
- its **News & events** panel lists what is coming;
- the setups table on **Strategies** has an *Earnings in (d)* column (days until results);
- **Markets → Post-market** lists earnings in the next 10
  days among watched and screened stocks.

Market-wide volatility is part of the app's market-regime check
(`scripts/swing_screener/core/regime.py`). When the VIX is above
25 (US) or India VIX is above 20, live position sizing halves the risk per
trade, from 1% to 0.5% of the account. Macro release dates themselves are not in
the app. Use the official calendars listed in Further reading.

---

## 1. Why scheduled events move markets

Markets react to **the news compared with what was expected**. Prices already reflect
the consensus (the average forecast of economists). So a CPI of 3.0% is good for stocks against a 3.3% forecast, and
bad for them against a 2.7% forecast.

- **The surprise is what matters.** The size of a move depends on two things: how far the
  number is from the consensus, and how much the market cares about that
  number *right now*. In 2022 CPI was the only thing that mattered; in other years it barely
  registers.
- **"Buy the rumour, sell the news."** When an outcome is widely expected
  and traders have already bought for it, the event itself can trigger the opposite move. Everyone
  who wanted to own it already does, so there is no one left to buy.
- **Expected volatility shows up in prices beforehand.** Options get more expensive before a known
  event and cheaper the moment it passes, whichever way the market moves. This drop is called the "volatility crush".

## 2. The United States

- **FOMC meetings** (the Fed committee that sets rates) — eight scheduled a year. The statement comes at 2:00 pm
  ET, and the chair's press conference at 2:30. The **minutes** (a written record of the discussion) follow three
  weeks later. At four meetings (March, June, September, December) the Fed
  also publishes its **Summary of Economic Projections**. This includes the
  **dot plot**, a chart of where each Fed official expects rates to go. It often
  moves markets more than the rate decision itself.
- **CPI** (Bureau of Labor Statistics) — monthly, usually the 10th–15th,
  8:30 am ET. **PPI** (prices that producers charge) comes the same week.
- **PCE price index** (Bureau of Economic Analysis) — near the end of the
  month, released with personal income and spending. It is the inflation measure the
  Fed targets. But CPI comes out first, so it usually moves markets more.
- **The jobs report** (officially the Employment Situation) — usually the **first Friday**
  of the month, 8:30 am ET. It covers payrolls (the number of jobs added), the unemployment rate and wages. Weekly
  jobless claims (new applications for unemployment benefit) come every Thursday.
- **Retail sales** (mid-month), **ISM PMIs** (manufacturing on the first
  business day, services on the third; above 50 means the sector is growing) and the
  **GDP advance estimate**, the first estimate (about four weeks after quarter end).
- **Treasury auctions** — when the government sells new bonds. A weak 10- or 30-year auction (too few buyers) can by itself push yields up
  and stocks down.
- **Jackson Hole** — the Kansas City Fed's late-August conference, where the
  Fed chair has often signalled a change in direction.

```series
title: The S&P 500 and the 10-year yield around two CPI days, 2022
from: 2022-08-01
to: 2022-12-30
tf: D
line: us:SP500_PRICE_LONG | S&P 500
line: us:US10Y | US 10-year yield (%) | right
mark: 2022-09-13 | hot CPI
mark: 2022-11-10 | cool CPI
caption: On 13 Sept 2022 a hotter-than-expected CPI took the S&P 500 down about 4.3% in a day. On 10 Nov a cooler one lifted it 5.5% while the 10-year fell about a third of a percentage point.
```

In 2022 inflation was the only thing the market cared about. So CPI mornings were
the biggest days of the month (on 10 November the Nasdaq 100 rose about
7.4%). In calmer years the same release can pass almost unnoticed.
Know **which number the market is focused on now**. That is the one to
take seriously.

## 3. India

- **RBI Monetary Policy Committee** (MPC) — six meetings a year, roughly every two
  months, each over three days. The Governor announces the decision on the last
  morning. Banks, NBFCs (non-bank lenders), real estate and autos react most.
- **CPI** (Ministry of Statistics, MoSPI) — monthly, around the **12th**,
  in the evening, so the market reacts the next morning. **WPI** (wholesale prices) follows
  around the 14th.
- **IIP**, the index of industrial production (monthly; check MoSPI's calendar, which has been revised), and
  **GDP** (quarterly, end of February, May, August, November).
- **Union Budget** — **1 February** each year. In a general-election year,
  an interim budget comes in February and the full budget comes after the
  election (it came on 23 July in 2024). Tax changes on capital gains,
  securities transactions, fuel, gold and specific sectors are announced on the day.
- **Monsoon** — the India Meteorological Department (IMD) issues its first
  seasonal forecast in mid-April and an update around late May or June.
  The rains normally reach Kerala around 1 June. A good monsoon helps rural
  demand (tractors, two-wheelers, FMCG — everyday consumer goods — and fertilisers), and it helps keep food inflation down.
- **Elections** — general elections every five years, and state elections in
  between. Results day is a scheduled, binary event: one of two very different outcomes.
- Monthly on the 1st: **auto sales** and **GST collections** (goods and services tax receipts). Daily, after
  the close: provisional **FII/DII flows**.

### Results day, June 2024

```series
title: NIFTY 50 and India VIX around the 2024 general election
from: 2024-04-01
to: 2024-07-31
tf: D
line: india:NIFTY50 | NIFTY 50
line: india:INDIAVIX | India VIX | right
band: 2024-04-19 2024-06-01 | voting
mark: 2024-06-03 | exit polls
mark: 2024-06-04 | results
caption: India VIX more than doubled during voting, from about 11.5 to about 25. NIFTY rose 3.3% on exit polls, fell about 5.9% on results day as the ruling party lost its single-party majority, and was back above the pre-result close within three sessions. VIX was below 13 ten days later.
```

This sequence is the typical pattern for a binary event:

1. **Volatility built up in advance.** India VIX went from about **11.5 in mid-
   April to 24.6 by 31 May**, while seven phases of voting ran.
2. **Traders bought on the expected result.** Exit polls on the weekend projected a large
   majority. NIFTY rose about **3.3%** on Monday 3 June, to a record.
3. **The actual news was a shock.** On 4 June the count showed the ruling party
   short of a majority on its own. NIFTY closed about **5.9% lower**, from
   about 23,260 to 21,880, and India VIX hit about 26.8.
4. **The market absorbed it quickly.** Within days it was clear the coalition would hold. NIFTY
   closed back above 23,260 on 7 June, and India VIX was about 12.8 by
   14 June.

Anyone who bought breakouts at full size on 3 June took the whole drop. Waiting a day or
two meant buying lower, with the uncertainty gone. The Budget on 23 July 2024 was
the quiet version. NIFTY closed nearly flat, and India VIX fell from about
15.4 to 12.8. The volatility crush happened without a big price move.

## 4. Earnings seasons, rebalances and expiries

**Earnings seasons.** US results start about **two weeks after quarter
end**, with the big banks, and run for about six weeks. Indian companies must
report within 45 days of quarter end (60 for the year-end quarter). The
season opens with the large IT companies. A leading company's results move its whole
group the next morning.

**Index rebalances.** Index funds must buy and sell on fixed dates, when an index changes its members or weights:

- **S&P 500** — quarterly, after the close of the third Friday of March,
  June, September and December. **Russell** — the late-June annual rebuild of the Russell indexes
  has been among the heaviest trading days of the US year.
- **NSE indexes** (NIFTY 50 and others) — reviews twice a year, effective at
  the end of March and September.
- **MSCI** (a global index provider) — quarterly reviews (Feb, May, Aug, Nov) move foreign index-fund
  money into or out of India.

**Option expiries.** In the US, monthly options expire on the **third
Friday**. In March, June, September and December, stock options, index
options and index futures all expire together — **triple witching** — on the
same day as the S&P rebalance. So trading volume at the close is enormous, and prices can
be held near a level or pushed around for reasons unrelated to news. In India, index options
expire weekly, and stock futures and options monthly. **The rules
changed in 2024–25.** SEBI (India's market regulator) cut weekly expiries to one main index per
exchange, and the expiry weekday has moved. So check the exchange's current
calendar rather than relying on memory. Expiry days are often choppy, as
large positions are closed or moved to the next expiry.

## 5. Volatility around events

```series
title: The S&P 500 and the VIX, July–September 2024
from: 2024-07-01
to: 2024-09-30
tf: D
line: us:SP500_PRICE_LONG | S&P 500
line: us:VIX | VIX | right
mark: 2024-08-02 | weak jobs report
mark: 2024-08-05 | VIX close 38.6
caption: A soft July jobs report on 2 Aug, on top of traders rushing to close yen-funded carry trades after the Bank of Japan raised rates, took the VIX from about 16 to a close near 38.6 on 5 Aug. Two weeks later it was below 15 and the S&P 500 had recovered most of its fall.
```

August 2024 shows what happens when an event hits a market where many traders hold the same bets. The
S&P 500 had already slipped from its mid-July high. The jobs report on
Friday 2 August came in weak: the S&P fell about 1.8%, and the 10-year
dropped from about 3.98% to 3.79% that day. By Monday 5 August the
S&P was about **8.5% below its 16 July high**, and the VIX closed near
**38.6**. By 16 August the VIX was about **14.8**. Volatility spikes caused by
events usually fade fast. **A spike is a reason to trade smaller, not a
reason to sell everything at the low.**

The pattern repeats in both markets: **implied volatility rises before a
scheduled event and collapses after it**, whatever the outcome. Around the
2024 US election the VIX drifted up to about 23. It then fell from about 20.5
to 16.3 the day after the vote, as the S&P 500 rose about 2.5%. The day
*after* an event is usually a better time to put money in than the day
before.

## 6. The trader's rules around events

1. **No new full-size positions the day before a big binary event.** That means an FOMC meeting
   with a dot plot, a CPI release the market is focused on, an RBI policy decision,
   Budget day, or an election result. Either wait, or enter at half size and
   add once the event is past.
2. **Reduce size or tighten stops on what you hold.** If the price gaps past your stop, the stop
   fills wherever the market opens. Could you live with a 5% gap down?
3. **Avoid holding through a stock's own earnings unless you planned to.**
   A results gap can jump straight past the stop. If you hold, make the
   position big enough to matter but small enough that a gap of twice the
   stop distance would not hurt badly. Or hold only stocks where you already have a profit to absorb the hit.
4. **Give the market a day to absorb the news.** The first reaction is often
   reversed (June 2024). The day after, the direction is more reliable.
5. **Respect the market regime.** When the VIX is above 25 or India VIX above 20,
   the app already halves risk per trade. Take that as the cue to be
   pickier, too.
6. **Know your gap risk.** US data comes out after the Indian market closes; Asian
   news comes out before the US opens. So events usually hit overnight.

### What this app's strategies do with earnings

The strategies check how many days remain until a stock's next results. (Search
`scripts/swing_screener/strategies/` for `earnings_days_away` to see the code.) The rule comes
in two strengths: a hard gate rejects the setup, while a watch flag only marks it.

| Strategy | Earnings rule (live screening) |
|---|---|
| `trend_pullback` | Hard gate D2: no setup if earnings are 10 or fewer business days away; earnings within 15 days also block the HIGH CONFIDENCE label |
| `breakout` | Hard gate B7: no setup within 10 days; within 15 days blocks HIGH CONFIDENCE |
| `chart_pattern` | Hard gate P5: no setup within 10 trading days |
| `chart_pattern_spec` | Hard gate S3: no setup within `EARNINGS_DAYS` (10) trading days |
| `minervini` | Watch flag V5: earnings due within 10 days — flagged, not rejected |
| `minervini_spec` | Watch flag B4: earnings within `EARNINGS_WARN_DAYS` (10) days |
| `donchian` | No earnings rule |

Two caveats. First, if the earnings date is **unknown, the stock passes**. Second, the **backtests never
apply these rules**. The backtester (`backtesting/backtest.py`) has no record of which earnings dates
were known at each past date, so it passes none. Tested results therefore include trades held through
earnings. And none of the strategies looks at *macro* dates. Watching FOMC,
CPI, RBI and Budget days is your job.

## 7. Events at a glance

| Event | Frequency | Typical date | What it moves |
|---|---|---|---|
| FOMC decision (+ dot plot quarterly) | 8 a year | Set in advance; 2 pm ET | Yields, dollar, growth stocks, then the world |
| FOMC minutes | 8 a year | 3 weeks after each meeting | Yields, mostly at the margin |
| US CPI / PPI | Monthly | ~10th–15th, 8:30 am ET | Yields, Nasdaq, dollar, gold |
| US PCE | Monthly | End of month | Yields (less than CPI) |
| US jobs report | Monthly | First Friday, 8:30 am ET | Yields, dollar, rate expectations |
| US retail sales | Monthly | Mid-month | Consumer stocks, yields |
| ISM PMIs | Monthly | 1st and 3rd business day | Cyclicals, yields |
| US GDP advance | Quarterly | ~4 weeks after quarter end | Usually modest |
| 10y / 30y Treasury auctions | Monthly | Mid-month | Long yields |
| Jackson Hole | Yearly | Late August | Rate expectations |
| US earnings season | Quarterly | Starts ~2 weeks after quarter end | Stocks and their groups |
| S&P rebalance / triple witching | Quarterly | 3rd Friday of Mar/Jun/Sep/Dec | Closing volume, index members |
| RBI MPC | 6 a year | ~every two months | Banks, NBFCs, realty, autos, rupee |
| India CPI / WPI | Monthly | ~12th / ~14th | Rate expectations, banks |
| India GDP | Quarterly | End of Feb/May/Aug/Nov | Usually modest |
| Union Budget | Yearly | 1 February (July in an election year) | Taxed and favoured sectors, whole market |
| Monsoon (IMD forecasts, onset) | Yearly | Mid-April forecast; onset ~1 June | Rural demand, FMCG, autos, fertilisers |
| Election results | Every 5 years (states in between) | Announced in advance | Whole market, PSUs, policy sectors |
| India results season | Quarterly | Within 45 days of quarter end | Stocks and their groups |
| NSE F&O (futures and options) expiry | Weekly (index) / monthly | Per current NSE calendar | Index held near a level, choppy intraday moves |
| MSCI / NSE index reviews | Quarterly / semi-annual | Feb/May/Aug/Nov; end-Mar/Sep | Foreign passive flows, index members |

## 8. A weekly prep routine

Sunday or Monday morning, fifteen minutes:

1. **List the week's macro dates** from the official calendars. Mark the
   one or two the market cares most about now.
2. **List earnings dates for your positions and watchlist.** Use Post-market's
   *Earnings in the next 10 days*, or each chart's News & events panel.
3. **Decide in advance** what you will do around each: hold, trim, or make no new entries
   until after. Write it in the **Notes** journal.
4. **Check the VIX / India VIX.** If it is already high, the market is
   already expecting big moves.
5. **Plan the day after in advance.** Which setups would you take if the event
   passes calmly? Have the list ready, so you act on the market's settled reaction, not the
   headline.

## 9. What the evidence says

- **Robust:** prices react to the surprise against the consensus, not to the number itself.
  Implied volatility rises before scheduled events and falls after them.
  Results days produce the largest single-stock gaps of the quarter.
- **Well documented:** historically, a large share of US stock returns has
  come in the day before FOMC announcements (the "pre-FOMC drift" studied by
  Lucca and Moench). But the effect has been weaker since it was published, so
  do not trade it as a rule.
- **Closer to folklore:** "sell the news" happens when many traders hold the same
  bet, but it is not a law; many events pass with no reversal. Elaborate rules
  such as "the market always falls into the Budget" do not hold up when you check
  the data.
- **Timing:** the first reaction is fast and often wrong. The market's
  verdict usually settles within one to three sessions.
- **For this app:** the earnings gates apply only to live screening. The backtests cannot
  measure whether they help.

## 10. Checklist

- What are this week's two most important macro events, in each market?
- Which number is the market most focused on right now (inflation, jobs,
  growth)?
- Do any positions or planned entries report earnings within 10 days?
- Am I opening full-size positions the day before a binary event? (Don't.)
- If everything gapped 5% against me, is the total loss acceptable?
- Is the VIX above 25 or India VIX above 20 — is sizing already halved?
- Is an option expiry, rebalance or results season distorting this week?
- After the event: wait a session, then act on the reaction that holds.

## Further reading

- Federal Reserve (federalreserve.gov) — the FOMC meeting calendar,
  statements, minutes and Summary of Economic Projections.
- U.S. Bureau of Labor Statistics (bls.gov) and Bureau of Economic Analysis
  (bea.gov) — release schedules for CPI, PPI, jobs, PCE and GDP.
- Reserve Bank of India (rbi.org.in) — MPC schedule and policy statements.
- Ministry of Statistics and Programme Implementation (mospi.gov.in) —
  India's CPI, IIP and GDP release calendar.
- NSE India (nseindia.com) — F&O expiry calendar and index review notices.
- David Lucca and Emanuel Moench, "The Pre-FOMC Announcement Drift",
  *Journal of Finance* (2015).
