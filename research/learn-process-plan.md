# A trading plan and routine — decide when calm, execute under pressure

**In short**

- A trading plan is a page of decisions made in advance: what you trade, how you enter, where the stop goes, how much you risk, and when you stand aside.
- Write it when nothing is at stake, so that you only have to look it up when a stock gaps through your stop or you have lost five times in a row.
- Run it with a fixed routine: the real work after the close, a short check before the open, a weekly review and a monthly review.
- Losing streaks are longer than they feel. A method that wins 35% of its trades will usually lose 10 or more in a row somewhere in 500 trades.
- Change the plan only at the monthly review, one rule at a time, with the date and the reason written down.

This is the first of three process guides. The next two are [journaling and review](learn-process-journal.md)
and [biases](learn-process-biases.md). Each step below links to the guide that explains it.

---

## 1. Why write it down

Picture a Tuesday evening. A stock you hold reports results after the close. Tomorrow it may open 10% lower,
straight through your stop. If you decide what to do tomorrow at 9:15, you decide in fear.

A plan is decisions made **when nothing is at stake**. Then none has to be made **when everything feels at stake**:
a stock gapping through the stop, or the fourth loss in a row ([biases](learn-process-biases.md)). In those moments
you look up what you already agreed with yourself.

A written plan also does three other jobs:

- **It makes results measurable.** Trades that follow the same rules tell you whether the *rules* work
  ([journal](learn-process-journal.md)).
- **It caps a bad day.** Limits on size, heat and drawdown are arithmetic. Heat is the total you would lose if
  every stop were hit at once. You cannot redo that arithmetic honestly in a panic ([portfolio risk](learn-risk-portfolio.md)).
- **It gets you through losing streaks.** Breakout and trend methods often win only 30–40% of their trades. At
  those rates, long runs of losses are normal (the table below).

How long can a losing streak be when nothing is wrong? We simulated it. Each trade wins with a fixed chance,
independent of every other trade, and 500 trades were drawn 5,000 times. At one trade a week, 500 trades is about
ten years.

| Win rate | Longest losing streak in 500 trades: typical (median) | 1 run in 10 is at least | Chance of 10 or more in a row | Chance of 15 or more |
|---|---|---|---|---|
| 30% | 15 | 20 | 99% | 52% |
| 35% | 12 | 17 | 92% | 23% |
| 40% | 11 | 14 | 70% | 9% |
| 50% | 8 | 11 | 22% | 1% |

Real trades are not independent, so real streaks are longer still (§9). **Keep the plan to one page** (§4). A plan
you cannot read in two minutes will not be read.

## 2. What your tools do — and what the plan must cover

Most traders use three tools. A charting and screening tool finds and shows setups. A broker takes orders. A record
— a spreadsheet, a journal or a notebook — keeps positions and results. None of them runs your plan for you.

| A charting or screening tool can | Your plan must still decide |
|---|---|
| Load prices, breadth and sector data after each close (§5) | Whether the data is current before you act |
| Find setups and suggest an entry, a stop and a target | Which setups you take |
| Show the stop distance as a percentage | How many shares that means ([sizing](learn-risk-sizing.md) §3) |
| Show volatility (VIX, India VIX) and the index trend | How much smaller to trade when the market is weak |
| Show earnings dates | What to do with stocks you already hold into results |
| — | **Placing, changing and cancelling orders** with your broker |
| — | **Tracking positions, stops, open risk and profit or loss** |
| — | Knowing the macro dates ([calendar](learn-macro-calendar.md)) |

Write in the plan where your positions are kept, and update that record every day. A position you cannot see is a
risk you cannot measure.

## 3. What a plan contains

