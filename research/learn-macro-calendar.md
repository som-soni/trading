# The macro event calendar — the dates that move whole markets

Learning material: the scheduled events that move whole markets in the US
and India — central banks, inflation and jobs data, budgets, elections,
earnings seasons, rebalances and expiries — why they move prices, what
volatility does around them, and the rules a swing trader uses to avoid the
wrong side of a gap. Companions: [the rates guide](learn-macro-rates.md) and
[the inflation guide](learn-macro-inflation.md).

**Where this shows in the app.** A stock's own earnings date is tracked:
the **Chart** marks past results with an "E", its **News & events** panel
lists what is coming, the setups table on **Strategies** has an *Earnings in
(d)* column, and **Markets → Post-market** lists earnings in the next 10
days among watched and screened names. Market-wide volatility is part of
the regime (`scripts/swing_screener/core/regime.py`): when the VIX is above
25 (US) or India VIX above 20, live position sizing halves the risk per
trade, from 1% to 0.5% of equity. Macro release dates themselves are not in
the app — use the official calendars in Further reading.

---

## 1. Why scheduled events move markets

Markets react to **news versus what was expected**: prices already reflect
the consensus, so a CPI of 3.0% is bullish against a 3.3% forecast and
bearish against 2.7%.

- **The surprise is the signal.** The size of a move depends on how far the
  number is from consensus and on how much the market cares about that
  number *right now* — in 2022 CPI was everything; in other years it barely
  registers.
- **"Buy the rumour, sell the news."** When an outcome is widely expected
  and positioned for, the event itself can trigger the opposite move: the
  people who wanted to own it already do.
- **Volatility is priced in advance.** Options get dearer before a known
  event and cheaper the moment it passes — the "volatility crush" — whatever
  the direction.

## 2. The United States

- **FOMC meetings** — eight scheduled a year. The statement comes at 2:00 pm
  ET and the chair's press conference at 2:30. The **minutes** follow three
  weeks later. At four meetings (March, June, September, December) the Fed
  also publishes its **Summary of Economic Projections**, including the
  **dot plot** of each official's expected rate path — often the bigger
  market event than the decision itself.
- **CPI** (Bureau of Labor Statistics) — monthly, usually the 10th–15th,
  8:30 am ET; **PPI** the same week.
- **PCE price index** (Bureau of Economic Analysis) — near the end of the
  month, with personal income and spending. It is the inflation measure the
  Fed targets, but CPI comes first and so usually moves markets more.
- **The jobs report** (Employment Situation) — usually the **first Friday**
  of the month, 8:30 am ET: payrolls, the unemployment rate, wages. Weekly
  jobless claims come every Thursday.
- **Retail sales** (mid-month), **ISM PMIs** (manufacturing on the first
  business day, services on the third; above 50 is expansion) and the
  **GDP advance estimate** (about four weeks after quarter end).
- **Treasury auctions** — a weak 10- or 30-year auction can push yields up
  and stocks down on its own.
- **Jackson Hole** — the Kansas City Fed's late-August symposium, where the
  chair has often signalled a change in direction.

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

In 2022 inflation was the market's single question, so CPI mornings were
the biggest days of the month (on 10 November the Nasdaq 100 rose about
7.4%). In calmer years the same release can pass almost unnoticed.
Know **which number the market is obsessed with now** — that is the one to
respect.

## 3. India

- **RBI Monetary Policy Committee** — six meetings a year, roughly every two
  months, over three days; the Governor announces the decision on the last
  morning. Banks, NBFCs, real estate and autos react most.
- **CPI** (Ministry of Statistics, MoSPI) — monthly, around the **12th**,
  in the evening, so the market reacts the next morning. **WPI** follows
  around the 14th.
