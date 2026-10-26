# Using the app — its pages, and what each shows

**In short**

- The menu has eight sections: **Today**, **Markets**, **Screens**, **Strategies**, **Chart**,
  **Watchlists**, **Library** and **System**. Alt+1 … Alt+8 jumps to each; ⌘K searches pages and symbols.
- The app screens and backtests. It never places an order, and it does not know your positions or P&L.
- Read it in menu order after the close: Today → Post-market → Breadth → Sectors → Strategies → Chart →
  Watchlists → Notes. That takes 30–45 minutes for one market.
- Every page answers one question. The Learn guide linked beside each page explains the idea behind it.
- The exact formulas and thresholds are in
  [how the app computes its numbers](app-guide-how-it-computes.md).

This is the manual for the screens of the app. It says what each page shows, how to read each card and
column, and which [Learn](learn-start-here.md) guide covers the idea. Three companion guides go deeper:
[reading backtests and screen studies](app-guide-backtests.md),
[screens versus strategies](app-guide-screens-strategies.md) and
[the strategy families](app-guide-strategy-families.md).

Most pages have a **market selector** in the header (US or India). The markets come from the app's
config, so a page always shows the market you picked last.

---

## 1. The menu at a glance

| Section | Pages | The question it answers | Idea behind it |
|---|---|---|---|
| **Today** | Today | Is the data current, how did the market close, and what can I trade? | [Trading plan](learn-process-plan.md) |
| **Markets** | Post-market · Breadth · Sectors · Movers | How healthy is the market, and where is the strength? | [Breadth](learn-health-breadth.md), [sectors](learn-sectors-groups.md) |
| **Screens** | Screens (and Quality companies) | Which stocks qualify? | [Stages](learn-price-stages.md), [system filters](learn-system-filters.md) |
| **Strategies** | Today's setups · one page per strategy | Is there a trade, at what price, with what stop? | [Strategies overview](learn-strat-overview.md) |
| **Chart** | Chart · Fundamentals · News | What does this one stock look like? | [Indicators](learn-price-indicators.md), [earnings](learn-fund-earnings.md) |
| **Watchlists** | Watchlists | What am I following, and what did the screener pick? | [Journal](learn-process-journal.md) |
| **Library** | Notes · Research · Learn | My notes and journal; reference reading | [Journal](learn-process-journal.md) |
| **System** | Status · Runs · Schedules · Reports archive · Sub-industries · TODO | Is the data current, and what did the jobs do? | — |

## 2. Today

Today is the starting page. It answers four questions for the market chosen in the header.

| Part | What it shows | How to read it |
|---|---|---|
| **Data health** banner | "Data current" (prices, breadth and the screens are up to date) or "Data health — check before trading" with a list of issues | Any issue — a stale dataset, a stopped job worker, a run that failed in the last 24 hours — means no orders from today's setups until it is fixed |
| **Market** card | The post-market tone label, "N of 6 signals", rising and falling stocks, and the first two Breadth readings against history since 2015 | The label is a count of six yes/no signals (§3.1). It describes the day, not the trend |
| **Macro** card and tiles | A rule-based read of rates, the dollar, oil, credit, growth and fear: each signal supportive or a headwind, and a label from Supportive to Hostile | Background, not a trade signal. See [rates](learn-macro-rates.md), [currencies](learn-macro-currencies.md), [credit](learn-macro-liquidity-credit.md) |
| **Today's setups** | The tradeable setups of every strategy, HIGH CONFIDENCE first: peer group, group RS, decision, setup, price, entry, stop, Risk %, Target R | A chip per strategy gives its count of tradeable names. A warning appears if newer prices loaded after the setups ran |
| **Screener picks** | Stocks added to the Screener picks list in the latest run | New names to look at, not trades |

## 3. Markets

### 3.1 Post-market

The day's recap, kept for every past day (pick a date to re-read one). It has four tabs.

**Summary.** The **tone** label (Strong, Positive, Mixed, Weak or Negative) and the six signals, each
marked bullish or bearish:

