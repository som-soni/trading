# Trading

A local, data-only system for screening and backtesting equity strategies in
the **US** and **India** markets. No LLM calls at runtime, no screenshots —
price data from yfinance, stored in Postgres, run from the command line.

Two things live here: a **screener** that produces a daily list of trade
candidates, and a **backtester** that measures whether a strategy is worth
running at all.

> **Read [`research/`](research/) before trusting any strategy in this repo.**
> The findings so far: the hand-built `trend_pullback` strategy has no edge in
> either market, while simple cross-sectional momentum beats the index in
> India (+6.23% CAGR) but not the US. The results ledger, methodology and known
> biases are all there.

---

## Quick start

```bash
cd scripts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Needs a local Postgres with a `trading` database. Put credentials in
`scripts/.env` (gitignored):

```
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=<yours>
PGDATABASE=trading
```

Then pull history — **do this first; nothing is trustworthy on two years of
data**:

```bash
PYTHONPATH=. python3 -m swing_screener.marketdata.backfill --market india --years 16
```

---

## What do you want to do?

Every command runs from `scripts/` with `PYTHONPATH=.` set.

### Screens and strategies

Two separate things, kept apart in code and in the web app:

- A **screen** answers *which stocks are worth looking at?* — qualification
  criteria only, no entry or stop. Four screens (`swing_screener/screens/`):
  **Stage 2 — Trend Template** (Minervini's eight criteria, with a true RS
  rank), **Established uptrend**, **Near highs, rising 200-day**, **Above the
  200-day**. A screen is a list of **conditions** over a daily **stock
  snapshot** (~50 fields per stock: returns, RS rank, averages, 52-week range,
  volatility, volume, trend structure, sector), so it runs as a live query —
  and you can build your own in the web app, like Chartink or Screener.in.
  The built-in screens' conditions are proven to return exactly what their
  coded criteria (shared with the strategies) return. A fifth built-in,
  **Strong stocks in leading groups**, uses the peer-group fields: stocks with RS
  70+ whose peer group (sub-industry, else industry group) is rated RS 80+, in an
  uptrend. Every list (screen results, today's setups, strategy setups, movers,
  watchlists) shows each stock's peer group and its RS badge, and "Clusters"
  chips show the peer groups several stocks share. Group RS is rebuilt for
  every past month-end (`analytics/group_history.py`, matching the Sectors page),
  so screens on group strength can be studied too, and
  [research/group-strength-study.md](research/group-strength-study.md) (refreshed
  monthly) tests whether group strength improves forward returns. A screen is judged by a
  **screen study**, on demand: on each month-end of the last five years, did
  its qualifiers beat the other tradable stocks over the next 1/3/6 months?
- A **strategy** answers *is there a trade, and how do I take it?* It draws its
  candidates from one screen and adds its own trade rules, setups,
  entry/stop/target, exits and sizing. Strategies are **backtested**.

| Strategy | Key | Draws from screen |
|---|---|---|
| Minervini SEPA | `minervini` | Stage 2 — Trend Template |
| Trend pullback | `trend_pullback` | Established uptrend |
| Volume breakout | `breakout` | Near highs, rising 200-day |
| Chart patterns | `chart_pattern` | Near highs, rising 200-day |
| Donchian channel | `donchian` | Above the 200-day |

One strategy per idea. Earlier implementations of the same two ideas
(`minervini_legacy`, `chart_pattern_legacy`, `chart_pattern_cup`) are no longer
registered — their modules stay in the tree, and the git history of their
`status` attributes keeps their measured results readable.

Every strategy carries a `version`, and `versions.lock.json` records the
version alongside a fingerprint of its tunables. **A backtest refuses to start
when the code's rules are not the ones recorded for its version**, naming the
parameter that moved — so a result can always be mapped back to the rules that
produced it. Change a threshold, raise `version`, add a changelog entry, then
`python3 -m swing_screener.strategies.versions --update`. An unrecorded
experiment can still run via `--vcp` / `--const`, which carry their own
fingerprint into the run directory and signal cache.

In the web app: **Screens** — one page, the screens on the left (built-in,
Quality, yours, "+ New screen"), the chosen one on the right (Results ·
Criteria · Study; any session of the last 40) and the screen builder with a
live preview and study — and **Strategies** (Today's setups across all
strategies, one page per strategy with Setups today · Rules · Backtests).

```bash
python -m jobs run screens --market us                     # today's stock snapshot (every screen queries it)
python -m jobs run strategies --market us --strategies all # today's setups for every strategy
python -m jobs run screen_history --market india           # month-end snapshots for the study (first run: 5 years)
python3 -m swing_screener.screening.pipeline --market india --strategy breakout   # one strategy, by hand
```

A strategy run writes `reports/<market>_<strategy>_universe.csv` — one row per
stock its screen passed, with every gate, flag and decision as its own column.

### The daily update, and checking it ran

Offline work is split into **jobs** in layers — reference data, market data,
analytics, screening, publish — run alone or chained into pipelines, so you
can pull data without screening, or re-screen without pulling:

The **daily** pipeline is data only — universe check → prices → indexes →
breadth → sectors → the screens' snapshot → post-market analysis. Strategies
(today's setups) and the Quality scores run **on demand**: the **strategies**
and **quality** pipelines.

Everything goes through a **job queue** (`jobs/queue.py`, in Postgres) that one
**worker** runs, one job at a time. The web app adds to it (**System → Schedules →
Run now** per pipeline, **System → Runs**: Resume a failed run, run a single
job; **Today's setups → Run strategies…**), and so do **schedules** (**System →
Schedules**: daily data for India at 18:30 Mon–Fri and the US at 07:00 Tue–Sat,
weekly reference data Saturday 10:00, monthly classification on the 1st —
edit, pause, add, run now). A slot missed while the computer slept runs once
when the worker next looks. No cron.

```bash
python -m jobs worker --install                   # once: a launchd agent keeps the worker running (logs/worker.log)
python -m jobs enqueue strategies --market india  # add to the queue (same arguments as run)
python -m jobs queue                              # running, waiting, recently finished
python -m jobs schedules                          # the schedules and their next run
python -m jobs run prices --market india          # run now, in this terminal (bypasses the queue)
python -m jobs list                               # every job, its layer, cadence and last run
```

**System → Status** shows the queue (Stop, cancel, run next) and the worker.
Without the launchd agent, **Start worker** there starts one
(until the next reboot). Changing anything is allowed only from the machine
running the app.

Screening reads stored prices only and refuses prices two or more trading days
old. Every step is logged with timestamps and its result. **System → Status**
(also the dot and date in the header) shows how current each dataset is against
the trading day it should have reached, and the job queue; **System → Runs**
shows every run step by step — live while it runs — with errors, the log tail
and every job's last run per market. Details: `scripts/README.md` → Jobs.

### Understand why one stock did or didn't qualify

```bash
python3 -m swing_screener.screening.inspect --market india --symbol RELIANCE.NS
```

Gate-by-gate pass/fail with reasons, watch flags, setups, and the entry plan
and sizing if it clears everything. `--fresh` bypasses the cache.

### See what changed since yesterday

```bash
python3 -m swing_screener.screening.history --market india          # diff last two runs
python3 -m swing_screener.screening.history --market india --list   # list recorded runs
```

### Backtest a strategy

```bash
# portfolio-level: one capital pool, position cap, costs — the default
python3 -m swing_screener.backtesting.backtest --market india --start 2013-01-01

