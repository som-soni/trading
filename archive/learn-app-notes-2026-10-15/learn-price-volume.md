# App notes moved out of learn-price-volume (verbatim)

## Intro: app/backtest framing
selling climaxes and volume on results days. The claims are checked against the
app's own backtest trades and against every breakout in its stored prices. The
answer is more modest than most books suggest. This guide is about one **stock**.

## Intro: "Where this shows in the app" and "The data" (backtest trade lists — removed from the guide)
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

## §2 Relative volume (the app's convention)
1.0 is a normal day. 2.0 is twice normal. 0.5 is half. The app uses the 50-day
average everywhere a rule tests volume (the stored `vol_sma50`, which includes
today). The Chart page's volume line is a 20-day average, so it will look a
little different.

## §3.1 The app's rules and §3.2 The app's backtest trades (backtest evidence — removed; replaced by a next-day-volume event study)
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

## §4 How the app tests it (dry-up)
**How the app tests it.** The Minervini strategy's base detector
(`core/vcp_spec.py`, rule VCP-10) takes the final tight area of the base — the
bars since the last pullback low, at most `TIGHT_DAYS` = 10. It requires their
average volume to be **at most `DRYUP_RATIO` = 0.70×** the 50-day average. The
50-day average is taken from the bar *before* the tight area. Otherwise the quiet
days themselves would lower the benchmark and make the test too easy to pass. The
older, superseded Minervini strategy used a looser test: tight-area volume above
1.0× its average raised flag V2.

## §5.1 What the app counts (demand/supply verdict)
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

## §5.2 (app use of the verdict)
far above the medians are pulled up by a few big rebounds. The app uses the
verdict as a **veto inside a pullback setup**, not as a forecast. That is the
right use: a pullback on heavy selling is a different thing from a quiet one.

## §5.3 Pocket pivots (app note)
of the prior 10 sessions**. Their idea is that a fund's buying shows up before
the stock breaks out. This is their method. The app does not compute pocket
pivots, and I have not tested them here.

## §6 Climax runs: the app's Minervini exit EX-05 / EX-06 and backtest result
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
on 17 November added an 8% jump. On 22 November the price was 70% above its
200-day average — the app's third climax test. That day it made a new intraday

## §7 (app strategy note)
- **Do not buy the capitulation day itself.** A strategy in this app buys
  strength — a stock back above its averages, in a base, with rising RS. A
  selling climax only tells you to start watching.

## §8 Results days: Emami backtest trade and gate B7
caption: On the day its results were filed, Emami rose 16.8% on 13.2× its average volume, closing above its January high. The India chart-pattern backtest bought it the next day and reached its target in July (+3.85R). The stock peaked 60% above the pre-results close in August.
Emami had traded below its January high for five months. On 30 May 2024, the
day its quarterly results were filed, it rose 16.8% on 13.2× average volume and
closed above that high. It added 11% more on 5 June, on 5.2×. The India
chart-pattern backtest bought it on 31 May at 612 with a stop at 568. It sold at
the 783 target on 9 July. The stock went on to 840 by 28 August.

**Most strategies here refuse new trades near results** (gate B7 in the Volume
breakout: no results within 10 days). A results gap is something you react to
afterwards, not something to hold through by design.

## §9 India: data notes
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

## §11 Evidence (backtest bullets)
- **Supported here, weakly:** in the backtests, entry days on above-average volume
  won more often. The effect on average R was small and within chance in most runs.
  The Volume breakout run's 40 signals at 3× or more did best, on a small sample.
- **Caveats:** daily bars only; survivorship bias in all the data; my breakout test
  is a simple stand-in for the patterns traders actually draw. None of the
  backtests here beats simply buying the index.

## §12 Checklist (app items)
- [ ] Trend pullback candidates: the demand/supply verdict — "Supply in control" means wait
- [ ] Markets → Post-market → Stocks: the unusual-volume lists for new names