| Signal | Bullish when |
|---|---|
| Benchmark vs its 50-day | The S&P 500 (Nifty 50) closed above its 50-day average |
| Benchmark vs its 200-day | It closed above its 200-day average |
| Advancers vs decliners | More stocks rose than fell |
| Highs vs lows | More new 52-week highs than lows |
| Above the 50-day | Half or more of stocks above their 50-day average |
| Volatility index | VIX (India VIX) fell on the day |

Below them: index tiles (above or below the 50- and 200-day, distance from the 52-week high), a
**Breadth** table (today, the previous day and the 10-day average), and **Sectors today**. A base-rate
line says how many of the recent sessions scored as high (or as low).

**Sectors.** *Strongest industries* and *Weakest industries* on the day, and **Group leadership
changes**: groups whose RS rating rose or fell over the last few sessions, and groups that changed
rotation quadrant since the day before. See [sectors and groups](learn-sectors-groups.md).

**Stocks.** *Top gainers*, *Top losers*, *Unusual volume — up / down* (at least 2.5× the 50-day average
volume and a move of 2% or more), *New 52-week highs* and *New 52-week lows*. These lists use liquid
stocks only. See [volume](learn-price-volume.md).

**Your lists.** **Your watchlists** lists every stock on your lists and in Screener picks, biggest moves
first, with flags: crossed above or fell below the 50-day, new 52-week high or low, heavy buying or
selling, earnings soon. **Screener changes** shows each strategy's names added and dropped since the
previous run. **Earnings in the next 10 days** lists watched and screened stocks that report soon. See
[the calendar guide](learn-macro-calendar.md).

### 3.2 Breadth

"How healthy is the market — risk, not direction." Breadth is built from the 1,000 most-traded common
stocks each day. Each card shows today's value, a gauge ranking it against every trading day since 2015
("Only N in 100 days since 2015 were…"), and a table against one week, one month and three months ago.
See [breadth](learn-health-breadth.md).

| Card | What it shows | How to read it |
|---|---|---|
| **S&P 500 against its 50 DMA?** (Nifty 50 for India) | The index's % distance from its 50-day | The index's own short-term trend: the context. See [trend](learn-health-trend.md) |
| **Stocks at a 52w high or low?** | New highs and lows, and the typical day over two weeks | Leadership against damage, ranked on the 10-day average of highs minus lows |
| **Stocks above their 5 & 50 DMA?** | % above the 5- and 50-day averages | 50-day: the average stock's trend. 5-day: short-term stretch |
| **Stocks rising or falling?** | Advancers and decliners, and the two-week typical day | Participation, ranked on the 10-day average of rising minus falling |
| **Leading sectors, last 3 months?** | Best and worst sector against the average stock; how many sectors have most stocks above the 50-day | Where the strength is, and how widely it is shared |
| **Options: expected vs actual?** | VIX (India VIX) against the index's realised volatility over 20 sessions | A ratio well above 1 means options are dear. See [volatility](learn-health-volatility.md) |

Above the cards is the **macro strip**: a row of tiles with the last close, the 1-day and 1-month change
(basis points for yields) and a 3-month sparkline. Hover a tile for why it matters.

| Market | Tiles |
|---|---|
| US | US 10Y yield, US 5Y yield, Dollar index, WTI crude, Gold, Copper, HY credit (HYG) |
| India | Brent crude, USD/INR, US 10Y yield, Dollar index, Gold |

The India strip carries US series on purpose: they drive foreign money into and out of India. See
[yield curve](learn-macro-yield-curve.md), [commodities](learn-macro-commodities.md),
[inflation](learn-macro-inflation.md).

Below the cards:

- **What changed in the last 5 sessions**: the share above the 50-day crossing 30% (washout) or rising
  above 70% (broad strength); highs-minus-lows or rising-minus-falling at a 90-day extreme; the index
  crossing its 50-day.
- **Charts** (6M, 1Y, 3Y, All): the two main indexes, highs minus lows, stocks above the 50-day with lines
  at 30% and 70%, and rising minus falling.
- **Sectors: where the strength is?** — each sector's stocks, 3- and 1-month change against the average
  stock, % above the 50-day, and highs and lows over two weeks. Click a sector for its stocks.
- **The last 30 days**: every reading by day, with the indexes and the options numbers. Green shading marks
  a reading in its strongest fifth since 2015; red, its weakest fifth.

### 3.3 Sectors