# a seeded random subset, for speed
python3 -m swing_screener.backtesting.backtest --market india --start 2013-01-01 --sample 500

# a different strategy
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 --strategy breakout

# let winners run instead of taking a fixed target
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 \
    --exit-mode donchian --no-target

# Minervini, exactly as research/minervini-backtest-spec.md defines it. EN-01 is the confirmed
# breakout (next open); add "TRADE ON TRIGGER" for EN-02, the buy-stop through the pivot. Taking
# only EN-01 tests a small minority of the setups the strategy finds — on India, 27 of 831.
python3 -m swing_screener.backtesting.backtest --market india --start 2010-01-01 \
    --strategy minervini --spec \
    --accept-labels "TRADE - HIGH CONFIDENCE,TRADE ON TRIGGER" [--market-filter]

# just these names — the pre-filter still applies to each, and the report names them
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 \
    --strategy minervini --symbols NVDA,MU,GOOG

# one-off experiments. Both change the spec fingerprint, so a variant gets its own
# signal cache and run directory and cannot overwrite the shipped rules' results.
python3 -m swing_screener.backtesting.backtest --market india --start 2010-01-01 \
    --strategy minervini --vcp shrink=0.5 --const MIN_STRUCTURAL_R=0
```

Produces `reports/<market>/<strategy>/<run>/` containing `report.md` (with
charts), `trades.csv`, `equity.csv`, `figures/` and `funnel.json`.

**The funnel** is the part worth reading first. It counts what reached each
stage — universe, pre-filter, hard gates, setup, entry trigger, trade plan,
decision, ranking, trades — and why the rest stopped, taken from the rule that
actually refused: the gate code for a hard gate, the strategy's own failure
code for a setup, the plan's own sentence for a reward-to-risk floor. It names
the symbols scanned when there are 25 or fewer. Where a loss cannot be
attributed to a named rule it says so, rather than implying a complete account.
`GET /api/reports/{id}/funnel` serves it, and it is a section in `report.md`.

Scanning enriches each symbol once rather than once per bar, which is 4–5x
faster than it was (minervini on five India symbols: 48.3s → 11.6s, signals
byte-identical). Repeat runs of the same `spec_id` hit the signal cache and are
faster again; changing a rule changes the `spec_id`, so the next run is cold.

### Compare a strategy against the momentum baseline

```bash
python3 -m swing_screener.backtesting.baseline --market india --start 2013-01-01 \
    --top-n 50 --rebalance QE --cost-bps 25