| Part | What to write | Explained in |
|---|---|---|
| **Markets and universe** | US, India or both; minimum price and daily traded value; what you never trade | [Volume](learn-price-volume.md) |
| **Setups** | **One or two** setups, not every pattern you know; what the chart must show | [Bases](learn-bases.md), [VCP](learn-vcp.md), [chart patterns](learn-chart-patterns.md), [strategies overview](learn-strat-overview.md) |
| **Entry** | A buy-stop order (it buys only if the price rises to it), placed before the open; how many days it stays; the chase limit — the most you will pay above the entry (about 5%) | [VCP](learn-vcp.md) §5 |
| **Stop** | Under structure, entered as an order as soon as the entry fills; never lowered; pass on stops wider than about 8% | [Stops and exits](learn-risk-stops-exits.md) §1–3 |
| **Size** | Risk 1% of equity (0.5% when VIX > 25 or India VIX > 20); shares = risk ÷ (entry − stop); no position over 25% of equity | [Sizing](learn-risk-sizing.md) §3, [volatility](learn-health-volatility.md) §11 |
| **Exits** | A target, a trend exit, or part into strength and the rest on a trend break — chosen before the entry | [Stops and exits](learn-risk-stops-exits.md) §6–10 |
| **Limits** | Heat at most 6% of equity; 8–10 positions at most; two or three per industry group; about a third in one sector | [Portfolio risk](learn-risk-portfolio.md) §11, [sectors](learn-sectors-groups.md) §8 |
| **Standing aside** | The exposure ladder below | [Trend](learn-health-trend.md) §8, [regime filters](learn-strat-regime-filters.md) |
| **Events** | No entry within about 10 trading days of results; for holdings, exit, trim or hold with a cushion, decided per stock; no new full-size entry the day before an FOMC meeting, a big CPI release, an RBI policy decision, the Budget or an election result | [Calendar](learn-macro-calendar.md) §6, [earnings](learn-fund-earnings.md) |
| **Drawdown** | From the **equity peak**: at −10% halve risk per trade; at −20% stop opening trades and review; restore after a recovery, not after a date | [Portfolio risk](learn-risk-portfolio.md) §8 |

### Style and timeframe

How long do swing trades last? Two textbook rules, run on stored daily prices for 2013–2026, give a feel for it.
They are illustrations of the idea, not strategies to trade:

- **55-day breakout**: buy at the next open after a close above the highest high of the prior 55 days. The stop
  is two ATRs below the entry. Exit at the next open after a close below the lowest low of the prior 20 days.
- **20-day breakout with a 2R target**: buy after a close above the prior 20-day high, with the close above the
  50-day average and the 50-day above the 200-day. The stop is two ATRs below. Sell at +2R, or after 20 sessions.

Each rule holds at most ten positions at once, taking the most heavily traded stocks first. Holding times, in
calendar days ("middle half" is the range covering the middle 50% of trades):

| Rule (market) | Median hold | Middle half | New trades a year |
|---|---|---|---|
| 55-day breakout (US · India) | 28 · 26 | 7–67 · 8–69 | 77 · 70 |
| 20-day breakout, 2R target (US · India) | 17 · 15 | 7–27 · 7–27 | 198 · 189 |

That is one to four new trades a week, held for weeks. It needs an evening routine, not a screen watched all day.
Write down which holding style is yours.

### Standing aside — the exposure ladder

The ladder has three levels ("rungs"), from full exposure to cash. Pick the rung from evidence you can read in a
minute. Move only one rung at a time, and only when two or three warnings agree. The warnings come from trend,
[breadth](learn-health-breadth.md), [volatility](learn-health-volatility.md) and
[distribution](learn-health-distribution.md).

| Rung | Evidence | Exposure |
|---|---|---|
| Full | Index above a rising 50-day and 200-day average; breadth healthy | Normal size and count |
| Reduced | Index below its 50-day, or weak breadth | Half size or half the positions; best setups only |
| Cash / minimal | Index below a falling 200-day; 20%+ drawdown | No new entries; manage exits; keep the watchlist |

A quick warning, such as both broad indices closing below their 50-day average, switches on and off often. We counted it over
2013–2026. In the US, with the S&P 500 and the Nasdaq 100, it started about seven times a year. In India, with the Nifty 50 and the Nifty 500, it started about six times a year. So one day of it means "be pickier", not a new rung.

## 4. The one-page template

Keep the plan where you will see it before every session: a pinned note, the first page of your journal, or a
printed sheet. Fill in every line. Change it only at the monthly review (§8), never during the session.