- **IIP** (monthly; check MoSPI's calendar, which has been revised) and
  **GDP** (quarterly, end of February, May, August, November).
- **Union Budget** — **1 February** each year. In a general-election year
  an interim budget comes in February and the full budget after the
  election (it came on 23 July in 2024). Tax changes on capital gains,
  securities transactions, fuel, gold and specific sectors land on the day.
- **Monsoon** — the India Meteorological Department (IMD) issues its first
  seasonal forecast in mid-April and an update around late May or June;
  onset over Kerala is normally around 1 June. A good monsoon helps rural
  demand (tractors, two-wheelers, FMCG, fertilisers) and food inflation.
- **Elections** — general elections every five years and state elections in
  between. Results day is a scheduled, binary event.
- Monthly on the 1st: **auto sales**, **GST collections**. Daily, after
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

The sequence is the template for a binary event:

1. **Volatility built in advance.** India VIX went from about **11.5 in mid-
   April to 24.6 by 31 May** while seven phases of voting ran.
2. **The rumour was bought.** Exit polls on the weekend projected a large
   majority; NIFTY rose about **3.3%** on Monday 3 June to a record.
3. **The news was a shock.** On 4 June the count showed the ruling party
   short of a majority on its own; NIFTY closed about **5.9% lower**, from
   about 23,260 to 21,880, and India VIX hit about 26.8.
4. **It was digested quickly.** The coalition was secure within days; NIFTY
   closed back above 23,260 on 7 June, and India VIX was about 12.8 by
   14 June.

Full-size breakout buys on 3 June took the whole drop; waiting a day or
two bought lower with the uncertainty gone. The Budget on 23 July 2024 was
the quiet version: NIFTY closed nearly flat and India VIX fell from about
15.4 to 12.8 — the crush happened without a big move.

## 4. Earnings seasons, rebalances and expiries

**Earnings seasons.** US results start about **two weeks after quarter
end** with the big banks and run about six weeks. Indian companies must
report within 45 days of quarter end (60 for the year-end quarter); the
season opens with the large IT companies. A leader's results move its whole
group the next morning.

**Index rebalances.** Passive funds must trade on fixed dates:

- **S&P 500** — quarterly, after the close of the third Friday of March,
  June, September and December. **Russell** — the late-June reconstitution
  has been among the heaviest trading days of the US year.
- **NSE indexes** (NIFTY 50 and others) — semi-annual reviews, effective at
  the end of March and September.
- **MSCI** — quarterly reviews (Feb, May, Aug, Nov) move foreign passive
  flows into India.

**Option expiries.** In the US, monthly options expire on the **third
Friday**; in March, June, September and December stock options, index
options and index futures expire together — **triple witching** — on the
same day as the S&P rebalance, so closing volume is enormous and prices can
be pinned or pushed for reasons unrelated to news. In India, index options
have weekly expiries and stock futures and options monthly ones. **The rules
changed in 2024–25** — SEBI cut weekly expiries to one benchmark index per
exchange and the expiry weekday has moved — so check the exchange's current
calendar rather than relying on memory. Expiry days are often choppy as
large positions are closed or rolled.

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
caption: A soft July jobs report on 2 Aug, on top of the yen carry-trade unwind after the Bank of Japan's hike, took the VIX from about 16 to a close near 38.6 on 5 Aug. Two weeks later it was below 15 and the S&P 500 had recovered most of its fall.
```

August 2024 is the example of an event landing on a crowded market. The
S&P 500 had already slipped from its mid-July high; the jobs report on
Friday 2 August came in weak (the S&P fell about 1.8% and the 10-year
dropped from about 3.98% to 3.79% that day), and on Monday 5 August the
S&P was about **8.5% below its 16 July high** with the VIX closing near
**38.6**. By 16 August the VIX was about **14.8**. Volatility spikes from
events mean-revert fast — **a spike is a reason for smaller size, not a
reason to sell everything at the low**.

The pattern repeats in both markets: **implied volatility rises into a
scheduled event and collapses after it**, whatever the outcome. Around the
2024 US election the VIX drifted up to about 23, then fell from about 20.5
to 16.3 the day after the vote as the S&P 500 rose about 2.5%. The day
*after* an event is usually a better time to commit capital than the day
before.

## 6. The trader's rules around events

1. **No new full-size positions the day before a big binary event.** FOMC
   with a dot plot, a CPI print the market is obsessed with, RBI policy,
   Budget day, an election result. Either wait, or enter at half size and
   add once the event is past.
2. **Reduce size or tighten stops on what you hold.** Through a gap a stop
   fills wherever the market opens: could you live with a 5% gap down?
3. **Avoid holding through a stock's own earnings unless it is planned.**
   A results gap can blow straight through the stop. If you hold, hold a
   position big enough to matter but small enough that a gap of twice the
   stop distance is survivable — or hold only stocks with a profit cushion.
4. **Let the market digest for a day.** The first reaction is often
   reversed (June 2024); the day after, the direction is more honest.
5. **Respect the regime.** When the VIX is above 25 or India VIX above 20,
   the app already halves risk per trade; take that as the cue to be
   pickier, too.
6. **Know your gap risk.** US data lands after the Indian close; Asian
   news before the US open. Overnight is where events hit.

### What this app's strategies do with earnings

Grep `scripts/swing_screener/strategies/` for `earnings_days_away` and you
find the rule applied in two strengths:

| Strategy | Earnings rule (live screening) |
|---|---|
| `trend_pullback` | Hard gate D2: no setup if earnings are 10 or fewer business days away; earnings within 15 days also block the HIGH CONFIDENCE label |
| `breakout` | Hard gate B7: no setup within 10 days; within 15 days blocks HIGH CONFIDENCE |
| `chart_pattern` | Hard gate P5: no setup within 10 trading days |
| `chart_pattern_spec` | Hard gate S3: no setup within `EARNINGS_DAYS` (10) trading days |
| `minervini` | Watch flag V5: earnings due within 10 days — flagged, not rejected |
| `minervini_spec` | Watch flag B4: earnings within `EARNINGS_WARN_DAYS` (10) days |
| `donchian` | No earnings rule |

Two caveats: an **unknown earnings date passes**, and the **backtests never
apply these rules** — `backtesting/backtest.py` has no point-in-time earnings
calendar and passes none, so tested results include trades held through
earnings. And none of the strategies looks at *macro* dates: FOMC,
CPI, RBI and Budget day are your job.

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
| NSE F&O expiry | Weekly (index) / monthly | Per current NSE calendar | Index pinning, intraday chop |
| MSCI / NSE index reviews | Quarterly / semi-annual | Feb/May/Aug/Nov; end-Mar/Sep | Foreign passive flows, index members |

## 8. A weekly prep routine

Sunday or Monday morning, fifteen minutes:

1. **List the week's macro dates** from the official calendars; mark the
   one or two the market cares most about now.
2. **List your positions' and watchlist's earnings** — Post-market's
   *Earnings in the next 10 days*, or each chart's News & events panel.
3. **Decide in advance** what you do on each: hold, trim, or no new entries
   until after. Write it in the **Notes** journal.
4. **Check the VIX / India VIX**: already elevated means the market is
   braced.
5. **Pre-plan the day after.** Which setups would you take if the event
   passes calmly? Have the list ready so you act on the digestion, not the
   headline.

## 9. What the evidence says

- **Robust:** prices react to the surprise versus consensus, not the level;
  implied volatility rises before scheduled events and falls after them;
  results days produce the largest single-stock gaps of the quarter.
- **Well documented:** a large share of US equity returns has historically
  arrived around FOMC announcements (the "pre-FOMC drift" studied by Lucca
  and Moench) — but the effect has been weaker since it was published, so
  do not trade it as a rule.
- **Folklore-leaning:** "sell the news" is real when positioning is
  crowded, not a law; many events pass with no reversal. Elaborate rules
  such as "the market always falls into the Budget" do not survive a look
  at the data.
- **Lags:** the first reaction is fast and often wrong; the verdict
  usually settles within one to three sessions.
- **For this app:** the earnings gates are live-only; the backtests cannot
  measure whether they help.

## 10. Checklist

- What are this week's two most important macro events, in each market?
- Which number is the market obsessed with right now (inflation, jobs,
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