```

Rank by 12-1 month momentum, hold the top N, rebalance, exit on dropping out.
Two real parameters. **Any strategy that cannot beat this is not worth its
complexity.**

### Test one variable at a time

```bash
# which exit policy is best, on an identical signal set
python3 -m swing_screener.backtesting.experiments --market india --start 2013-01-01 \
    --sample 500 --exits

# how sensitive is it to the position cap
python3 -m swing_screener.backtesting.experiments --market india --start 2013-01-01 \
    --sample 500 --caps

# risk-per-trade and notional cap together: can the book afford its own slots?
python3 -m swing_screener.backtesting.experiments --market us --start 2013-01-01 \
    --strategy donchian --sample 500 --sizing \
    --exit-mode donchian --no-target --donchian-bars 50
```

**`--caps` and `--sizing` hold the exit policy fixed while varying one other
thing, so pass the strategy's real exit policy.** They default to
`bracket`+target; donchian measured with a fixed target is not donchian, and
the mistake is invisible in the output unless you check the trade count and
median holding days against the strategy's own run.

### Change position sizing

`max_positions` x `max_position_pct` can exceed 100% of capital, in which case
the book runs out of cash before it runs out of slots and silently declines
most signals. Both markets ship 10 slots x 25% = 250%.

```bash
python3 -m swing_screener.backtesting.backtest --market us --start 2013-01-01 \
    --strategy donchian --exit-mode donchian --no-target \
    --risk-pct 0.005 --max-position-pct 0.15
```

The sizing appears in the run directory name, so configurations don't
overwrite each other. Check `report.md` for the line reporting how many
signals were declined for insufficient cash — if it dwarfs the trade count,
the book is the binding constraint, not the strategy.

### Decide when to put money into the index

A separate question from which stock to buy, so a separate suite — SIP
timing, trend overlays, allocation and rotation, on dividend-inclusive index
series going back to 1980 (US) and 1997 (India).

```bash
# once: fetch total-return index series, then check them for vendor artefacts
python3 -m swing_screener.marketdata.index_data --refresh
python3 -m swing_screener.marketdata.index_data --validate