```text
TRADING PLAN — version / date
Markets: US / India.   Universe: ______ (min price, min daily value)
Style: swing/position, daily bars. Decisions after the close; orders before the open.
Setups I trade: ______ (one or two)
  Chart must show: ______ (base, tight area, volume, no supply overhead)
Entry: buy-stop at the setup entry, valid __ days; skip if filled > __% above entry
Stop: setup stop, placed on fill; skip setups with stop > __%; never lowered
Size: risk __% of equity (half if VIX > 25 / India VIX > 20); shares = risk ÷ (entry − stop);
  max __% of equity in one position
Exit: ______ (target / trend exit / partial + trail). Raise stop when ______
Limits: heat ≤ __%; ≤ __ positions; ≤ __ per industry group; ≤ __% in one sector
Market: Full / Reduced / Cash by ______ (index vs 50/200-day, breadth, volatility)
Events: no entry within __ days of results; holdings into results: ______;
  no new full size the day before FOMC / CPI / RBI / Budget
Drawdown: at −__% from peak halve risk; at −__% stop and review
Losing streak: after __ losses in a row, review the trades before the next one
Where my positions live: ______ (broker / sheet / journal) — updated daily
```

## 5. When the numbers are current

Suppose you scan for breakouts at 6 p.m., but your data provider has not yet loaded today's close. The scan then
shows yesterday's setups, and you place orders on a stale picture. So the first step of every routine is a data
check.

Before you act, confirm three things:

- **The last session is there.** The latest bar on a chart is today's date (or the last trading day).
- **Holidays are understood.** A missing day may be an exchange holiday, not a data gap. The two markets have
  different holidays.
- **Corporate actions are applied.** A split or a bonus issue that is not adjusted looks like a crash and can
  trigger a false stop.

**Plan rule:** no order from a scan until the data is current. One session late is a warning; two sessions late
is stale.

### Local times

India has no daylight saving time. New York does, from the second Sunday of March to the first Sunday of
November. So US times shift by an hour in Indian time (IST):

| Event | New York | India (US summer · US winter) |
|---|---|---|
| NSE session | — | 09:15–15:30 |
| NYSE / Nasdaq session | 09:30–16:00 | 19:00–01:30 · 20:00–02:30 |
| US close | 16:00 | 01:30 · 02:30 (next day) |

## 6. The daily routine, step by step

Start after the close, once the data has updated. It takes about **30–45 minutes** for one market, less on quiet
days. Any charting tool will do.

| # | Step | What to check | Minutes |
|---|---|---|---|
| 1 | **Data** | Last session loaded; no unadjusted splits (§5) | 2 |
| 2 | **Market tone** | Index against its 50-day and 200-day; how many stocks are above their 50-day; volatility (VIX, India VIX); new highs against new lows; decide the rung (§3) | 5 |
| 3 | **Sectors and groups** | Which sectors and industry groups lead; any newly improving; your holdings' groups weakening ([sectors](learn-sectors-groups.md)) | 3–5 |
| 4 | **Your holdings** | Each one against its stop and exit rule; big moves on heavy volume; results dates inside ten days | 5 |
| 5 | **Scan** | Only your setups; stop distance within your limit | 5–10 |
| 6 | **Chart each candidate** | The base and the tight area; stop under structure; overhead supply; next results date | 2–3 each |
| 7 | **Watchlist** | Add the ones you want, with a note of the entry and stop; remove stale names | 5 |
| 8 | **Orders** | Size each order; place buy-stops and stops with the broker; update the positions record | 5–10 |
| 9 | **Journal** | Market, positions, watching, lessons ([journal](learn-process-journal.md)) | 3 |

Then stop. Reading more after the plan is set only reopens a decision you made calmly.

### US and India, by where you live

- **US from New York:** do the review in the evening. Check again at about 09:00, before orders go live at 09:30.
- **India from India:** do the review in the evening. Check again at about 09:00 IST, before the NSE opens at 09:15.
- **Both, from India:** the US closes in the early hours IST. So the US review fits the **IST morning**, beside
  India's pre-open check, with US orders in before 19:00 or 20:00 IST. India's review is in the IST evening.

