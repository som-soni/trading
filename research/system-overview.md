# My trading system — overview (draft)

The operating procedure I trade by: what I look at, in what order, and how each reading becomes a decision. It is
assembled from the creator research notes and from what this repository has measured. **Every rule starts as
proposed.** It moves to *adopted* when I decide to follow it, and to *tested* when a backtest or event study here
supports it. A rule the data contradicts is marked *rejected* and kept, with the reason.

**In short**

- One system, cut three ways: **horizon** (position, swing, short-term), **side** (long, short) and **instrument** (cash
  shares, or futures and options). Each horizon is a **book** with its own slice of risk.
- Everything is **planned at the close on daily bars**. Short-term means 1–5 sessions, not same-day trades; intraday
  trading is a decision deferred until it can be tested (§1).
- One chain of decisions, top-down: **market → exposure and bias → sectors → stocks → setups → instrument → risk →
  management → review**. Each step answers one question and has its own tab.
- **Entry and exit are TBD** in every book: they will be set from strategies that pass their tests. Until then the
  creators' setups are *candidates under study*, and size comes from the market and my results.
- The one thing this repository has measured to help — across strategies — is **when to be in the market**, not which
  pattern to buy. So the daily review comes first and has the final say on size.

---

## 1. What the system trades

### 1.1 The books

| Book | Holding period | Chart | Planned | Longs | Shorts | F&O (India) |
|---|---|---|---|---|---|---|
| **Position** | Months, while the trend holds | Weekly and daily | Weekend | Leaders in groups leading for 4+ weeks | Former leaders in Stage 4 | Long futures; hedges on the book |
| **Swing** | Days to a few weeks | Daily | Each evening | Leaders in leading and emerging groups | Bounces into resistance in breaking groups | Long and short futures; bought options |
| **Short-term** | 1–5 sessions | Daily | Each evening | Fast movers in the week's strongest groups | First failed bounces | Bought options at probe size |

Pages: [Longs](system-swing-longs.md), [Shorts](system-shorts.md), [F&O and leverage](system-fno-leverage.md). Each book's
share of open risk is set on [risk and exposure](system-risk-exposure.md) §2.

**Not in the playbook: investing for years.** Buying quality companies to hold through cycles is a different job, with its
own pages — Screens → Quality companies (the long-term tracker) and Library → Sector research (dated sector theses). The
position book is a trade: it has a stop and leaves when the trend ends.

### 1.2 Planned at the close — and why not intraday

Every trade, short-term included, is planned on daily bars after the close; orders (a buy-stop at the pivot, a stop) are set
the evening before, and the session itself is for execution only. No position is opened and closed in the same session.

Intraday trading is **deferred, not rejected**. What it would need:

| Need | Today |
|---|---|
| Intraday prices, stored | None. India's minute bars could come from the broker's read-only history endpoint (a new download job); US minute bars need a paid vendor |
| A test of any intraday rule | Impossible until those are stored — and every edge measured here so far is on daily bars |
| Attention | The US session runs through the Indian night (19:00–01:30 or 20:00–02:30) |

Intraday charts keep one job: **timing an entry the daily plan already chose** — an opening-range break, or an hourly retest
of an average (Luk, Kullamägi). The trigger is intraday; the trade is not.

### 1.3 Instruments

**Cash shares** in both markets. **Futures and options in India only** (NSE): a stock future for a long or an overnight
short, a bought option or debit spread where gap risk is too large, and index hedges. No naked option selling, no US
options (their history is paid). Details and limits: [F&O and leverage](system-fno-leverage.md).

### 1.4 How the strategies fit

The system has two dials (principle P2, §3), and the strategies are one of them:

| Dial | Question | Where it lives | How it is tested |
|---|---|---|---|
| **Setup** | *Whether* to trade this stock, at what entry, stop and exit | The strategies (Strategies page; Today's setups) — each a coded, backtested version of a setup on the [Longs](system-swing-longs.md) or [Shorts](system-shorts.md) page | Backtests, in stages |
| **Exposure** | *How much* to trade today, on which side | The daily review: the market snapshot's readings and the rules over them | Rule studies; the strategies' market gate in backtests |
| **Me** | Whether I followed both, and whether it pays *me* | The journal | My own trades |

Three links tie them together:
- **A setup on the system pages becomes a strategy** when it can be coded and backtested (L1, the base breakout, is the
  Minervini strategy; Shorts §7 specifies the next one). **A strategy becomes a book's entry and exit rule** when it passes
  its verify run — that is how the TBD boxes get filled.
- **The strategies' market gate is a review reading.** The market snapshot shows the gate the backtests use, so a rule
  proven in a backtest (the market filter, progressive exposure) is the same rule the review applies.
- **A strategy's live setups are the hunt list.** The review says which setups to hunt today; Today's setups lists what the
  strategies found. I trade the intersection with the week's [Sectors → stocks](system-sector-selection.md) list, sized by
  the review.

## 2. The decision chain

| # | Step | The question it answers | Cadence | Tab | Status |
|---|---|---|---|---|---|
| 1 | Market | Which regime are we in, and is the index stretched? | Daily | [Daily review](system-daily-market-review.md) | Draft |
| 2 | Exposure and bias | How much risk, long or short, and at what size tier? | Daily | [Daily review](system-daily-market-review.md) §4, [Risk](system-risk-exposure.md) | Draft |
| 3 | Sectors | Which groups lead, which are emerging, which are breaking? | Weekly; daily glance | [Sectors → stocks](system-sector-selection.md) | Draft |
| 4 | Stocks | Which stocks in those groups, for which book? | Weekly | [Sectors → stocks](system-sector-selection.md) §4–5; Scans & reports | Draft |
| 5 | Setups — long | Which pattern, which pivot? | Daily | [Longs](system-swing-longs.md) | Candidates; entry TBD |
| 6 | Setups — short | Bouncing into what? | Daily | [Shorts](system-shorts.md) | Candidates; entry TBD |
| 7 | Instrument | Cash, a future or an option? | Per trade | [F&O and leverage](system-fno-leverage.md) §3 | Draft |
| 8 | Risk and sizing | Risk per trade, per book, open risk, leverage, overrides | Per trade, daily | [Risk](system-risk-exposure.md) | Draft |
| 9 | Management | Partials, trailing, covering, earnings | Per position, daily | Longs §5, Shorts §6 | Candidates; exit TBD |
| 10 | Review | Did I follow the plan; what is working? | Weekly, monthly | [App manual](app-guide-pages.md) §11 (routine), journal notes | To write |

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
| P8 | **Entry and exit come from a tested strategy.** A creator's setup is a candidate until a strategy built on it passes verify | — | Most strategies here have not passed verify; the TBD boxes stay until one does |
| P9 | **Leverage expresses a decision; it never makes one.** F&O is sized by its worst case, and a probe is never open-ended | SEBI: about 93% of individual F&O traders lost money, FY22–FY24 | Untested here ([F&O and leverage](system-fno-leverage.md) §6) |
| P10 | **One job per timeframe.** Weekly sets the trend, daily finds the setup, and the entry is a buy-stop left resting. Do not flip timeframes to talk myself into a trade | Reddit post, u/bradgohtrades (Nov 2026), lessons 1 and 4 | Matches §1.2 (planned at the close on daily bars) |
| P11 | **Waiting is a position.** No setup at its level means no order. If I have to argue for a setup, it is not one | Same post, lessons 2–4; Minervini (no chasing) | Untested as a rule. The written strategy gates are the "clear rules" |
| P12 | **Hands off between closes.** Once the stop and exit are set, the trade is reviewed at the close, not watched intraday. Exits come from the plan, not from how a candle feels | Same post, lessons 6–7 | **Supported:** early-weakness exits lowered the average in every replay, and managed exits lost to unmanaged ones in the base-breakout strategies ([swing longs](system-swing-longs.md) §5–6; [strategy review](strategy-review-summary.md)) |

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
| u/bradgohtrades (Reddit post, Nov 2026) | None: a short text post, so no research note. An intraday forex trader; the "$10K → $291K student" claim is marketing, not evidence | Principles P10–P12; Swing longs (§5 "would I enter now?", marked rejected); Risk (§1 size by tolerance); Tools (§4 run after exit). Not used: lesson 5, trading London/New York hours, and lesson 7's 15-minute chart, both intraday |

## 5. Tools

The system is built from four general parts rather than one tool per rule, so it can take in any number of sources.
Details on [Tools for the trading system](system-tools.md).

| Part | What it is | Status |
|---|---|---|
| **Market snapshot** | Every review reading, per market and session, point in time: each index against its averages, distribution days, breadth, volatility, the strategies' market gate, cap- vs broad-index ratios | **Built** (5 Nov 2026) — Today → Market readings |
| **Rule registry** | Each rule as a condition over the readings, with its effect, sources and status; the adopted rules that fire show on Today's Market card | Next |
| **Journal** | My trades (with the stop planned at entry) and each day's call | Then |
| **Rule study** | Any rule tested on stored history, inside the backtest stages | Then |
