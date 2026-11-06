# My trading system — overview (draft)

The operating procedure I trade by: what I look at, in what order, and how each reading becomes a decision. It is
assembled from the creator research notes and from what this repository has measured. **Every rule starts as
proposed.** It moves to *adopted* when I decide to follow it, and to *tested* when a backtest or event study here
supports it. A rule the data contradicts is marked *rejected* and kept, with the reason.

**In short**

- **Swing and position trades, planned at the close** — not day trading. Intraday charts only time an entry the
  daily plan already chose.
- One chain of decisions, top-down: **market → exposure and bias → groups → setups → execution → risk → management →
  review**. Each step answers one question, and each has its own page.
- Two dials, never one: **the setup decides *whether* to trade; the market and my own recent results decide *how much***.
- The one thing this repository has measured to help — across strategies — is **when to be in the market**, not which
  pattern to buy. So the daily market review comes first and has the final say on size.
- Sources so far: [Martin Luk](creator-martin-luk.md) (short-side swing timing, tape-scaled risk) and
  [Mark Minervini](creator-mark-minervini.md) (finding leaders in a decline, progressive exposure). Each new creator
  adds to the same pages.

---

## 1. What the system trades — and what it doesn't

**Swing and position trades, decided at the close.** A swing trade is held for days to a few weeks: a breakout from a base,
a pullback in a trend, a short on a bounce. A position is a true leader held for the trend, months if it keeps working
([swing longs](system-swing-longs.md) §5). Both are planned on daily bars after the close; orders (a buy-stop at the pivot, a stop) are set
the evening before; the session itself is for execution only.

**Not day trading.** No position is opened and closed on the same day by design. The reasons are practical, not
dogmatic: no intraday prices are stored, so nothing intraday can be tested here; the US session runs through the Indian
night; and every edge this repository has measured is on daily bars. Intraday charts still have one job: **timing an entry
the daily plan already chose** — an opening-range break, or an hourly retest of an average (Luk, Kullamägi). The trigger
is intraday; the trade is a swing.

**So the daily market review is for swing decisions.** Its output (rung, bias, risk tier, hunt, events) sets how much
risk, on which side, and in which setups for the *next* session's swing entries, and whether open positions should be
reduced. It is not a scan for intraday opportunities.

**How the strategies fit.** The system has two dials (principle P2, §3), and the strategies are one of them:

| Dial | Question | Where it lives | How it is tested |
|---|---|---|---|
| **Setup** | *Whether* to trade this stock, at what entry, stop and exit | The strategies (Strategies page; Today's setups) — each a coded, backtested version of a setup on the [swing longs](system-swing-longs.md) or [shorts](system-shorts.md) page | Backtests, in stages |
| **Exposure** | *How much* to trade today, on which side | The daily review: the market snapshot's readings and the rules over them | Rule studies; the strategies' market gate in backtests |
| **Me** | Whether I followed both, and whether it pays *me* | The journal | My own trades |

Three links tie them together:
- **A setup on the system pages becomes a strategy** when it can be coded and backtested (L1, the base breakout, is the
  Minervini strategy; Shorts §7 specifies the next one). An untested setup is a candidate for a strategy.
- **The strategies' market gate is a review reading.** The market snapshot shows the gate the backtests use, so a rule
  proven in a backtest (the market filter, progressive exposure) is the same rule the review applies.
- **A strategy's live setups are the hunt list.** The review says which setups to hunt today; Today's setups lists what the
  strategies found. I trade the intersection, sized by the review.

## 2. The decision chain

| # | Step | The question it answers | Cadence | Page | Status |
|---|---|---|---|---|---|
| 1 | Market | Which regime are we in, and is the index stretched? | Daily | [Daily market review](system-daily-market-review.md) | Draft |
| 2 | Exposure and bias | How much risk, long or short, and at what size tier? | Daily | [Daily market review](system-daily-market-review.md) §4, [Risk and exposure](system-risk-exposure.md) | Draft |
| 3 | Groups | Where is the strength — or the breakdown? | Daily glance, weekly in depth | [Sector analysis playbook](sector-analysis-playbook.md) | Exists |
| 4 | Setups — long | Which stocks, which pattern, which pivot? | Daily | [Swing longs](system-swing-longs.md) | Draft |
| 5 | Setups — short | Which weak stocks, bouncing into what? | Daily | [Shorts](system-shorts.md) | Draft |
| 6 | Execution | Which trigger, which timeframe, which order? | Per trade | In 4 and 5 | Draft |
| 7 | Risk and sizing | Risk per trade, open risk, overrides | Per trade, daily | [Risk and exposure](system-risk-exposure.md) | Draft |
| 8 | Management | Partials, trailing, covering, earnings | Per position, daily | In 4 and 5 | Draft |
| 9 | Review | Did I follow the plan; what is working? | Weekly, monthly | [App manual](app-guide-pages.md) §11 (routine), journal notes | To write |

## 3. Principles

| # | Principle | Sources | Evidence here |
|---|---|---|---|
| P1 | **Regime first.** Whether to be invested matters more than the pattern | Minervini: start from cash after a correction, toes in the water; Luk: risk scaled to the tape | Tested: the market filter is the one rule that improved both return and drawdown ([strategy families](app-guide-strategy-families.md) §5) |
| P2 | **Two dials.** Setup quality decides *whether*; market and recent results decide *how much* | Luk (probes at 0.02–0.1% on a poor day); Minervini (buy a few, add if they work) | Progressive exposure cut the Minervini strategy's US drawdown on its own ([Minervini notes](creator-mark-minervini.md) §9.2) |
| P3 | **Let price and my own trades lead,** not news and opinions | Minervini/Ritchie: shut off the news; Luk: study alone, chat rooms are noise | — |
| P4 | **Be wrong fast and cheap.** The stop is set before entry and never moved against me | Luk: never move a stop after entry; Minervini: the right price is where it moves quickly | — |
| P5 | **Longs and shorts are managed differently.** Shorts are covered into weakness | Luk | Untested here |
| P6 | **No hot-hand sizing.** After a strong run, raise size more slowly than equity grows | Luk; also the process rules in [video strategy notes](video-strategy-notes.md) §2 | — |
| P7 | **A creator's example is not a base rate.** Check the population before adopting a selection rule | — | "Held up best" lost to the average stock in three sell-offs ([relative strength](learn-price-rs.md) §4.3) |

## 4. How material gets in — the three places

Every creator video or stream goes to three places, in this order:

1. **Research note** — `creator-<name>.md`: what they said, faithfully, with timestamps, using the shared template
   ([Martin Luk](creator-martin-luk.md) §0). Claims about named stocks are checked against stored prices.
2. **Learn** — the generalizable mechanism, folded into an existing `learn-*.md` guide under the Learn rules (no creator
   names or their numbers; evidence from stored data).
3. **This system** — each decision the creator makes is added to the matching page here as a *proposed* rule, with its
   source, so the pages consolidate everyone's views into one procedure.

| Creator | Note | Feeds |
|---|---|---|
| Martin Luk | [creator-martin-luk.md](creator-martin-luk.md) — stream of 3 Nov 2026 | Daily review (stretch, narrow vs broad, events), Shorts, Risk (probes, anti-hot-hand) |
| Mark Minervini | [creator-mark-minervini.md](creator-mark-minervini.md) — webinar, mid-2022 | Daily review (setup supply, feedback), Swing longs (leaders in a decline), Risk (progressive exposure) |

## 5. Tools

The system is built from four general parts rather than one tool per rule, so it can take in any number of sources.
Details on [Tools for the trading system](system-tools.md).

| Part | What it is | Status |
|---|---|---|
| **Market snapshot** | Every review reading, per market and session, point in time: each index against its averages, distribution days, breadth, volatility, the strategies' market gate, cap- vs broad-index ratios | **Built** (5 Nov 2026) — Today → Market readings |
| **Rule registry** | Each rule as a condition over the readings, with its effect, sources and status; the adopted rules that fire show on Today's Market card | Next |
| **Journal** | My trades (with the stop planned at entry) and each day's call | Then |
| **Rule study** | Any rule tested on stored history, inside the backtest stages | Then |