python3 -m swing_screener.backtesting.index_investing --market us
python3 -m swing_screener.backtesting.index_investing --market india --family A
```

Four families: **A** contribution timing (day-of-month, day-of-week,
frequency, lump sum vs DCA, dip-buying, value averaging), **B** lump-sum
timing overlays, **C** static allocation and rebalancing cadence, **D**
rotation between index sleeves. Results carry pre-tax *and* after-tax columns,
cash earns the real T-bill/liquid-fund rate, and every calendar experiment is
scored against a randomised-day null — because the best of 30 contribution
days is a selected maximum before it is a finding. See
[`research/index-investing-research.md`](research/index-investing-research.md).

### Browse charts and reports in a web UI

A read-only viewer: TradingView-style price charts (candles, volume, SMAs,
RSI, daily/weekly/monthly), the screener's entry/stop/target levels drawn on the
chart, backtest trades overlaid as markers, plus every screening run and
backtest/index report. Strategies still run offline; this only displays results.

```bash
cd scripts
PYTHONPATH=. python3 -m swing_screener.web          # http://127.0.0.1:8000
```

Pages are grouped by what they are about: **Markets** (Post-market — tabs
Summary · Sectors · Stocks · Yours — Breadth, Sectors, Movers) → **Screens**
(overview, one page per screen, Quality, the screen builder) → **Strategies**
(Today's setups, one page per strategy with its setups, rules and backtests) →
**Chart** → **Watchlists** → **Library** (Notes, Playbook, TODO) → **System**
(Status, Runs, Schedules, Reports archive). A section link opens its first page;
a section with several pages shows them as a tab row under the header. The
header holds the **market selector** (it applies to every page), search
(**⌘K / Ctrl+K**: a page, or a stock by symbol or company), the data dot (the
selected market's latest price date; System → Status on click) and **⚙**
(theme — Black, Graphite, Light or match the system — density, keyboard
shortcuts, load reports). Alt + 1…7 jumps to a section, Alt + [ / ] to the
previous / next page in it, Alt + 0 to Status. Explanations sit behind **ⓘ**
buttons and "How to read this page" links. On
narrow windows the sections fold into a ☰ menu.

The **Strategies** page explains every strategy — thesis, each hard gate,
watch flag and setup, entry/stop/target and exit rules, live parameter values
per market, and its backtest results. It is generated from the strategy
classes themselves (`strategies/docs.py`), and
`PYTHONPATH=. python3 -m tests.test_strategy_docs` fails when a strategy's
code and documentation drift apart — run it after any strategy change (see
`CLAUDE.md`).

Reports (`report.md`, figures, trades, equity, CSVs) and `research/*.md` are
loaded into Postgres (`report_runs`, `report_figures`, `report_tables`) at
startup, and again with **⚙ → Load reports from disk** or
`python3 -m swing_screener.web.ingest` after a new run. Prices and screener
history come from the existing `prices` / `universe_history` / `index_series`
tables.

Company names (shown next to tickers everywhere, and searchable — "apple",
"tata motors") live in `symbol_names`, taken from the exchanges' own lists:
Nasdaq Trader for the US, NSE's main-board, SME and ETF lists for India. The
server fills the table on first start and a universe refresh updates it; to
refresh by hand:

```bash
PYTHONPATH=. python3 -m swing_screener.marketdata.names
```

### Keep watchlists

Watchlists work like TradingView's. **Screener picks** is a built-in list that
every full screening run updates: a name is on it while its strategy marks it
`tradeable` or `watchlist_candidate` (the same rule as the daily summary's
watchlist section) and drops off when it no longer does. Removing a name from
it hides it until it drops off the screen and is flagged again, so the next run
doesn't put it straight back.

Your own lists ("My watchlist", plus any you create) hold whatever you add and
the screener never touches them; one list can mix US and India symbols. On the
chart, the icon bar on the far right opens the Watchlist panel (as in
TradingView): click the list name to switch lists or create one, **+** adds a
symbol from any market, **⋯** renames or deletes the list, the Symbol / Last /
Chg / Chg% headers sort it, and right-clicking a row adds it to another list or
removes it. ↑ / ↓ step through the list; details for the open symbol sit
underneath. ☆ next to the symbol toggles it in the active list, and
right-clicking ☆ picks any list. Drag the panel's left edge to resize it. The
Watchlist page shows every list as a table with notes. From the command line:

```bash
python3 -m swing_screener.screening.watchlist --show
python3 -m swing_screener.screening.watchlist --add AAPL --market us --note "breakout above 235" [--list "Breakouts"]
python3 -m swing_screener.screening.watchlist --remove AAPL --market us [--list "Breakouts"]
python3 -m swing_screener.screening.watchlist --sync-latest   # rebuild Screener picks from the latest recorded runs
```

### Keep notes and a trading journal

**Research › Notes** is a Markdown notebook stored in Postgres (`notes`): a
searchable list (text, `#tags`, linked stocks) beside an editor with live
preview that saves as you type. New notes can start from a template — daily
journal, trade plan, trade review. Link a note to stocks and it appears in the
chart's details panel for that stock, where "+ note" starts one already linked.
Delete has Undo; to keep a copy outside the database:

```bash
python3 -m swing_screener.notes --export notes_export/   # one .md file per note
```

### Review the day after the close

The web app's **Markets › Post-market** page is the day's recap for each market,
kept for every trading day (`postmarket_daily`; step back through history with
‹ › or the tone timeline): a market-tone verdict from six signals (index vs its
50/200-day averages, advancers vs decliners, new highs vs lows, % above the
50-day, volatility), index cards, breadth vs the previous day and 10-day
average, every sector's and the strongest/weakest industries' day move,
group-leadership changes, top gainers/losers, unusual volume, new 52-week
highs/lows, how your watchlists did (50-day crosses, new highs, earnings soon),
what changed in each strategy's screen, and earnings in the next 10 days. The
`daily` pipeline writes it after screening; to build or backfill by hand:

```bash
python -m jobs run postmarket --market india --days 60    # last 60 sessions
```

### Sub-industries: which business each company is in

Groups that mix businesses are split one level further (Semiconductors → AI &
compute, Analog, Memory…; India's Electrical Equipment → T&D, Cables, Consumer
electricals…), and every tradable stock in such a group is labelled. Each label
records its source — your edit, the curated list (`data/sub_industries.csv`),
a rule, a suggestion awaiting review (`data/sub_industries_suggested.csv`), an
official code mapped to a sub-industry (`data/sub_industry_codes.csv`), or for
India BSE's own industry — and **Library → Sub-industries** lists each group's
stocks with their label, source and official code (BSE's industry for India,
Nasdaq's SIC-based industry for the US) so you can review, relabel one or many,
accept suggestions, or create a sub-industry. The monthly `subindustries` job
fetches the codes for new listings. `python -m swing_screener.marketdata.subindustries
--export` writes your portal labels into the curated CSV. Design:
`research/sector-taxonomy.md`.

### Find the leading sectors and industry groups

The web app's **Sectors** page ranks every Yahoo sector, industry group
(~140 in the US, ~85 in India) and — for groups that mix businesses —
sub-industry by an RS rating (1–99, IBD-style: 40% 3-month,
20% each 6/9/12-month return relative to the typical stock) and its change
over the month, with equal- and cap-weight returns, breadth inside the group
(% above the 50/200-day averages, new highs vs lows), a weekly Relative
Rotation Graph (Leading / Improving / Weakening / Lagging), and each group's
members ranked strongest first — one click saves the top 10 to a watchlist.
The method, the weekly routine and the roadmap are in
[research/sector-analysis-playbook.md](research/sector-analysis-playbook.md).

```bash
python3 -m swing_screener.marketdata.industries            # classify stocks (~5 min; monthly)
python3 -m swing_screener.marketdata.sectors --market us   # the ranking in the terminal
```

### See the top gainers and losers

The web app's **Movers** page lists the top 25 gainers and losers for the US
and India from the latest day in the database, over 1D / 1W / 1M / 3M / 6M /
YTD / 1Y, with each market's index change, the up/down count, relative volume
(the last day's volume ÷ its 50-day average) and traded value. "Liquid stocks"
(the default) keeps common stocks trading at least $10M a day (₹10 Cr in India)
priced at $5 / ₹20 or more; "All stocks" drops that filter. Click a row to open
its chart and step through the list with ↑ / ↓. Prices are not adjusted for
spin-offs, so a demerger can appear as a large drop.

### Check market breadth (how risky is the market?)

How the 1,000 most-traded stocks are doing as a group, for India and the US:
52-week highs vs lows, % above the 5- and 50-day averages, rising vs falling,
sector leadership, and options' expected vs actual volatility (India VIX / VIX)
— each ranked against every trading day since 2015. It judges risk, not
direction. See the web app's **Breadth** page.

```bash
python3 -m swing_screener.marketdata.breadth --market india --full --classify   # once: history + stock/fund labels
python3 -m swing_screener.marketdata.breadth --market us --full                 # once
python3 -m swing_screener.marketdata.breadth --market us                        # catch up (the page also does this itself)
```

### Track quality companies, and buy them at the right price

Long-term investing, separate from the swing strategies: score companies on
up to five years of annual statements (return on capital, growth, margins,
cash conversion, debt, dilution, Piotroski F-score), then judge today's price
(FCF yield, P/E against the company's own history, PEG; dip from the 52-week
high, distance from the 200-day average, RSI). The web app's **Quality** page
shows BUY ZONE / ACCUMULATE / WAIT, lets you track companies and set your own
buy-below price; the full rules are under "How the signals work" there and on
the Strategies page.

```bash
python3 -m fundamentals.quality --market us --top 500      # the most liquid US companies
python3 -m fundamentals.quality --market india --top 300
python3 -m fundamentals.quality --tracked                  # just the companies you track
```

Statements are fetched with yfinance (~1.5 s per company) and re-fetched only
when older than 30 days; prices come from the database, so the price verdicts
update with every new close without re-running anything. Not investment advice.

### Re-render a finished run as a report

```bash
python3 -m swing_screener.backtesting.report --list
python3 -m swing_screener.backtesting.report \
    --market india --strategy momentum_baseline --run 2013-01-01_top20_mom252_ME_25bps
```

No re-simulation — it rebuilds from the run's saved CSVs.

---

## Layout

```
trading/
  scripts/        code — see scripts/README.md for the full guide
    swing_screener/
      core/           indicators, swings, chart patterns, context — strategy-agnostic
      strategies/     one file per strategy, behind one interface
      backtesting/    simulator, metrics, reports, baseline, experiments,
                      index-investing suite (core/allocate/accumulate/stats)
      marketdata/     cache, Postgres, universes, backfill
      screening/      the daily screener pipeline
      web/            read-only viewer (FastAPI + static JS) and report ingest
    fundamentals/     long-term investing: quality scores + "is the price right?" (separate from swing trading)
    tests/            behaviour-preservation harness
  data/           inputs: universe lists, earnings overrides
  reports/        generated output — one directory per run (gitignored)
  logs/           run logs (gitignored)
  research/       findings: results ledger, methodology, known biases
  archive/        superseded material, kept not deleted
```

## Further reading

| | |
|---|---|
| [`scripts/README.md`](scripts/README.md) | Full command reference, how the strategy works gate by gate, known gaps |
| [`research/`](research/) | What has been tested and what the numbers were |
| [`research/index-investing-research.md`](research/index-investing-research.md) | Index investing: SIP timing, overlays, allocation — results and caveats |
| [`archive/README.md`](archive/README.md) | The original prompts and how they diverge from the code |

## A caution

The backtests here apply point-in-time screening, pessimistic fills, realistic
costs and portfolio-level capital constraints — but they still carry
**survivorship bias** (the universe is today's listed names) and have not been
validated out of sample. Nothing in this repository is investment advice.
