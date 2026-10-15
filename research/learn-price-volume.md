# Volume — how strongly a move is supported

Learning material: what a stock's volume can and cannot tell you. It covers
relative volume, breakouts with and without volume, volume drying up in a base,
accumulation and distribution days in a single stock, pocket pivots, climax runs,
selling climaxes and volume on results days. The claims are checked against the
app's own backtest trades and against every breakout in its stored prices. The
answer is more modest than most books suggest. This guide is about one **stock**.
Volume for the whole **market** (distribution days on the index) is in
[the distribution guide](learn-health-distribution.md). For the basic vocabulary,
see [Start here](learn-start-here.md).

**Where this shows in the app.** The **Chart** page draws volume bars under the
price by default, with a 20-day average line. That is the *Volume* indicator. Its
*Volume* group also offers Rolling VWAP, On Balance Volume, Money Flow Index and
Chaikin Money Flow (`web/static/studies.js`). Relative volume (the day's volume ÷
its 50-day average) appears in three places:

- the *Rel vol* column on **Markets → Movers**;
- the *Unusual volume — up / down* lists on **Markets → Post-market → Stocks**
  (`analytics/postmarket.py`: at least `UNUSUAL_RVOL` = 2.5× average and a move of
  2% or more);
- the *Relative volume* field you can use in your own screens (`screens/snapshot.py`).

The strategies' volume rules are described in sections 3–6.

**The data.** Trade lists of the app's backtests, each strategy's latest full run:
US Volume breakout (703 closed trades, 2013–2026), US trend pullback (863),
US Donchian (496), US Minervini v1.6 (551, 2010–2026), India trend pullback (347),
India Donchian (437), India chart patterns (515). These are **backtests with
modelled costs** on stocks listed today, so they carry survivorship bias (companies
that failed and delisted are missing). Relative volume for each trade was computed
from the stored daily prices. My analysis scripts are not part of the app.

---

## 1. What volume is — and what it cannot tell you

Volume is **the number of shares that changed hands** in a session. Every share
bought was sold by someone else. So volume is never "more buyers than sellers".
Buyers and sellers are always equal in number of shares.

What differs is **who was more eager**. If buyers are keener, they pay the
sellers' asking price, and the price rises. If sellers are keener, they accept
the buyers' bids, and the price falls. The price change shows which side was
pushing. The volume shows **how much business was done at those prices**.

So read the two together:

| Price | Volume | What it suggests |
|---|---|---|
| Up strongly | Well above average | Many shares changed hands at rising prices: the move is broadly supported |
| Up | Below average | The price rose, but little business was done: few participants confirmed it |
| Down strongly | Well above average | Heavy selling was absorbed only at lower prices |
| Down gently | Below average | A quiet pause; few holders are selling |

What volume **cannot** tell you:

- **Who is buying.** Daily volume does not show whether it is a pension fund, a
  hedge fund or many small traders. "Institutional accumulation" is an inference.
  It is a reasonable one when volume is heavy, because funds trade in size. But it
  is never visible in the data.
- **Why.** Index additions, options expiry, a block trade and results all inflate
  volume. None of them needs anyone to have changed their view of the company.
- **What happens next**, on its own. Section 3 shows how little a single day's
  volume predicts.

## 2. Relative volume — compare a stock with itself

A million shares is a lot for one stock and nothing for another. So compare a
day's volume with **the same stock's normal volume**:

> **Relative volume = today's volume ÷ the 50-day average volume**

1.0 is a normal day. 2.0 is twice normal. 0.5 is half. The app uses the 50-day
average everywhere a rule tests volume (the stored `vol_sma50`, which includes
today). The Chart page's volume line is a 20-day average, so it will look a
little different.

How often big and small days occur, measured since 2015 on a third of the liquid
stocks in each market:

| Daily relative volume | US | India |
|---|---|---|
| Median day | 0.89× | 0.74× |
| 2× or more | 4.3% of days | 8.7% |
| 3× or more | 1.2% | 3.9% |
| Under 0.5× | 6.1% | 26.5% |

Indian stocks trade far more unevenly. **A 2× day is about twice as common in
India, and a 3× day three times as common.** The average is pulled up by a few
huge days, so the typical day sits well below 1.0. Keep this in mind when you use
the same threshold in both markets (section 9).

## 3. Breakouts on volume and without — measured