## 7. Pre-market against after-close work

**After the close** is when the real work happens: reading the market, choosing setups, checking charts, sizing,
writing orders and stops, and the journal.

**Before the open** is a few minutes of checking:

- Is overnight news out for a stock with an order or a holding?
- Has a results date moved inside ten days?
- Has a holding's price moved through its stop in another session or market?

Cancel an order if the reason for it no longer holds. **Decide in the evening, verify in the morning, never
re-decide.** The morning may cancel or shrink a trade. It may never add a trade the evening did not choose.

## 8. Weekly and monthly

### Weekly — about 30–45 minutes, at the weekend

1. **The week's calendar** — FOMC, CPI, jobs, RBI, India CPI, expiries, and your holdings' and watchlist's
   results. Write the decision for each before Monday ([calendar](learn-macro-calendar.md) §8).
2. **Rotation** — the top 15–20 industry groups by relative strength (RS), the biggest one-month changes, and
   which groups are improving or weakening ([sectors](learn-sectors-groups.md) §8).
3. **Market rung** for next week — the weekly close against the 30-week average, and breadth over the week.
4. **Heat and concentration** — for each position, (the lower of price and cost − stop) × shares; add them up and
   divide by equity. Count positions per group ([portfolio risk](learn-risk-portfolio.md) §5).
5. **Prune the watchlist** — remove names that broke their base, lost the 50-day or sit in a lagging group. Keep
   it short enough to chart in one sitting.
6. **Review the week's closed trades** against the plan ([journal](learn-process-journal.md)).

### Monthly — about an hour

- **Equity against its peak** — does the drawdown rule change your size?
- **Numbers by setup** — win rate, average win and loss in R, expectancy. They mean something only after 30–50
  trades per setup ([expectancy](learn-risk-expectancy.md) §5).
- **Against what you expected** — compare with your own tested numbers for the setup, if you have them. An
  average loss worse than −1R means stops were moved or positions were held through results. A much lower win
  rate means the trades you took are not the ones the rules select.
- **Compliance** — what share of trades followed every rule ([biases](learn-process-biases.md))?
- **Change the plan only here**, one rule at a time. Write the date and the reason in the plan, and give it a new
  version number. Then later results can be read against the rules that produced them.

## 9. If-then rules

Decide these now; look them up then.

| Situation | Rule |
|---|---|
| A stock **gaps below the stop** at the open | Exit at the market — the stop's job is done; do not wait for a bounce. Log the R |
| A stock **gaps far above the entry** | Skip it if the fill would be more than your chase limit above the entry; the risk to the stop is now larger than planned |
| **Results tomorrow** for a holding | Do what the weekly review decided: exit, trim, or hold only with a cushion big enough to survive a gap of twice the stop |
| **Results within 10 days** for a new setup | No entry; put it on the watchlist for after the report |
| The market **moves down a rung** | No new breakouts at full size; tighten stops on laggards; keep the watchlist |
| **VIX above 25 / India VIX above 20** | Half risk per trade; fewer new positions |
| **Three losses in a row** | Review the three trades against the plan before the next one (see below) |
| **Drawdown −10% / −20%** from the peak | Halve risk / stop new trades and review |
| Heat at the limit | No new trade until a stop is raised or a position closes |
| **Data not current** | No new orders until it is |
| A **big macro event** tomorrow | No new full-size entry today; enter after the reaction if the setup holds |

How often does a stop gap? In the two illustrative rules of §3, about one stop in ten (India) to one in six (US)
filled below the stop price. The median gapped stop cost about −1.2R instead of −1R. Plan for it: it is part of
the normal cost of a stop.

### Three losses in a row — what simulation and illustrative trades show

We tested two common reactions to a losing streak. A "trigger" is the third losing exit in a row:

- **skip**: take no entry in the seven days after a trigger;
- **halve**: halve the risk on any entry while the last three exits were losses, until a winner.

First, the simple case: a simulated method that wins 35% of trades, with wins that vary but average 2.5R, and losses of
−1R. Every trade is independent of the last. Over 500 trades, the median run had 48 triggers.