Leading sectors, industry groups and their leaders. Pick the level: **Sectors**, **Industry groups**,
**Sub-industries** or **Themes**. Everything is recomputed daily from stored prices. See
[sectors and groups](learn-sectors-groups.md) and [the cycle](learn-macro-cycle.md).

| Column or part | Meaning |
|---|---|
| **RS** | The group's RS rating, 1–99, ranked against the other groups. 99 is the strongest |
| **Δ 1M** | Change in the rating over 21 trading days. A 20–30 point jump often marks a group coming into favour |
| **Stocks** | Liquid members counted |
| Returns 1W … 12M | Equal-weight returns; tick *Returns vs the typical stock* to see them relative to the average stock |
| **> 50D**, **> 200D** | % of members above their 50- and 200-day averages |
| **Highs / lows** | Members at a new 52-week closing high or low |
| **Rotation** | Quadrant: Leading, Weakening, Lagging or Improving |
| **RS line 6M** | The group's index divided by the typical stock's, over six months |
| **Leaders** | The group's strongest members by RS |

The **Rotation** graph plots the groups at the top of the table, with an 8-week tail. The quadrant chips
filter the table to one quadrant. Groups tend to move clockwise: Improving → Leading → Weakening →
Lagging. A sell-off can drop one straight from Leading to Lagging.

Click a group for its own page: *Group vs the typical stock* (with its RS line), *Returns* (equal-weight
beside cap-weight), *Breadth*, its sub-groups, and *Members, strongest first*. **Add top 10 to a
watchlist…** copies the leaders to a list. Cap-weight far above equal-weight means a few giants carry the
group.


**Themes** are your own baskets of stocks that share an investment story across industry groups (AI
infrastructure; India railways, defence, capital markets, power & grid capex are the starters, as drafts to
edit). Each market has its own, since an equal-weight index cannot mix currencies. A theme is tracked like a
group — equal-weight index, breadth, rotation, leaders — but its **RS** is placed on the industry groups'
1–99 scale (a theme rated 85 is as strong as an industry group rated 85), because ranking a handful of
themes against each other would say little. **New theme…** creates one; its page carries:

| Part | Meaning |
|---|---|
| Status | watching / confirmed / active / closed, with the date it last changed |
| **Confirmation and invalidation** | The sector playbook's checks on today's numbers: RS above 70 and rising, Improving or Leading, breadth broadening; and the invalidation signal, RS below 40 or Lagging (`THEME_CONFIRM_RS` / `THEME_INVALID_RS` in analytics/sectors.py) |
| **RS rating over time** | Weekly, rebuilt from stored prices for three years by the daily `sectors` job. A stock counts only from the day it was added; before the first member was added, today's members stand in, drawn faded (hindsight) |
| **Thesis log** | The playbook's §3.2 template: thesis, evidence for and against, invalidation, notes |
| **Members** | Add symbols (India's `.NS` is optional); × removes one, keeping its past membership. Members below the liquidity floor are listed but not in the index. Changing members clears the stored history, which the next `sectors` run rebuilds |

Stored in `themes` and `theme_members` (marketdata/themes.py).
### 3.4 Movers

Top gainers and losers over 1D, 1W, 1M, 3M, 6M, YTD or 1Y, among liquid stocks or all stocks. Columns:
group and its RS, last price, change, **Rel vol** (the last day's volume ÷ its 50-day average) and traded
value. The header shows advancing and declining stocks over the period, and the benchmark's change.

## 4. Screens

A screen only says which stocks qualify. It has no entry, stop or decision. See
[screens versus strategies](app-guide-screens-strategies.md).

| Built-in screen | Asks | Strategy that draws from it |
|---|---|---|
| **Stage 2 — Trend Template** | Minervini's eight conditions (C1–C8), including RS rank 70+ | Minervini SEPA |
| **Established uptrend** | Weekly and daily trend in order, near highs, not fading (U1–U8) | Trend pullback |
| **Near highs, rising 200-day** | Above a 200-day that is not falling, within 15% of the 52-week high (H1–H3) | Volume breakout, Chart patterns |
| **Above the 200-day** | The long-term trend filter alone (A1) | Donchian channel |

Two presets have no strategy behind them: **Strong stocks in leading groups** (RS 70+ in a peer group
rated 80+, above the 50- and 200-day) and **Minervini leaders in Stage 2** (Stage 2 plus a SEPA verdict of
LEADER). **+ New screen** builds your own from the
snapshot's ~60 fields; editing a built-in saves a copy of your own.

**Quality companies** is the long-term tracker. Each company gets a quality score out of 100 (70+ with no
red flag counts as high quality), the Piotroski F-score, returns on capital, growth, margins, cash
conversion and debt. Each close then values it (FCF yield, P/E against its own median, PEG) and sorts it
into **BUY ZONE**, **ACCUMULATE** or **WAIT**. Chips show *Tracked*, *Buy zone*, *At your price*,
*Accumulate*, *High quality* and *All scored*. **Track a company** adds one, with an optional buy-below
price that flags the row AT YOUR PRICE. See [quality](learn-fund-quality.md) and
[valuation](learn-fund-valuation.md).

Each screen has two tabs:

- **Results**: the qualifying stocks, sorted by RS rank unless you choose otherwise. The rules are listed
  above the table ("every condition must hold").
- **Study**: how the screen's stocks did over the next 1, 3 and 6 months, from five years of month-end
  snapshots. How to read it is in [reading backtests and screen studies](app-guide-backtests.md) §7.

The ideas: [stages and the Trend Template](learn-price-stages.md), [relative strength](learn-price-rs.md),
[bases](learn-bases.md).

## 5. Strategies

A strategy draws candidates from one screen and adds the trade: setup, entry, stop, target, exits and
size. The sidebar groups strategies by market behaviour and by how candidates are selected.

**Today's setups** lists every strategy's tradeable and watch names for the chosen market.

Each strategy's own page has three tabs:

| Tab | What it shows |
|---|---|
| **Setups today** | The latest run: every stock the screen passed, with its decision. Chips filter *Tradeable*, *Watch* or *All*; a select picks one exact decision. **Run this strategy…** queues a fresh run |
| **Rules** | Generated from the strategy's code: thesis, gates, warning flags, setups, entry and exit rules, parameters, the regime note, the changelog and the commands |
| **Backtests** | Every stored run, grouped by version. Runs from an older version are marked as not reflecting the current rules |

**The decision labels**, from best to worst:

| Label | Meaning |
|---|---|
| **TRADE - HIGH CONFIDENCE** | The setup's entry signal has fired and every quality check passed |
| **TRADE ON TRIGGER** | Valid plan; place the buy-stop and let the price trigger it |
| **WATCH - WAIT** | Not now: extended, stop too wide, target under 2R, earnings close, too large for the account… the *Reason* column says which |
| **WATCH - SECTOR LIMIT** | A tradeable name demoted because three better ones in its sector came first |
| **AVOID** | Failed a hard gate, or no valid plan |

Default columns of *Setups today*: symbol, name, peer group, group RS, decision, setup, price, **Entry**,
**Stop**, **Risk %** (the stop's distance below the entry), **Target R**. The **Columns** menu adds about
40 more, among them *Reason*, *Wait for*, *First failed gate*, *RS vs index*, *RS vs sector*, *RSI*,
*ADX*, *Earnings in (d)*, *Demand / supply*, *Nearest overhead*, *Shares*, *Position value* and the amount
at risk. When the market downgrade is active, the regime note on the Rules tab says how the decision was
lowered.

Backtest results live on the Backtests tab and in System → Reports archive, not in this manual. How to read
them: [reading backtests](app-guide-backtests.md) and [backtesting honestly](learn-test-backtesting.md).

## 6. Chart, Fundamentals and News

**Chart.** Candles with daily, weekly or monthly bars. **Indicators** opens a searchable picker of 35
studies, computed in the browser from the bars on screen; your list is saved and applies to every symbol.
On first use the chart shows the 20-, 50- and 200-day SMA, Volume and RSI. Two studies are not
indicators: **Screener levels** draws a strategy's entry, stop and target, and **Chart patterns (live
detection)** runs the chart-pattern detectors on stored prices. **Support & Resistance (zones)** is computed
on the server (`core/sr_levels.py`, `/api/sr-levels`): weekly zones first, then daily (monthly then weekly on a
weekly chart); turning points that drew a clear reaction, clustered (reactions spread over more than 1 ATR are
separate levels) into zones drawn from the structure — wick extremes to the body cluster, never stretched or
trimmed to an ATR band; a lone wick standing apart from the cluster neither sets an edge nor counts as a touch
(evenly spread turns have none). A weekly zone takes its edges, touches and start from the daily turns inside it
over its own five-year look-back; a daily zone at least half inside a weekly one is left to it, one that merely
overlaps it is kept; and two same-role zones less than half an ATR apart become one zone with both reference levels. Touches are distinct visits (price must close half an ATR outside the
zone before another counts). Each zone carries its height ÷ the ATR of its own timeframe ("wide" above 1.5), its
grade on seven factors (kept at 3+), its role ("Support (was resistance)") and "worn" at five or more visits; zones
crossed repeatedly are dropped. Key levels are chosen proximity-first, not by quota: within 8 / 6 / 5 ATR of price
(daily / weekly / monthly chart), scoring 4+ (a daily zone also needs two visits) — the nearest each side, then the
best of the rest, up to 7 in all and 4 a side; a side may show none. If price is more than 3 ATR from its nearest
key zone, the nearest graded zone in that gap is promoted (on a weekly or monthly chart it may come from the
timeframe below), or the next round number is marked. Same-role zones that overlap become one zone (the coarser
timeframe's, each visit counted once) before key levels are chosen, unless that zone would be taller than one ATR,
when the better is kept; a zone still taller than one ATR of its own timeframe is cut back to its body side,
keeping only the visits that came to it. The 52-week high and low (and the all-time high / low near
price) are always marked as provisional levels, since a fresh extreme has no confirmed swing yet. Long-term levels —
weekly or monthly zones beyond that window whose three or more reactions span 1.5+ years, within half to double
the price — are drawn as muted bands with a "Long-term …" axis tag (up to three a side). The setting "All
graded levels" also draws the other graded zones as thin dashed outlines (off by default). The measurement behind all of
this is `python -m swing_screener.analytics.level_study` (zones vs a same-geometry placebo); `python -m
tests.test_sr_levels` checks the drawing against a golden set of hand-labelled charts and rules every chart must
obey. Labels sit on the price axis by default ("Axis only"); Short adds an in-chart tag ("Support · weekly"), Full
adds grade, visits and height. Price inside a zone, or within a quarter of a daily ATR of it, makes it a pivot ("Pivot — price inside" /
"At price"); a zone price has closed inside on 30%+ of bars is labelled a congestion zone. A higher-timeframe
box price keeps crossing is redrawn as the daily clusters inside it that still hold, and — if price has lived in
it — drawn as a grey **congestion band** (context, not a level). Earnings within 10 sessions add a warning to the
legend. The previous week's and month's high and low are off by default (setting "Previous periods"). **Supply & Demand Zones** is computed on the
server too (`core/sd_zones.py`, `/api/sd-zones`), on daily or weekly bars: the base each decisive move left
from, its proximal (body) and distal (wick) edges, extended right until a close through the distal edge,
with its retests numbered. By default it shows the active zones nearest the last close; the **Zones** panel
lists every zone with its quality checklist. See
[indicators](learn-price-indicators.md), [momentum indicators](learn-price-oscillators.md),
[chart patterns](learn-chart-patterns.md) and [supply and demand](learn-supply-demand.md).

Drawings (trend lines, horizontal lines, rectangles, Fibonacci and more) are saved on the server per
symbol. Shortcuts: Alt+T trend line, Alt+H horizontal line, Alt+Shift+R rectangle; ⌘Z undoes.

Markers along the bottom show **E** (earnings or results) and **D** (ex-dividend); upcoming ones sit to the
right of the last bar. A past **E** is green when the company beat the analyst consensus, red when it missed
(by EPS growth where no consensus is stored), and its card shows reported EPS against the consensus. The
upcoming **E** card shows the consensus for the quarter being reported: its range and analyst count, growth
against the year-ago quarter, the **estimate trend** (the consensus now against 30 and 90 days ago — raised
estimates into a report tend to precede a beat), upward and downward revisions over 30 days, the revenue
consensus and the beat record (`marketdata/estimates.py`). The right-hand rail opens panels:

| Panel | Contents |
|---|---|
| Watchlist | Your watchlists; a second icon holds the list you opened the chart from (a screen's results, today's setups), to step through it |
| **Symbol details** | Sector › industry group › sub-industry (each a link); *Quarterly fundamentals* (latest EPS and sales growth, ROE, SEPA verdict, Code 33); *Fundamentals* from the Quality tracker; *Screener — latest* (each strategy's plan); *Decision history*; your linked notes with **+ note** |
| **News & events** | Headlines, filings and exchange announcements; earnings dates, dividends, splits, analyst ratings |
| **Backtest trades** | A stored run's buys and exits in this symbol; click one to zoom to it |
| **Chart patterns** / **Zones** | Shown while that indicator is on: every pattern / supply-demand zone found; click one to go to it |

**Fundamentals** (Chart → Fundamentals) is one company's financials in tabs: Overview, Quarters, Profit &
Loss, Balance Sheet, Cash Flows, Ratios, Shareholding (India: promoters, FIIs, DIIs, public) and Peers, plus
**Analyst estimates**: EPS and revenue consensus for this and next quarter and fiscal year (range, analysts,
growth against a year ago, the 30- and 90-day trend, revisions, and "since first stored" once the weekly
snapshots reach past Yahoo's 90 days), a one-line read, and the earnings surprise record (consensus against
reported, beat or miss). Analysts' EPS is often adjusted, so it can differ from the filed EPS above; company
guidance is not included (no free source carries it as numbers). It
includes a **Minervini SEPA** section (tests F1–F8 and a verdict) and a **CAN SLIM** section (`fundamentals/canslim.py`):
C1–C2 and A1–A2 from the filings, then N (within 15% of the 52-week high), S (up-day over down-day volume, 50
sessions), L (RS rank 80+), I (FII + DII up on the quarter; India only) and M (the index above its 50-day with at
most 4 distribution days in 25 sessions), judged live — verdict QUALIFIES, EARNINGS PASS (wait for the stock or the
market), WEAK or NO DATA. See [earnings](learn-fund-earnings.md),
[quality](learn-fund-quality.md) and [valuation](learn-fund-valuation.md). Sales, operating profit, net profit and EPS each carry a **growth row** beneath them, green up / red down, in words ("turned profit", "loss narrowed / widened") where the earlier period was a loss. The Quarters table has a **Growth** switch beside its title: **YoY + QoQ** (the default, both rows under each line), **YoY** (each quarter against the same quarter a year earlier, free of seasonal swings), **QoQ** (against the quarter before: sooner, but partly the season) or **Off**. The table opens on the last three years; **◀ Earlier** / **Later ▶** step a year at a time through the older quarters stored (US filings back to 2009, India from 2021) and **Latest** returns. The Profit & Loss table shows year-on-year growth, its TTM column against the twelve months before.

**News** is the same News & events feed on a full page.

## 7. Watchlists

Your own lists keep a **note** per stock. The **Screener picks** list fills itself after each strategy
run: every stock a strategy marks tradeable or on watch. Its columns are strategy, decision, entry, **to
entry %** (how far the price is from the entry), stop, target R, peer group and group RS. Removing a pick
hides it until it drops off the screen and is flagged again. Its **CAN SLIM** column is the Fundamentals page's CAN SLIM verdict for each pick (QUALIFIES / EARNINGS PASS / WEAK / NO DATA; blank where no fundamentals are stored); for EARNINGS PASS it adds the letters still failing — "wait: M" means the earnings qualify and the market does not.

Watchlists hold symbols, notes and the planned levels. They do not hold positions.

## 8. Library

**Notes** is your notes and trading journal. A note has a title, a Markdown body (rich or plain editor;
tables and checklists work), tags, linked stocks and a pin. It saves as you type. Search covers title,
body, tags and linked stocks; tags show as filter buttons. The Chart's Symbol details panel lists the notes
linked to the stock. **Copy as Markdown** exports one note;
`python -m swing_screener.notes --export <dir>` exports all.

**Research** lists the research notes and these app guides. **Learn** holds the learning guides, the
pattern catalogue and the glossary.

## 9. System

| Page | What it shows |
|---|---|
| **Status** | The **Job queue** (worker running or stopped, its lanes, running and waiting jobs) and, per market, every dataset with its date and a badge: ok, warn (one trading day behind — a holiday or a run not done yet) or stale. Daily datasets (prices, breadth, indices, the stock snapshot, sector ranking, post-market, fund NAVs, FII/DII flows, F&O) are checked against the trading day they should have reached; slower ones (rates, universe, names, industries, quality, earnings dates) by age; and economic indicators, news, company financials and FPI-by-sector — whose own dates cannot show it — by when their job last succeeded, with a warning when its latest run failed |
| **Runs** | Every run, its steps and log; a failed run can be resumed |
| **Schedules** | When each routine runs, with **run now** |
| **Reports archive** | Every backtest and screening report. A run opens with tabs *Report*, *Funnel* (backtests), *Equity curve* and *Trades* |
| **Sub-industries** | Which sub-industry each company belongs to; review and edit. **Needs review** lists groups with unassigned or suggested labels, **My stocks** the groups holding a stock on any of your watchlists (★). Each row shows its traded value a day, and unreviewed stocks come first |
| **TODO** | Ideas and follow-ups |

The default schedules run on each market's own clock:

| Schedule | When | What it refreshes |
|---|---|---|
| Market close · US | Mon–Fri 18:00 New York | Universe, prices, indexes, breadth, sectors, the screens' snapshot, Post-market, every strategy's setups, the report |
| Market open · US | Mon–Fri 08:00 New York | Missed prices, earnings dates, news; re-runs stale setups; the **readiness** check |
| Market close · India | Mon–Fri 18:30 Kolkata | As the US close |
| Market open · India | Mon–Fri 08:00 Kolkata | As the US open |
| Weekly reference data | Saturday 10:00 | Universe, names, fund labels, splits, earnings dates, fundamentals, company financials and their scores |
| Monthly classification | 1st of the month, 09:00 | Industries, sub-industries, month-end snapshot history, the group-strength study |

The readiness step fails, and shows red, when the last session's prices or any strategy's setups are
missing before the open.

## 10. What the app does not do

| The app does | Your plan must do |
|---|---|
| Loads prices, breadth, sectors and setups on a schedule | Check Data health before acting |
| Proposes entry, stop and target per setup, and a decision label | Decide which you take |
| Sizes each row from its stop (1% risk, half when volatility is high, 25% cap) | Size from **your** equity, not the configured account |
| Lowers decisions when the market downgrade fires | Set your own exposure |
| Caps a day's tradeable picks at three per sector | Cap what you **hold** per sector and group |
| Lists earnings in the next 10 days; most strategies gate setups on them | Decide what to do with stocks you already hold |
| — | Place, change and cancel orders with your broker |
| — | Track positions, stops, open risk and P&L |
| — | Watch macro dates ([calendar](learn-macro-calendar.md)) |

There is no order entry, no position table, no price alert and no record of real trades. The *Daily
journal* template has a *Positions* table you fill in by hand. See [portfolio risk](learn-risk-portfolio.md).

## 11. The daily routine, page by page

Start after the close routine has run. **Plan rule: no order from a setup until Data health says
current.**

| # | Page | What to look for | Minutes |
|---|---|---|---|
| 1 | **Today** | Data health; the market's tone; number of tradeable setups; new screener picks | 2 |
| 2 | **Markets → Post-market** | The six signals; *Sectors today*; *Group leadership changes*; *Unusual volume — up*; new highs; *Your watchlists*; *Earnings in the next 10 days*; *Screener changes* | 5–8 |
| 3 | **Markets → Breadth** | The cards against history; *What changed in the last 5 sessions*; decide how much exposure | 3 |
| 4 | **Markets → Sectors** | Leading groups; anything new in Improving; your holdings' groups slipping to Weakening | 3–5 |
| 5 | **Strategies → Today's setups** | Only your strategies and labels; the downgrade; Risk % within your limit | 5–10 |
| 6 | **Chart**, each candidate | The base and its tight area; stop under structure; overhead supply; the results date; Fundamentals if your plan uses it | 2–3 each |
| 7 | **Watchlists** | Screener picks: entry, to entry %, stop, target R; move the ones you want to your own list with a note | 5 |
| 8 | Outside the app | Size each order; place buy-stops and stops with the broker; update positions | 5–10 |
| 9 | **Library → Notes** | A *Daily journal* note | 3 |

**Before the open**, once the open routine has run: did readiness pass, is there news on an order or a
holding, has a results date moved inside ten days? The morning may cancel or shrink a trade. It never adds
one the evening did not choose. See [a trading plan and routine](learn-process-plan.md).

**Local times.** India has no daylight saving; New York does (second Sunday of March to first Sunday of
November), so US times move by an hour in IST.

| Event | New York | India (US summer · US winter) |
|---|---|---|
| NSE session | — | 09:15–15:30 |
| India close routine | 09:00 · 08:00 | 18:30 |
| US open routine | 08:00 | 17:30 · 18:30 |
| NYSE / Nasdaq session | 09:30–16:00 | 19:00–01:30 · 20:00–02:30 |
| US close routine | 18:00 | 03:30 · 04:30 (next day) |
| India open routine | 22:30 · 21:30 (previous day) | 08:00 |

Trading both from India, the US review fits the IST morning, with US orders in before the US open; the
India review is in the IST evening.

### Weekly and monthly

**Weekly (30–45 minutes):** the week's calendar and your holdings' results dates, with a decision for each
written in Notes; Markets → Sectors at the industry-group level (top 15–20 by RS, the biggest Δ 1M, the
quadrants); the market's weekly close against its 30-week average; open risk and positions per group;
prune the watchlists; review the week's closed trades.

**Monthly (about an hour):** equity against its peak; your numbers by setup against the strategy's
Backtests tab; the share of trades that followed the plan; at most one rule change, dated in your plan
note. See [expectancy](learn-risk-expectancy.md) and [biases](learn-process-biases.md).

## 12. Notes templates

**New** in Library → Notes offers four templates. Each sets a tag.

| Template | Tag | Sections |
|---|---|---|
| Blank note | — | — |
| **Daily journal** | `journal` | Market (tone; breadth / leading groups) · Positions table (stock, plan, action) · Watching · Lessons |
| **Trade plan** | `plan` | Setup · Entry / stop / target (entry, stop, target, size / risk) · Why now · What would prove me wrong |
| **Trade review** | `review` | What happened · What I did well · What I'd do differently · Lesson |

Keep your one-page trading plan as a pinned Blank note tagged `plan`, and change it only at the monthly
review. A fuller *Trade plan* body that records the decision as it was made:

```
## Before — 2026-10-15
- Strategy / setup: chart_pattern · FWDG     Market: india
- Entry 812   Stop 768   Target 930   (1R = 44 / share)
- Shares 113   Risk ₹4,972 = 1.0% of account   Position 9.2%
- Regime: Nifty above rising 50 & 200-day; 61% of stocks above 50-day
- Group: leading     Earnings: 2026-11-06 (22 days)
- Reason: falling wedge breakout on 2× volume; wrong if back inside the wedge
## During
- (date): stop raised to … — reason:
## After
- Exit date / price / reason:        R (net):      Days held:
- MAE:      MFE:      Followed plan?      Mistakes:      Emotion:
```

A tagging scheme that makes the monthly review a few clicks (tags are stored lower-case):

| Tags | Use |
|---|---|
| `open`, `closed` | Status, changed at the exit |
| `fwdg`, `cupnh`, `vcp` … | The setup, one per trade |
| `win`, `loss`, `scratch` | Result |
| `err-chase`, `err-early-exit`, `err-stop-moved`, `err-size`, `err-no-plan` | One per mistake |
| `regime-up`, `regime-mixed`, `regime-down` | Market at entry |

The app works out none of R, MAE or MFE for your real trades. Keep a spreadsheet with one row per trade
beside the notes; [journaling and review](learn-process-journal.md) says what to record.

## Further reading

- [Using the app — how it computes its numbers](app-guide-how-it-computes.md)
- [Using the app — reading its backtests and screen studies](app-guide-backtests.md)
- [Using the app — screens and strategies](app-guide-screens-strategies.md)
- [Using the app — the strategy families](app-guide-strategy-families.md)
- [A trading plan and routine](learn-process-plan.md) · [Journaling and review](learn-process-journal.md)