The classic rule (O'Neil, Minervini): a breakout should come on volume at least
40–50% above average. Few buyers behind a breakout means it is likely to fail.

### 3.1 The app's rules

| Strategy | Volume rule on the breakout |
|---|---|
| Volume breakout | BO-01: close above the 55-day high on volume **over 1.5×** the 50-day average |
| Minervini SEPA | MV-01: close through the pivot on at least `VOL_MULT` = **1.4×**, in the upper half of the day's range |
| Chart patterns | The trigger fires on a close through it on `BO_VOL` = **1.4×**; without it, flag XS2 caps the setup at WATCH |
| Donchian, trend pullback | No volume rule on entry |

The Volume breakout strategy also has a flag (XB2) for a breakout on below-average
volume. Its own Strategies page notes that it can never fire, because BO-01
already demands 1.5×.

### 3.2 The app's backtest trades

Each trade was grouped by relative volume **on its entry day**. In the Volume
breakout run, every signal day already had over 1.5× by rule. The order then
filled on a later day as the price moved through the entry level. For 72% of
trades that was the very next session. So the entry day is a second test:
did the buying continue?

| Run | Entry day under 1× | 1–1.5× | 1.5× or more |
|---|---|---|---|
| US Volume breakout | 178 trades · 28% won · −0.10R | 274 · 34% · +0.10R | 251 · 39% · +0.07R |
| US trend pullback | 522 · 24% · −0.11R | 234 · 29% · +0.08R | 107 · 37% · +0.27R |
| India trend pullback | 147 · 24% · −0.05R | 112 · 34% · +0.31R | 88 · 33% · +0.14R |
| India chart patterns | 149 · 32% · +0.10R | 148 · 25% · −0.09R | 218 · 37% · +0.33R |
| US Donchian | 199 · 27% · +0.32R | 173 · 34% · +0.67R | 124 · 25% · +0.49R |
| India Donchian | 172 · 26% · +0.53R | 124 · 26% · +0.15R | 141 · 30% · +0.52R |

What this shows, honestly:

- **The win rate rises with entry-day volume** in four of the six runs. In the
  Volume breakout run it went from 28% to 39%.
- **The average R barely moves.** In the Volume breakout run, the gap between
  light and heavy entry days is about 0.2R. Each average has a standard error of
  about ±0.10R, so the gap is not much larger than chance. The same direction
  held in both halves of the period: 2013–19 −0.17R against +0.05R, 2020–26
  −0.01R against +0.13R.
- **In the Donchian runs, volume tells you nothing.** These trend trades are
  decided by a few very large winners, and those came on light and heavy days alike.

Within the Volume breakout run, the **signal day's** volume mattered only at the
extreme. Signals at 1.5–2× (464 trades) and 2–3× (199) both averaged +0.02R.
The 40 signals at 3× or more won 48% of the time and averaged +0.44R (±0.25R).
That is suggestive, but it rests on 40 trades.

### 3.3 Every breakout in the stored data

Backtest trades are filtered by many other rules. So I also tested the plain
pattern. A breakout here is the first close above the highest high of the prior
55 sessions, after 30 sessions trading within a 15% range, with the price above
its 200-day average. That gave 47,062 breakouts in 979 liquid US stocks,
2013–2026. A **failure** is a close more than 3% back under the old high within 10
sessions. The return is 60 sessions, minus SPY's return over the same days.

| Breakout-day volume | Breakouts | Failed within 10 days | 60-day return vs SPY | Of those closing within 2% of the old high: failed |
|---|---|---|---|---|
| under 0.8× | 10,646 | 22.6% | −0.3% | 22.6% |
| 0.8–1.2× | 18,508 | 23.0% | −0.5% | 23.2% |
| 1.2–1.5× | 7,481 | 23.0% | −0.4% | 23.5% |
| 1.5–2× | 5,190 | 23.1% | −0.7% | 25.1% |
| 2–3× | 3,182 | 19.1% | −0.2% | 24.3% |
| 3× or more | 2,055 | 12.6% | +0.3% | 25.3% |

At first sight, heavy-volume breakouts fail far less often (12.6% against about
23%). But **they also close much further above the old high**: a median of 3.6%,
against 0.3% for the lightest. So a heavy breakout needs a bigger drop to count
as failed. Compare breakouts that closed within 2% of the old high (the last
column), and the advantage disappears. In India (6,437 breakouts in 434 liquid
stocks) heavy-volume breakouts that closed near the old high failed *more* often:
37.4% against 28.8%. **In neither market did the breakout day's volume change
the 60-day return relative to the index.**

So the evidence here is weaker than the folklore. A big, decisive day — a large
move on heavy volume — tends to keep going a little better in the short run.
The volume alone, without the size of the move, does not.

### 3.4 Two examples

```series
title: Arista Networks (ANET) — a breakout on heavy volume, November 2016
from: 2016-08-01
to: 2017-03-31
tf: D
line: us:ANET | Arista (split-adjusted) | log
line: us:ANET@sma50 | 50-day average
line: us:ANET@vol | Volume | pane2 bars
mark: 2016-11-21 | +7.4% on 3.4× volume
caption: After three months in a range, ANET closed at the day's high, above its 55-day high, on 3.4× its average volume. The three days before were quiet (0.4–0.8×). It was 26% higher three months later, despite a 12% one-day drop on heavy volume in January.
```

Arista spent September to mid-November within about 10% of its high. Volume
faded in the last days: 0.68×, 0.41× and 0.80× of average. On 21 November it
rose 7.4% to close at the top of its range, on 3.4× average volume. On
17 January 2017 it fell 12% in one day on 5.4× volume, closing about 1.4% under
the old high. It held that level for a week, then went on. By the end of March it
was 40% above the breakout close. So even a clean breakout can give one hard
test: a stop placed under the base, not under the breakout day, survived it.

```series
title: Domino's Pizza (DPZ) — new highs on light volume, December 2021
from: 2021-10-01
to: 2022-02-28
tf: D
line: us:DPZ | Domino's Pizza
line: us:DPZ@sma50 | 50-day average
line: us:DPZ@vol | Volume | pane2 bars
mark: 2021-12-27 | new high on 1.07× volume
mark: 2021-12-31 | peak close, 0.74× volume
caption: DPZ broke to new highs in the week between Christmas and New Year, on 0.45–1.07× its average volume. It peaked on 31 December and was 25% lower by 26 January.
```

Domino's closed above its 55-day high on 27 December 2021, on 1.07× average
volume. It made new closing highs on the 29th and 31st on 0.62× and 0.74×. On
28 December volume was 0.45×. That is holiday-week volume: many traders are away.
The stock peaked at 564 on 31 December and fell to 424 by 26 January, down 25%.

Be fair to this example: **the whole market fell in January 2022** (SPY −8% to
21 January). Light volume did not cause the fall. It means the new highs had
little participation behind them, so they gave little evidence of demand. Many of
the worst light-volume breakouts in the data sit just before market-wide drops,
such as February 2020.

## 4. Volume drying up in a base

A base is a pause in an uptrend. While it forms, holders who want out sell.
When they have mostly gone, fewer shares are offered, and **volume falls**.
Quiet trading near the lows of a base suggests sellers are scarce. That is the
"dry-up" in [the VCP guide](learn-vcp.md) and [the bases guide](learn-bases.md).

**How the app tests it.** The Minervini strategy's base detector
(`core/vcp_spec.py`, rule VCP-10) takes the final tight area of the base — the
bars since the last pullback low, at most `TIGHT_DAYS` = 10. It requires their
average volume to be **at most `DRYUP_RATIO` = 0.70×** the 50-day average. The
50-day average is taken from the bar *before* the tight area. Otherwise the quiet
days themselves would lower the benchmark and make the test too easy to pass. The
older, superseded Minervini strategy used a looser test: tight-area volume above
1.0× its average raised flag V2.

**What the data says.** In the broad US breakout test, I split breakouts by the
volume of the 10 sessions before them, against the 50-day average before those:

| Volume of the 10 days before the breakout | Breakouts | Failed | 60-day return vs SPY |
|---|---|---|---|
| 0.7× or less (dried up) | 6,726 | 24.1% | −0.1% |
| 0.7–1.0× | 24,101 | 22.6% | about −0.35% |
| above 1.0× | 16,235 | 21.0% | about −0.5% |

A dry-up before the breakout made **no measurable difference** here. Dry-up plus
a 1.5× breakout day (835 cases) did no better either. This is a crude stand-in
for a VCP: ten days, not the tight area of a measured base. It does not test the
full pattern. It does say that **"quiet before the breakout" is not an edge on
its own**. Treat the dry-up as one piece of a base that looks right, not as a
signal.

## 5. Accumulation and distribution in one stock

### 5.1 What the app counts

An **accumulation day** is a day the price closes up at least 0.2% on volume
higher than the day before. A **distribution day** is the mirror image: down at
least 0.2% on higher volume. This is O'Neil's index rule applied to one stock.

The Trend pullback strategy computes a demand/supply verdict for each candidate
(`core/demand_supply.py`). It scores three tests, +1 or −1 each:

| Test | +1 (demand) | −1 (supply) |
|---|---|---|
| Up/down volume ratio: volume on up days ÷ volume on down days, last 50 sessions | 1.2 or more | below 0.8 |
| Accumulation vs distribution days, last 25 sessions | accumulation more than distribution + 1 | distribution more than accumulation + 1 |
| Pullback volume ÷ volume of the rally before it | below 0.8 | above 1.1 |

A total of +2 or more is "Demand in control"; −2 or less is "Supply in control";
anything else is "Balanced". **"Supply in control" caps the decision at WATCH —
WAIT.** The verdict and its counts ("U/D 1.35, 7 acc vs 4 dist") appear in the
strategy's output. The same file also marks a supply zone at the low of any
down bar on more than 1.5× average volume in the last 60 sessions that sits above
the price. Those thresholds are written into the code, not named settings.

### 5.2 Does it predict anything?

On month-ends 2013–2026 across the same 979 US stocks (142,493 readings), the
typical stock had 6 accumulation and 5 distribution days in 25 sessions. The
up/down ratio's median was 1.06. Then the next 60 sessions, against SPY:

| Reading | Readings | Mean | Median |
|---|---|---|---|
| Distribution > accumulation + 1 | 44,165 | +2.15% | −0.18% |
| Balanced | 46,439 | +0.79% | −0.60% |
| Accumulation > distribution + 1 | 51,889 | +0.87% | −0.57% |
| Up/down volume ratio under 0.8 | 27,153 | +3.53% | −0.24% |
| Up/down volume ratio 1.2 or more | 50,853 | +0.90% | −0.60% |

**There is no edge in the counts on their own.** If anything, stocks under recent
selling did slightly better on average, which is a bounce effect. Averages this
far above the medians are pulled up by a few big rebounds. The app uses the
verdict as a **veto inside a pullback setup**, not as a forecast. That is the
right use: a pullback on heavy selling is a different thing from a quiet one.

### 5.3 Pocket pivots

Gil Morales and Chris Kacher (*Trade Like an O'Neil Disciple*) describe the
**pocket pivot**: an early buy point *inside* a base or near the 10-day average.
Their test is an up day whose volume is **larger than the largest down-day volume
of the prior 10 sessions**. Their idea is that a fund's buying shows up before
the stock breaks out. This is their method. The app does not compute pocket
pivots, and I have not tested them here.

## 6. Climax runs — the volume of a top

A **climax run** is the last burst of a long advance. The stock has already risen
a long way, often 100% or more in a few months. Then it has its biggest up day,
often a gap, on its heaviest volume of the move. It looks like strength. It is
often the last buyers arriving at once. O'Neil and Minervini both sell into it.
See [the chart-patterns guide](learn-chart-patterns.md) for the shape.

The app's Minervini exit EX-05 (`backtesting/portfolio_sim.py`) only applies
once a position is up 25%. Then any one of these sells at the next open:

- the biggest up day since entry, on the biggest volume since entry;
- 8 up closes in the last 10;
- a close 70% or more above the 200-day average;
- a 3% gap up after a gain of more than 50%.

In the US Minervini run, 29 climax exits averaged +4.63R
([stops and exits](learn-risk-stops-exits.md)). The same exit set uses volume
once more, on the way out: EX-06 sells on a close under the 50-day average only
if that day's volume is at least average. A quiet dip under the average is
allowed; a heavy one is not.

```series
title: NVIDIA — a climax run, November 2021
from: 2021-06-01
to: 2022-06-30
tf: D
line: us:NVDA | NVIDIA (split-adjusted) | log
line: us:NVDA@sma50 | 50-day average
line: us:NVDA@vol | Volume | pane2 bars
mark: 2021-11-04 | +12% on 4.4× volume
mark: 2021-11-29 | peak close
caption: After doubling in six months, NVDA rose 12% in a day on 4.4× its average volume, its heaviest of the run. Three weeks later it peaked, about 70% above its 200-day average. It then fell 66% by October 2022.
```

By 4 November 2021, NVIDIA was up 101% over the prior six months. That day it
rose 12.0% on 4.4× its average volume, in a range far wider than usual. Results
on 17 November added an 8% jump. On 22 November the price was 70% above its
200-day average — the app's third climax test. That day it made a new intraday
high, then closed down 3.1% on 2.3× volume: a reversal on heavy volume. The
closing high came on 29 November. By 14 October 2022 it was 66% lower.

**A climax is clear only afterwards.** Many stocks have big up days on heavy
volume and keep rising. So the climax rule sells only *part* of a position or
only after a large gain. It does not short the stock.

## 7. Selling climaxes and capitulation

The mirror image happens at bottoms. After a long fall, holders give up at once:
a huge down day, often a gap, on record volume. This is **capitulation** — the
last sellers leaving. Once they have sold, there may be few left.

```series
title: Meta Platforms — capitulation and a results-day gap, 2022–2023
from: 2022-07-01
to: 2023-06-30
tf: D
line: us:META | Meta
line: us:META@sma50 | 50-day average
line: us:META@vol | Volume | pane2 bars
mark: 2022-10-27 | −24.6% on 6.6× volume
mark: 2022-11-03 | low
mark: 2023-02-02 | +23.3% on 4.7× volume
caption: Already down 66% from its 2021 peak, Meta fell another 25% in a day on 6.6× volume. The low came five sessions later, on far lighter volume. Then a results-day gap up on 4.7× volume started a run that more than tripled the stock from its low.
```

Meta peaked at 382 on 7 September 2021. On 27 October 2022, after its results,
it fell 24.6% to 97.94 on 6.6× its average volume. **That was not the exact
low.** The stock drifted to 88.91 by 3 November, on 1.4× volume, down 76.7% from
the peak. From there it rose 223% by the end of June 2023.

Two lessons:

- **Capitulation marks the area of a low, not the day.** Prices often slide a
  little further on lighter volume. The lighter volume is the point: the forced
  sellers have gone.
- **Do not buy the capitulation day itself.** A strategy in this app buys
  strength — a stock back above its averages, in a base, with rising RS. A
  selling climax only tells you to start watching.

At the level of the whole market, the bottom is confirmed by a follow-through
day, covered in [the distribution guide](learn-health-distribution.md).

## 8. Volume on results days

Results days usually have the heaviest volume of a stock's quarter. That is why
[the earnings guide](learn-fund-earnings.md) dates each results reaction as the
highest-volume session around the filing.

A gap on results is new information arriving all at once. The volume says how
many holders acted on it. A **gap up on very heavy volume that holds** for the
next days shows that many buyers changed their view of the company. Meta on
2 February 2023 (above: +23.3% on 4.7×) is one example. A gap that is sold back
into within days, on heavy volume, says the opposite.

```series
title: Emami (India) — a results-day surge on 13× volume, May 2024
from: 2024-02-01
to: 2024-09-30
tf: D
line: india:EMAMILTD.NS | Emami
line: india:EMAMILTD.NS@sma50 | 50-day average
line: india:EMAMILTD.NS@vol | Volume | pane2 bars
mark: 2024-05-30 | results: +16.8% on 13.2× volume
caption: On the day its results were filed, Emami rose 16.8% on 13.2× its average volume, closing above its January high. The India chart-pattern backtest bought it the next day and reached its target in July (+3.85R). The stock peaked 60% above the pre-results close in August.
```

Emami had traded below its January high for five months. On 30 May 2024, the
day its quarterly results were filed, it rose 16.8% on 13.2× average volume and
closed above that high. It added 11% more on 5 June, on 5.2×. The India
chart-pattern backtest bought it on 31 May at 612 with a stop at 568. It sold at
the 783 target on 9 July. The stock went on to 840 by 28 August.

**Most strategies here refuse new trades near results** (gate B7 in the Volume
breakout: no results within 10 days). A results gap is something you react to
afterwards, not something to hold through by design.

## 9. India: what is different

- **Volume is more uneven** (section 2). A median day is 0.74× average, and over
  a quarter of days trade under half the average. A fixed 1.4× or 1.5× rule is a
  lower bar in India than in the US. Big-volume breakouts were common (25% of
  Indian breakouts were at 3× or more, against 4% in the US). They did not do
  better.
- **NSE only.** The app's Indian prices come from the NSE listing (symbols ending
  `.NS`). Shares traded on the BSE are not added in.
- **Delivery percentage is not stored.** In India, a trade is either settled by
  delivery (shares move into a demat account — the holding account for shares)
  or squared off the same day (intraday). NSE publishes the delivery share each
  day. Many Indian traders read a high delivery share as genuine buying, rather
  than day trading. The app does not download it, so no rule or chart here uses it.
- **F&O stocks.** About 200 large Indian stocks also have futures and options on
  the NSE (F&O). Their volume can spike on the monthly expiry, when traders roll
  positions. The app does not record which stocks are in F&O. Give an expiry-week
  volume spike in such a stock less weight. The [calendar guide](learn-macro-calendar.md)
  lists the expiry dates.
- **Block and bulk deals** (one large trade between two parties, reported by the
  exchange) can make one day's volume huge with no change in the price.

## 10. What a trader does

1. **Read volume as relative volume**, against the stock's own 50-day average.
   Never compare raw share counts between stocks.
2. **On a breakout, look at the whole day:** the size of the move, where it
   closed in its range, and the volume. A small close above the old high on light
   volume is weak evidence. A wide day closing at its high on 2–3× average is
   strong evidence. Neither is a guarantee.
3. **Check the calendar before reading volume.** A holiday week, an index
   rebalance, an options expiry or results day changes volume for mechanical reasons.
4. **In a base, watch the pullbacks.** Pullbacks on lighter volume than the rally
   before them are normal. Big down days on heavy volume inside a base are a
   warning.
5. **After a long run, a record-volume up day is a reason to sell some**, not to
   buy more.
6. **After a long fall, a record-volume down day is a reason to start watching**,
   not to buy.
7. **Do not let volume override the stop.** It is one input among price, trend
   and RS, never the reason to keep a losing trade.

## 11. What the evidence says

- **Robust:** volume rises on big price moves and on news. Climaxes and
  capitulations come on extreme volume. Studies also find that stocks with unusually
  high volume tend to do a little better over the following weeks (Gervais, Kaniel and
  Mingelgrin, 2001), but the effect is small.
- **Supported here, weakly:** in the backtests, entry days on above-average volume
  won more often. The effect on average R was small and within chance in most runs.
  The Volume breakout run's 40 signals at 3× or more did best, on a small sample.
- **Not supported here:** that breakout-day volume, alone, reduces failures or lifts
  returns. The lower failure rate of heavy-volume breakouts came from their bigger
  moves. A dry-up before the breakout and accumulation/distribution counts did not
  predict 60-day returns.
- **Not tested here:** pocket pivots; the full VCP with its dry-up; delivery
  percentage in India.
- **Caveats:** daily bars only; survivorship bias in all the data; my breakout test
  is a simple stand-in for the patterns traders actually draw. None of the
  backtests here beats simply buying the index.

## 12. Checklist

- [ ] Breakout candidates: relative volume on the day, the size of the move, and the close in the day's range
- [ ] Any holiday, expiry, rebalance or results date behind an odd volume reading?
- [ ] Bases on the watchlist: pullbacks on lighter volume? Any heavy-volume down days?
- [ ] Trend pullback candidates: the demand/supply verdict — "Supply in control" means wait
- [ ] Holdings up a long way: any record-volume up day or wide reversal — sell some?
- [ ] Markets → Post-market → Stocks: the unusual-volume lists for new names
- [ ] India: discount volume spikes in F&O stocks near expiry

## Further reading

- William O'Neil, *How to Make Money in Stocks* — breakout volume, climax tops,
  distribution.
- Mark Minervini, *Trade Like a Stock Market Wizard* — the VCP, volume dry-up and
  selling into a climax.
- Gil Morales and Chris Kacher, *Trade Like an O'Neil Disciple* — the pocket pivot.
- Joseph Granville, *Granville's New Key to Stock Market Profits* — On Balance Volume.
- Jonathan Karpoff, "The Relation Between Price Changes and Trading Volume: A
  Survey", *Journal of Financial and Quantitative Analysis* (1987).
- Simon Gervais, Ron Kaniel and Dan Mingelgrin, "The High-Volume Return Premium",
  *Journal of Finance* (2001).
- Charles Lee and Bhaskaran Swaminathan, "Price Momentum and Trading Volume",
  *Journal of Finance* (2000).