Skipping three
trades after each trigger cut total R from +112R to +79R. Halving cut it to +97R. Both made the worst drawdown a
little shallower (from about −25R to about −22R).

When trades are independent, a streak tells you nothing about the next trade. A pause then just throws away
trades with a positive expectancy.

Real trades are not independent. The two rules of §3 hold up to ten stocks at once, and one market drop can stop
out several of them together. So their streaks were far longer than the simulation's: 28–30 losses in a row in
each of the four runs.

| Rule (market) | Triggers a year | Expectancy, entries in the week after a trigger | Expectancy, other entries | Total R: base → skip → halve | Worst drawdown: base → skip → halve |
|---|---|---|---|---|---|
| 55-day breakout (US) | 7.1 | +0.07R | +0.17R | +148 → +124 → +132 | −61 → −52 → −45 |
| 55-day breakout (India) | 6.5 | +0.23R | +0.14R | +155 → +100 → +130 | −87 → −52 → −64 |
| 20-day breakout (US) | 13.7 | +0.08R | +0.09R | +237 → +166 → +205 | −58 → −56 → −48 |
| 20-day breakout (India) | 13.3 | +0.03R | +0.04R | +91 → +65 → +102 | −85 → −57 → −62 |

What this shows:

- **Streaks are frequent**: 6–14 triggers a year.
- **The streak did not reliably predict the next trade.** Entries after a trigger did worse in three runs and
  better in one.
- **Skipping a week lowered total R in all four runs.** It also made drawdowns shallower, because fewer trades
  means less of everything.
- **Halving until a winner cut the worst drawdown in all four runs.** It cost some total R in three runs and added
  a little in one.

So **three losses trigger a review, not a pause**. Was each one a plan trade: stop placed, size right, no results
held through, rung respected? If so, take the next setup at normal size. Size is cut by the **drawdown** rule
(§3), which reacts to how much was lost, not to how many trades lost it.

## 10. What the evidence says

- **Robust:** rules fixed in advance hold up better under stress than judgement on the spot. That is the case
  for checklists (Gawande), and the theme of every trading author below. Fixed-fractional risk and drawdown limits
  are arithmetic.
- **Robust:** long losing streaks are normal at the win rates of breakout and trend methods. They are longer
  still when positions move together.
- **Measured here:** two textbook breakout rules trade one to four times a week and hold for weeks, so an evening
  routine is enough. A pause after three losses lowered total R. Halving size after losses cut drawdowns, usually
  at a small cost in R.
- **Not shown:** that any routine improves returns. Nothing here measures live trading. The template's
  thresholds are common practice, not optimised.
- **Limits:** the illustrative trades use today's listed stocks (so failed companies that were delisted are
  missing), daily bars, no trading costs, and every rule followed perfectly. The simulation assumes independent
  trades. Live trading adds missed fills, hesitation and bent rules. The plan exists to keep that gap small.

## 11. Checklist

- [ ] The plan fits on one page, and I read it before each session
- [ ] Data current (last session loaded, splits adjusted) before any order
- [ ] Market rung set from trend, breadth and volatility
- [ ] Only my setups; each chart checked; results date known
- [ ] Every order sized from the stop; stop placed on fill
- [ ] Heat, position count and group limits checked after new orders
- [ ] Positions record updated; journal written
- [ ] Weekly: calendar, rotation, heat, pruning, trade reviews
- [ ] Monthly: equity vs peak, numbers by setup, compliance, one change at most
- [ ] If-then table followed — and any break of it written down

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — R, expectancy and sizing as the core of a plan.
- Brett N. Steenbarger, *The Daily Trading Coach* — routines and review.
- Mark Douglas, *Trading in the Zone* — rules made in advance over any one outcome.
- Atul Gawande, *The Checklist Manifesto* — why short written checklists work under pressure.
- Mark Minervini, *Think & Trade Like a Champion* — a practitioner's risk, position and exit rules.
- [learn-process-journal.md](learn-process-journal.md) and
  [learn-process-biases.md](learn-process-biases.md) — the next two guides.
