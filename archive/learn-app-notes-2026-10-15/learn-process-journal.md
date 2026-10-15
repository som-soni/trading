# App notes moved out of learn-process-journal (verbatim, 2026-10-15)

Note: sections 6, 7, 9 and parts of 8 and 10 are evidence from the owner's strategy backtests, removed from the guide and kept here for the record.

## Intro, 'Where this shows in the app', 'The data'

# Journaling and review — what to record, and how to find what actually works

Learning material: why a written record beats memory, and what to write down
before, during and after every trade. That includes MAE and MFE — how far a
trade went against you and for you. The guide then shows how to keep that
record in this app today, and the weekly and monthly review that turns it into
knowledge. The review is run on this app's own backtest trades, standing in for
a real journal. This is the second of three process guides, after
[a trading plan and routine](learn-process-plan.md) and before
[biases](learn-process-biases.md).

**Where this shows in the app.** **Library → Notes** ("your notes and trading
journal") has *Daily journal*, *Trade plan* and *Trade review* templates.
**Watchlists** keeps a note per stock. Each backtest's **Trades** tab
(Strategies → a strategy → **Backtests**, or System → Reports archive) lists every
trade with its R and days held, and can **Export CSV**. What the app does *not*
do — record your real trades or their P&L — is in §4.2.

**The data.** Five backtests, closed trades only, 2013–2026 unless stated:
India chart patterns v1.5 (515 trades), US Minervini v1.6 without the market
filter (551, 2010–2026), US Donchian v1.1 (496), India Donchian v1.1 (437) and
US breakout v1.1 (703). R is net of modelled costs. The backtests use stocks
listed today (survivorship bias) and fills at daily-bar prices, and they never
hesitate. Your journal will be messier — finding that mess is its job.

---


## §3 template (used app strategy/setup codes)

## 3. A template

Paste this into a *Trade plan* note. Fill in the bottom half when the trade closes.

```
## Before — 2026-10-15
- Strategy / setup: chart_pattern · FWDG     Market: india
- Entry 812   Stop 768   Target 930   (1R = 44 / share)
- Shares 113   Risk ₹4,972 = 1.0% of account   Position 9.2%
- Regime: Nifty above rising 50 & 200-day; 61% of stocks above 50-day
- Group: leading     Earnings: 2026-11-06 (22 days)
- Reason: falling wedge breakout on 2× volume; wrong if back inside the wedge
- Entry quality: 1.8% above pivot, 6% above 50-day, first base
## During
- (date): stop raised to … — reason:
## After
- Exit date / price / reason:        R (net):      Days held:
- MAE:      MFE:      Followed plan?      Mistakes:      Emotion:
```


## §4 Doing it in the app today (whole section)

## 4. Doing it in the app today

### 4.1 What exists

**Library → Notes.** A note holds a **title**, a **body** in Markdown (with a
rich or plain editor; tables and checklists work), **tags**, linked **stocks**
and a **pinned** flag. It saves as you type (`notes.py`). **New** offers the
templates:

- *Daily journal* (tag `journal`): market tone, breadth and leading groups, a
  Positions table, Watching, Lessons.
- *Trade plan* (tag `plan`): setup; entry / stop / target; size / risk; why
  now; what would prove me wrong.
- *Trade review* (tag `review`): what happened; what I did well; what I'd do
  differently; lesson.

Search covers title, body, tags and linked stocks. Tags show as filter buttons
with counts, and pinned notes sort first. The **Chart**'s side panel lists the
notes linked to the stock on screen, with **+ note**. **Copy as Markdown** and
`python -m swing_screener.notes --export <dir>` write notes out as files.

A tagging scheme that makes the review a few clicks (tags are stored lower-case):

| Tags | Use |
|---|---|
| `open`, `closed` | Status, changed at the exit |
| `fwdg`, `cupnh`, `dc-01`, `vcp` … | The setup, one per trade |
| `win`, `loss`, `scratch` | Result |
| `err-chase`, `err-early-exit`, `err-stop-moved`, `err-size`, `err-no-plan` | One per mistake (§8) |
| `regime-up`, `regime-mixed`, `regime-down` | Market at entry |

**Watchlists.** Your own lists keep a **note** per stock. The **Screener picks**
list shows each pick's strategy, decision, planned entry, stop and target R, peer
group and group RS. That is a record of what the plan *was* that day. For a
tracked company, you can set a **buy-below** price on **Screens → Quality
companies**; its row is flagged AT YOUR PRICE when the close reaches it. There
is no screenshot button. But the Chart's drawings are saved per stock, so an
entry, stop and target drawn on the chart stay there.

### 4.2 What the app cannot do

Confirmed in the code: **no trade log, no position tracking, no P&L of real
trades**, and no broker link or order entry. The app stores notes, watchlists,
chart drawings and backtest results, but nothing about your fills or holdings.
So you work out R, MAE and MFE by hand. The practical companion is a
spreadsheet with one row per trade and the columns of §2. The review in §5 is
then a few pivot tables (summary tables grouped by a column) on it. The *Daily
journal*'s Positions table is typed by you and checked by nothing. **Avg R** on
a Trades tab is the strategy's number, not yours.


## §6 What such a review finds — the backtests as a stand-in journal (whole section)

## 6. What such a review finds — the backtests as a stand-in journal

### 6.1 By setup

India chart patterns, setups with 13 or more trades. The standard error is the
typical amount by which an expectancy could be off through chance alone:

| Setup | Trades | Win % | Avg win | Avg loss | Expectancy | Std error | 2013–19 (n) | 2020–26 (n) |
|---|---|---|---|---|---|---|---|---|
| Ascending triangle (ATRI) | 52 | 36.5% | +2.54R | −1.04R | **+0.27R** | 0.26 | +0.46 (19) | +0.16 (33) |
| Inverse head and shoulders (IHS) | 34 | 32.4% | +2.88R | −1.02R | +0.24R | 0.35 | −0.07 (15) | +0.49 (19) |
| Symmetrical triangle (SYMM) | 27 | 33.3% | +2.56R | −1.02R | +0.18R | 0.34 | +0.08 (6) | +0.20 (21) |
| Falling wedge (FWDG) | 107 | 32.7% | +2.62R | −1.03R | +0.16R | 0.18 | +0.16 (35) | +0.16 (72) |
| Cup without handle (CUPNH) | 201 | 28.9% | +3.01R | −1.08R | +0.10R | 0.14 | −0.13 (56) | +0.19 (145) |
| Double bottom (DBOT) | 27 | 37.0% | +2.04R | −1.12R | +0.05R | 0.31 | +0.17 (13) | −0.06 (14) |
| Rectangle (RECT) | 48 | 31.2% | +1.91R | −1.03R | **−0.12R** | 0.20 | −0.01 (15) | −0.17 (33) |
| Triple bottom (TBOT) | 13 | 30.8% | +1.82R | −1.02R | −0.14R | 0.39 | −1.02 (3) | +0.12 (10) |
| **All** | 515 | 32.0% | +2.68R | −1.05R | **+0.14R** | 0.08 | | |

**The standard errors are larger than the gaps between setups.** The rankings
also flip between the two halves of the period (IHS −0.07R → +0.49R; DBOT
+0.17R → −0.06R); only FWDG held steady. Nothing here proves one pattern
better. What deserves attention: rectangles were below zero in both halves,
with the smallest average win. That is a reason to *watch* RECT and test a
change on more data, not to drop it on 48 trades.

### 6.2 By market regime

Split by whether the index (S&P 500, Nifty 50) closed above its 200-day average
on the entry date. This is a simple stand-in for the app's market-regime check
([the trend guide](learn-health-trend.md) §7):

| Run | Index above 200-day: trades, expectancy | Below: trades, expectancy |
|---|---|---|
| US Donchian | 310, **+0.87R** | 186, **−0.16R** |
| India Donchian | 260, +0.59R | 177, +0.17R |
| US breakout | 650, +0.07R | 53, −0.31R |
| US Minervini v1.6, no market filter | 489, +0.06R | 62, −0.08R |
| India chart patterns | 428, +0.08R | 87, +0.44R |

Four of five did worse below the 200-day — US Donchian by a wide margin, on a
large sample. India chart patterns did better, on 87 trades with a standard
error of 0.23R. That result is noted, not explained away. The app acted on
this kind of finding: Minervini v1.7 made its market filter the default. Its
changelog records trades falling from 557 to 490, expectancy rising from
+0.04R to +0.06R, and max drawdown improving from −43.5% to −28.6%.

### 6.3 By holding period

| Days held (calendar) | US Donchian: trades, expectancy | India chart patterns: trades, expectancy |
|---|---|---|
| 10 or fewer | 123, −1.11R | 129, −0.67R |
| 11–30 | 92, −1.04R | 154, −0.04R |
| 31–90 | 104, −0.87R | 171, +0.56R |
| Over 90 | 177, **+3.18R** | 61, **+1.15R** |

Every Donchian trade closed within 30 days lost. But "hold longer" is the wrong
lesson. **Holding period is an outcome, not a decision**: the stop ends losers
early, and the trend lets winners run. The table shows what a normal trade
looks like. So a journal full of winners sold after 12 days says the exits are
too quick.

### 6.4 By entry quality

Two measures, each cut into thirds of 146–235 trades: stop width (entry to
stop, as a % of entry), and how far the price was above its 50-day average at
entry ("extended"):

| Run | Tight-stop third | Wide-stop third | Least extended | Most extended |
|---|---|---|---|---|
| US Donchian | +0.68R (2.2–5.6%) | +0.06R (9.6–36.8%) | +0.82R | +0.36R |
| US breakout | −0.00R (3.0–4.1%) | +0.14R (5.4–15.8%) | +0.00R | +0.18R |
| US Minervini | +0.00R (2.0–4.8%) | +0.15R (6.3–8.0%) | +0.06R | −0.02R |
| India chart patterns | +0.02R (3.2–5.6%) | +0.16R (6.9–17.7%) | +0.21R | +0.23R |

Standard errors are 0.10–0.48R. Wide stops hurt Donchian and helped the
breakout. Minervini's RS rank gives +0.20R below 80, −0.20R at 80–89 and +0.14R
at 90+. There is no steady pattern there that anyone could trade. **Most
entry-quality splits are noise.** Trust one only if it moves steadily in one
direction, makes sense, and holds in both halves.

### 6.5 By exit reason, and by month

US Minervini:

- 144 stop-outs cost −149.4R (−1.04R each);
- 367 trend exits (a close below the 50-day) made +35.4R;
- 11 breakeven stops made +3.6R;
- **29 climax sales — 5% of trades — made +134.3R**, more than the whole run's +23.8R.

The edge lives in a handful of exits. Anything that cuts those winners short
erases it ([stops and exits](learn-risk-stops-exits.md)).

By month: the share of calendar months whose closed trades added up to a loss
was 53% (India chart patterns, 135 months), 54% (US breakout), 55% (US
Donchian) and 61% (US Minervini, India Donchian). By year of entry, India chart
patterns ranged from −0.67R (2019, 34 trades, 9% winners) to +0.78R (2020).
**Over half of all months lose in every run, including the ones with a real
edge.** Judge a method month by month and you will abandon every method.

### 6.6 MAE and MFE

Computed from the stored daily prices for every trade (method below):

| Run | Winners: median MAE | Winners that first fell −0.5R or more | Losers that first reached +1R | Winners: median MFE → realised |
|---|---|---|---|---|
| India chart patterns | −0.34R | 37% | 31% | +2.53R → +2.53R (target) |
| US breakout | −0.39R | 40% | 25% | +2.17R → +2.17R (target) |
| US Minervini | −0.21R | 19% | 21% | +3.27R → +1.66R |
| US Donchian | −0.36R | 37% | 27% | +5.29R → +2.10R |
| India Donchian | −0.44R | 44% | 30% | +4.85R → +1.92R |

**Winners dip.** Over a third went half-way to the stop first (a fifth for
Minervini), so a much tighter stop would have cut them. **A quarter or more of
losers were up +1R first.** That is the case for a breakeven stop, tested in
§9. **Trailing exits keep about half the peak profit.** That is the price of
catching the rare very large winners.

```series
title: BofI (now Axos, AX), 2015 — a +6.3R open profit that ended at −1R
from: 2015-06-01
to: 2015-11-30
tf: D
line: us:AX | AX | log
mark: 2015-07-08 | Donchian entry about $26.5, stop $25.04
mark: 2015-10-12 | High $35.98: MFE +6.3R
mark: 2015-10-14 | Opens $33.40, falls to $24.78: stopped at $25.03
caption: The US Donchian backtest's biggest round trip. Its exit waits for a close below the 50-day low and its stop never trails, so a 30% fall in one session (close $35.50 to $24.78) took the trade from +6.3R open profit to −1.0R.
```

**Method.** MAE = the lowest daily low from the day *after* entry to the day
*before* exit, or the exit price if that is lower. MFE is the same with highs.
Both are divided by the initial risk (entry − initial stop). The entry-day and
exit-day highs and lows are left out, because a daily bar cannot say whether
they came before or after the fill. That is why fixed-target winners show MFE
equal to the target. Every entry price lies within 0.5% of its day's stored
low–high range (slippage included), so the prices match.


## §7 Your live R against the backtest (whole section)

## 7. Your live R against the backtest

After 20 live trades you will want to know whether you are trading the strategy
or something worse. A bootstrap shows how widely an honest average moves by
chance. It takes 20,000 random samples of N trades from each run's closed
trades (the same trade can be drawn more than once):

| Run (backtest expectancy) | 20 trades: 10th–90th pct, P(avg < 0) | 50 trades | 100 trades |
|---|---|---|---|
| US Donchian (+0.49R) | −0.51 to +2.11, 40% | −0.24 to +1.42, 26% | −0.07 to +1.14, 15% |
| India chart patterns (+0.14R) | −0.37 to +0.68, 38% | −0.19 to +0.48, 30% | −0.09 to +0.38, 23% |
| US Minervini (+0.04R) | −0.37 to +0.50, 48% | −0.22 to +0.32, 44% | −0.15 to +0.24, 40% |

**A strategy truly earning +0.49R a trade shows a loss after 20 trades 40% of the
time.** A negative live average over 20–50 trades proves nothing by itself. An
average below the 10th percentile for your trade count is worth investigating
now. Faster evidence comes from **rule breaks**. Compare the plan with the
actual fill on every trade, and they show up from the first trade. See
[expectancy](learn-risk-expectancy.md) §5 for how many trades a verdict needs.


## §8 (backtest sentence) and §9 breakeven test on backtests, §10 evidence, §11 checklist

## 8. Error categories — process versus outcome

Grade each trade twice: **did I follow the plan**, and **did it make money**.

| | Made money | Lost money |
|---|---|---|
| **Followed the plan** | Good trade, good result | **Good trade, bad result** — the cost of business; change nothing |
| **Broke the plan** | **Bad trade, good result** — the dangerous one: it teaches the wrong lesson | Bad trade, bad result — fix the process |

In these backtests 66–73% of trades lose, and every one was executed exactly to
plan. A losing trade is not an error. Errors are failures of process:

| Category | Examples | Shows up as |
|---|---|---|
| Selection | Outside the screen; bad regime ignored; earnings in two days | Lower win rate |
| Entry | Chased above the pivot; bought before the trigger | Smaller R on winners |
| Sizing | 3% risk "because it looked great"; cap ignored | Drawdowns out of proportion |
| Management | Stop moved wider; added to a loser | Average loss worse than −1R |
| Exit | Winner sold early; exit signal ignored | The biggest winners cut short |
| Admin | No plan note; R not recorded | Nothing to review |

Two numbers a month summarise discipline: **the share of trades that followed the
plan**, and **the total R of those that did not**. The second is usually
negative, and often larger than any difference between setups in §6.

## 9. From finding to rule change — one at a time

1. **Write the finding with its sample size**: "31% of chart-pattern losers first
   reached +1R (350 losers)."
2. **State the change exactly**: "once the high reaches entry + 1R, raise the
   stop to entry from the next day."
3. **Test it on the whole record and on each half separately.**
4. **Change one rule at a time** and log it with a date — as each strategy's
   changelog does — so later results can be read against it.
5. **Re-review after enough trades** (§7), not after one bad week.

That breakeven idea was tested trade by trade on the stored daily bars. The
stop moves to the entry price the day after the high first reaches +1R. If a
later low touches it, the trade exits at the stop, or at the open if the price
gapped below. Otherwise the original result stands:

| Run | Trades changed | Expectancy before → after | 2013–19 | 2020–26 |
|---|---|---|---|---|
| India chart patterns | 148 of 515 | +0.14R → **+0.07R** | +0.03 → −0.06 | +0.19 → +0.13 |
| US breakout | 167 of 703 | +0.04R → **+0.01R** | −0.01 → −0.03 | +0.10 → +0.04 |

It **halves the edge or worse, in both halves of both runs**. The winners it
closes at breakeven on a normal dip (§6.6) outnumber the losers it rescues.
The simulation ignores the capital such an exit frees for the next trade
([stops and exits](learn-risk-stops-exits.md) §8). Still, a rule that feels
like free insurance tested as the opposite. That is why a change is tested
before it is traded.

## 10. What the evidence says

- **Robust:** process and outcome are separate. Every run here loses on 66–73% of
  trades and in more than half of all months while following its rules exactly.
- **Robust:** splits on small samples mislead. Setup and entry-quality rankings
  flip between halves of a 13-year record (§6.1, §6.4), and a personal journal
  has far fewer trades.
- **Supported here:** trend and breakout methods earn less, or lose, with the index
  below its 200-day (four of five runs, §6.2).
- **Widely held, not measured here:** that a written review improves trading.
  Performance coaches (Steenbarger, Tharp) put it at the centre. Its measurable
  payoff is that it exposes the gap between your plan and what you actually did.
- **Folklore:** that a breakeven stop is free protection (§9), or that the
  holding-period split says "hold longer" (§6.3).
- **Limits:** the stand-in journal is a backtest — perfect execution, modelled
  costs, survivorship bias. Your record adds execution errors; finding them is the point.

## 11. Checklist

- [ ] Weekly: every closed trade has R (net), days held, MAE, MFE, exit reason and tags
- [ ] Weekly: each *Plan* note read against what happened; rule breaks tagged `err-…`; no rule changed
- [ ] Monthly: expectancy, win rate, average win and loss — with the trade count
- [ ] Monthly: split by setup, regime, holding period, entry quality, exit reason; sample size beside each
- [ ] Average loss no worse than about −1.1R; if worse, find the stops that slipped
- [ ] Live average R against the backtest's 10th–90th percentile for your trade count (§7)
- [ ] Share of trades that followed the plan, and the total R of those that did not
- [ ] At most one rule change — written exactly, tested on the full record and both halves, dated

