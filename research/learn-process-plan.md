# A trading plan and routine — decide when calm, execute under pressure

Learning material: why a plan is written down, what goes in it, and the
daily, weekly and monthly routine that runs it through this app. This is the
first of three process guides, before [Journaling and review](learn-process-journal.md)
and [Biases](learn-process-biases.md). It links to the guide behind each step.

**Where this shows in the app.** The routine follows the menu: **Today** →
**Markets** (Post-market, Breadth, Sectors) → **Strategies** (Today's setups)
→ **Chart** → **Watchlists**, then **Library → Notes** (templates *Daily
journal*, *Trade plan*, *Trade review*). **System → Schedules** says when the
data refreshes; **System → Status** says whether it has. What the app does
*not* do — orders, positions, P&L — is in §2.

**The data.** The holding periods and the three-losses test (§9) use each
strategy's latest full-history backtest under its current rules:

- US Minervini SEPA with the market filter (2010–2026, 490 trades);
- US Volume breakout (705), US · India Trend pullback (870 · 352),
  US · India Donchian channel (506 · 446), India Chart patterns (516), all 2013–2026.

These are backtests on today's stocks with modelled costs, not live results.

---

## 1. Why write it down

A plan is decisions made **when nothing is at stake**. Then none has to be
made **when everything feels at stake**: a stock gapping through the stop, or
the fourth loss in a row ([biases](learn-process-biases.md)). In those moments
you look up what you already agreed with yourself. A written plan also:

- **makes results measurable** — trades that follow the same rules tell you
  whether the *rules* work ([journal](learn-process-journal.md));
- **caps a bad day** — limits on size, heat (the total you could lose if every
  stop were hit) and drawdown are arithmetic. You cannot redo that arithmetic
  honestly in a panic ([portfolio risk](learn-risk-portfolio.md));
- **gets you through losing streaks** — these strategies win 27–34% of trades,
  so 15–20 losses in a row is normal over a decade ([expectancy](learn-risk-expectancy.md) §4).

**Keep it to one page** (§4): a plan you cannot read in two minutes will not be read.

## 2. What the app does — and what your plan must cover

The app is a research and screening tool. It never sees your broker.

| The app does | Your plan must do |
|---|---|
| Loads prices, breadth, sectors and setups on a schedule (§5) | Check they are current before acting |
| Proposes entry, stop and target per setup; labels TRADE / WATCH | Decide which you take |
| Shows *Risk %* (the stop distance) per setup | Compute the shares ([sizing](learn-risk-sizing.md) §3) |
| Sizes at half risk when the VIX / India VIX is high; demotes its TRADE / WATCH decisions when the market downgrade fires (§3) | Apply that to your own size and exposure |
| Caps a day's tradeable picks at three per sector | Cap what you **hold** per sector and group |
| Lists earnings in the next 10 days; most strategies gate new setups on them | Decide what to do with stocks you already hold |
| — | **Place, change and cancel orders** with your broker |
| — | **Track positions, stops, open risk and P&L** |
| — | Know the macro dates ([calendar](learn-macro-calendar.md)) |

The app has no order entry, no position table, no price alerts and no record
of real trades. It stores watchlists, notes and backtests, not holdings. That
is why the *Daily journal* template has a *Positions* table you fill in by
hand. Write in the plan where your positions are kept, and update that daily.

## 3. What a plan contains

| Part | What to write | Explained in |
|---|---|---|
| **Markets and universe** | US, India or both; minimum price and daily value; what you never trade | The **Screens** page's criteria |
| **Setups** | **One or two** strategies, not all five, and the labels you act on (e.g. TRADE - HIGH CONFIDENCE and TRADE ON TRIGGER) | Each strategy's page under **Strategies**; [bases](learn-bases.md), [VCP](learn-vcp.md), [chart patterns](learn-chart-patterns.md) |
| **Entry** | A buy-stop order (it buys only if the price rises to it) at the setup's entry, placed before the open; how long it stays (Volume breakout and Trend pullback document 10 business days); the chase limit — the most you will pay above the entry (~5%) | The strategy's *Entry rules*; [VCP](learn-vcp.md) §5 |
| **Stop** | The setup's stop under structure, entered as an order on the fill; never lowered; pass on stops wider than ~8% | [Stops and exits](learn-risk-stops-exits.md) §1–3 |
| **Size** | Risk 1% of equity (0.5% when VIX > 25 or India VIX > 20); shares = risk ÷ (entry − stop); no position over 25%; your real equity, not the config's account size (US $50,000, India ₹20 lakh) | [Sizing](learn-risk-sizing.md) §3, [volatility](learn-health-volatility.md) §11 |
| **Exits** | Target, trend exit, or part into strength and the rest on a trend break — chosen before the entry | [Stops and exits](learn-risk-stops-exits.md) §6–10 |
| **Limits** | Heat ≤ 6% of equity; 8–10 positions at most; two or three per industry group; about a third in one sector | [Portfolio risk](learn-risk-portfolio.md) §11, [sectors](learn-sectors-groups.md) §8 |
| **Standing aside** | The exposure ladder below | [Trend](learn-health-trend.md) §8 |
| **Events** | No entry within ~10 trading days of results; for holdings, exit / trim / hold with a cushion, decided per stock; no new full size the day before FOMC, a big CPI, RBI policy, the Budget, an election result | [Calendar](learn-macro-calendar.md) §6, [earnings](learn-fund-earnings.md) |
| **Drawdown** | From the **equity peak**: at −10% halve risk per trade; at −20% stop opening trades and review; restore after recovery, not after a date | [Portfolio risk](learn-risk-portfolio.md) §8 |

**Style and timeframe.** These are swing and position trades on daily bars.
You decide after the close and place orders before the open. How long the
strategies held trades in the backtests (calendar days; "middle half" is the
range covering the middle 50% of trades):

| Strategy (market) | Median hold | Middle half | Trades a year |
|---|---|---|---|
| Minervini SEPA (US) | 20 | 8–47 | 29 |
| Volume breakout (US) | 20 | 8–40 | 52 |
| Trend pullback (US · India) | 23 · 20 | 8–49 · 9–49 | 63 · 26 |
| Chart patterns (India) | 27 | 11–55 | 38 |
| Donchian channel (US · India) | 49 · 60 | 11–134 · 14–164 | 37 · 32 |

That is about **one new trade a week per strategy**, held for weeks. It needs
an evening routine, not a screen watched all day. Write down which holding
style is yours.

**Standing aside — the exposure ladder.** The ladder has three levels
("rungs"), from full exposure to cash. Pick the rung from evidence you can read
in a minute. Move only one rung at a time, and only when two or three warnings
agree (trend, [breadth](learn-health-breadth.md), [volatility](learn-health-volatility.md),
[distribution](learn-health-distribution.md)):

| Rung | Evidence | Exposure |
|---|---|---|
| Full | Index above rising 50- and 200-day; breadth healthy | Normal size and count |
| Reduced | Below the 50-day, the app's downgrade firing, or weak breadth | Half size or half the positions; best setups only |
| Cash / minimal | Below a falling 200-day; 20%+ drawdown | No new entries; manage exits; keep the watchlist |

The app's downgrade fires when both broad indices close below their 50-day
average. It switches on and off often — seven or eight separate spells a year.
So one day of it means "be pickier", not a new rung.

## 4. The one-page template

Copy this into **Library → Notes** (a *Blank note*, tag `plan`, pinned) and
fill in every line. Change it only at the monthly review (§8), never during the
session.

```text
TRADING PLAN — version / date
Markets: US / India.   Universe: ______ (min price, min daily value)
Style: swing/position, daily bars. Decisions after the close; orders before the open.
Setups I trade: ______ (strategies + labels: TRADE - HIGH CONFIDENCE / ON TRIGGER)
  Chart must show: ______ (base, tight area, volume, no supply overhead)
Entry: buy-stop at the setup entry, valid __ days; skip if filled > __% above entry
Stop: setup stop, placed on fill; skip setups with stop > __%; never lowered
Size: risk __% of equity (half if VIX > 25 / India VIX > 20); shares = risk ÷ (entry − stop);
  max __% of equity in one position
Exit: ______ (target / trend exit / partial + trail). Raise stop when ______
Limits: heat ≤ __%; ≤ __ positions; ≤ __ per industry group; ≤ __% in one sector
Market: Full / Reduced / Cash by ______ (index vs 50/200-day, downgrade, breadth)
Events: no entry within __ days of results; holdings into results: ______;
  no new full size the day before FOMC / CPI / RBI / Budget
Drawdown: at −__% from peak halve risk; at −__% stop and review
Losing streak: after __ losses in a row, review the trades before the next one
Where my positions live: ______ (broker / sheet / note) — updated daily
```

## 5. When the numbers are current

The numbers are only as fresh as the last data update the app ran. The default
schedules (**System → Schedules**, `jobs/queue.py`) run on each market's own clock:

| Schedule | When | What it refreshes |
|---|---|---|
| Market close · US | Mon–Fri 18:00 New York | Universe, prices, indexes, breadth, sectors, screens' snapshot, Post-market, every strategy's setups, report |
| Market open · US | Mon–Fri 08:00 New York | Missed prices, earnings dates, news; re-runs stale setups; **readiness** check |
| Market close · India | Mon–Fri 18:30 Kolkata | As the US close |
| Market open · India | Mon–Fri 08:00 Kolkata | As the US open |
| Weekly reference data | Saturday 10:00 (this machine's time) | Universe, names, splits, earnings dates, fundamentals, financials |
| Monthly classification | 1st of the month, 09:00 | Industries, sub-industries, month-end history, group study |

**System → Status** expects a session's data once its close plus a data delay
has passed (17:30 New York, 17:00 Kolkata). It does not know about holidays.
So one session behind is a warning, and two sessions behind is stale.

The **readiness** step fails, and shows red on Status, if the last session's
prices or any strategy's setups are missing before the open. **Today**'s *Data
health* card sums it up: "all current" or "check before trading". Today's
setups also warns when newer prices loaded after the setups ran. **Plan rule:
no order from a setup until Data health says current.** System → Runs shows
when a routine finished.

### Local times

India has no daylight saving time. New York does, from the second Sunday of
March to the first Sunday of November. So US times shift by an hour in Indian
time (IST):

| Event | New York | India (US summer · US winter) |
|---|---|---|
| NSE session | — | 09:15–15:30 |
| India close routine | 09:00 · 08:00 | 18:30 |
| US open routine | 08:00 | 17:30 · 18:30 |
| NYSE / Nasdaq session | 09:30–16:00 | 19:00–01:30 · 20:00–02:30 |
| US close routine | 18:00 | 03:30 · 04:30 (next day) |
| India open routine | 22:30 · 21:30 (previous day) | 08:00 |

## 6. The daily routine, page by page

Start after the close routine has run. It takes about **30–45 minutes** for
one market, less on quiet days.

| # | Page | What to look for | Minutes |
|---|---|---|---|
| 1 | **Today** | Data health current? Each market's tone (*N of 6 signals*); number of tradeable setups; new screener picks | 2 |
| 2 | **Markets → Post-market** | The six tone signals; *Sectors today*; *Group leadership changes*; *Unusual volume — up*; *New 52-week highs*; **Your watchlists** (your stocks' moves, 50-day crosses); **Earnings in the next 10 days**; *Screener changes* | 5–8 |
| 3 | **Markets → Breadth** | The six cards against history; *What changed in the last 5 sessions*; decide the exposure rung (§3) | 3 |
| 4 | **Markets → Sectors** | Leading sectors and industry groups; anything new in *Improving*; your holdings' groups slipping to *Weakening* | 3–5 |
| 5 | **Strategies → Today's setups** | Only your strategies and labels; the regime note (downgrade?); risk % ≤ your limit | 5–10 |
| 6 | **Chart** (each candidate) | The base and the tight area; stop under structure; overhead supply; results date in *News & events*; Fundamentals tab if your plan uses it | 2–3 each |
| 7 | **Watchlists** | *Screener picks* (entry, to entry %, stop, target R); move the ones you want onto your own list with a note; remove stale names | 5 |
| 8 | Outside the app | Size each order; place buy-stops and stops with the broker; update positions | 5–10 |
| 9 | **Library → Notes** | *Daily journal* note: market, positions, watching, lessons | 3 |

Then stop. Reading more after the plan is set only reopens a decision you made
calmly.

### US and India, by where you live

- **US from New York:** do the review after the 18:00 close routine. Check
  again at ~09:00, after the open routine, before orders go live at 09:30.
- **India from India:** do the review after the 18:30 close routine. Check
  again at ~09:00 IST, before the NSE opens at 09:15.
- **Both, from India:** the US close routine ends in the early hours IST. So
  the US review fits the **IST morning**, beside India's pre-open check, with
  US orders in before 19:00 / 20:00 IST. India's review is in the IST evening.

## 7. Pre-market against after-close work

**After the close** is when the real work happens: reading the market,
choosing setups, checking charts, sizing, writing orders and stops, and the
journal.

**Before the open** is a few minutes of checking, once the open routine has
refreshed prices, earnings dates and news:

- Did readiness pass (Today → Data health)?
- Is there anything in *News & events* for an order or a holding?
- Has a results date moved inside ten days?

Cancel an order if the reason for it no longer holds. **Decide in the evening,
verify in the morning, never re-decide.** The morning may cancel or shrink a
trade. It may never add a trade the evening did not choose.

## 8. Weekly and monthly

### Weekly — about 30–45 minutes, at the weekend

1. **The week's calendar** — FOMC, CPI, jobs, RBI, India CPI, expiries, and
   your holdings' and watchlist's results; write the decision for each in
   Notes before Monday ([calendar](learn-macro-calendar.md) §8).
2. **Rotation** — Markets → Sectors, industry groups: the top 15–20 by
   relative strength (RS), the biggest one-month changes (the *Δ 1M* column),
   and the quadrants ([sectors](learn-sectors-groups.md) §8).
3. **Market rung** for next week — the weekly close against the 30-week
   average, and breadth over the week.
4. **Heat and concentration** — the sum over positions of (lower of price and
   cost − stop) × shares, divided by equity; and positions per group
   ([portfolio risk](learn-risk-portfolio.md) §13).
5. **Prune the watchlists** — remove names that broke their base, lost the
   50-day or sit in a lagging group. Keep each list short enough to chart in
   one sitting.
6. **Review the week's closed trades** against the plan, with the *Trade
   review* template ([journal](learn-process-journal.md)).

### Monthly — about an hour

- **Equity against its peak** — does the drawdown rule change size?
- **Numbers by setup** — win rate, average win and loss in R, expectancy;
  meaningful after 30–50 trades per setup ([expectancy](learn-risk-expectancy.md) §5).
- **Against the backtest** (each strategy's **Backtests** tab) — an average
  loss worse than −1R means stops were moved or positions were held through
  results. A much lower win rate means the trades you took are not the ones
  the rules select.
- **Compliance** — what share of trades followed every rule
  ([biases](learn-process-biases.md))?
- **Change the plan only here**, one rule at a time. Write the date and reason
  in the plan note — as the app does with each strategy's version number and
  changelog.

## 9. If-then rules

Decide these now; look them up then.

| Situation | Rule |
|---|---|
| A stock **gaps below the stop** at the open | Exit at the market — the stop's job is done; do not wait for a bounce. Log the R (about one stop in twelve gaps, averaging −1.5R: [stops](learn-risk-stops-exits.md) §5) |
| A stock **gaps far above the entry** | Skip it if the fill would be more than your chase limit above entry; the risk to the stop is now larger than planned |
| **Results tomorrow** for a holding | Do what the weekly note decided: exit, trim, or hold only with a cushion big enough to survive a gap of twice the stop |
| **Results within 10 days** for a new setup | No entry; put it on the watchlist for after the report |
| The **downgrade fires** / market moves down a rung | No new breakouts at full size; tighten stops on laggards; keep the watchlist |
| **VIX above 25 / India VIX above 20** | Half risk per trade (the app's sizing already does); fewer new positions |
| **Three losses in a row** | Review the three trades against the plan before the next one (see below) |
| **Drawdown −10% / −20%** from the peak | Halve risk / stop new trades and review |
| Heat at the limit | No new trade until a stop is raised or a position closes |
| **Data health not current** | No new orders from the setups until it is |
| A **big macro event** tomorrow | No new full-size entry today; enter after the reaction if the setup holds |

### Three losses in a row — what the backtests say

Method: for each run above, the trades are put in order of exit. A "trigger"
is the third losing exit in a row. Two rules were tested as simulations,
adding up R without compounding:

- **skip** every entry in the seven days after a trigger;
- **halve** risk on any entry while the last three exits known by then were
  losses, until a winner.

Results:

- **It is frequent**: 2.5 to 5.7 triggers a year per strategy.
- **The streak did not predict the next trade.** Trades entered in the week
  after a trigger did better than the rest in four runs and worse in three.
  Each comparison rested on 26–118 trades, so this is noise.
- **Skipping a week** changed total R by anywhere from −14R (US Volume breakout,
  +29.8R → +15.8R) to +38R (US Trend pullback, −3.2R → +34.7R). There was no
  consistent effect.
- **Halving until a winner** cut the worst R drawdown in all seven runs (US
  Donchian −86R → −70R, India Chart patterns −37.5R → −25.8R). It also lowered
  total R in all seven. It hurt the trend followers badly (US Donchian +249R →
  +155R, India Donchian +208R → +108R). Their trades right after a losing
  streak were their biggest winners, because a losing run ends when a trend starts.

So **three losses trigger a review, not a pause**. Was each one a plan trade:
stop placed, size right, no results held through, rung respected? If so, take
the next setup at normal size. Size is cut by the **drawdown** rule (§3),
which reacts to how much was lost, not to how many trades lost it.

## 10. What the evidence says

- **Robust:** rules fixed in advance hold up better under stress than
  judgement on the spot. That is the case for checklists (Gawande), and the
  theme of every trading author below. Fixed-fractional risk and drawdown
  limits are arithmetic.
- **Measured here:** the strategies trade about once a week each and hold for
  weeks, so an evening routine is enough. A three-loss pause had no consistent
  effect. Halving size cut drawdowns, at a real cost to the trend followers.
- **Not shown:** that any routine improves returns. Nothing here measures
  live trading, and the template's thresholds are common practice, not optimised.
- **Caveats:** backtests on today's stocks, modelled costs, no earnings rule,
  and every rule followed perfectly. Live trading adds missed fills, hesitation
  and bent rules. The plan exists to keep that gap small.

## 11. Checklist

- [ ] The plan fits on one page and is pinned in Notes; I read it before each session
- [ ] Data health current (Today / System → Status) before any order
- [ ] Market rung set from trend, breadth and volatility
- [ ] Only my strategies and labels; each chart checked; results date known
- [ ] Every order sized from the stop; stop placed on fill
- [ ] Heat, position count and group limits checked after new orders
- [ ] Positions updated outside the app; journal written
- [ ] Weekly: calendar, rotation, heat, pruning, trade reviews
- [ ] Monthly: equity vs peak, numbers by setup vs backtest, compliance, one change at most
- [ ] If-then table followed — and any break of it written down

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — R, expectancy and sizing as the core of a plan.
- Brett N. Steenbarger, *The Daily Trading Coach* — routines and review.
- Mark Douglas, *Trading in the Zone* — rules made in advance over any one outcome.
- Atul Gawande, *The Checklist Manifesto* — why short written checklists work under pressure.
- Mark Minervini, *Think & Trade Like a Champion* — a practitioner's risk, position and exit rules.
- [learn-process-journal.md](learn-process-journal.md) and
  [learn-process-biases.md](learn-process-biases.md) — the next two guides.
