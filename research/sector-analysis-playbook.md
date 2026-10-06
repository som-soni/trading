# Sector analysis playbook

**Premise (a learning from my own trading):** returns come mostly from being in
the right *group* at the right time, then owning the strongest companies in it.
Stock-level analysis (price action, fundamentals) is well covered elsewhere; this
document is about the level above it — how to judge sectors and industry
groups now, and how to find the next growth areas early.

It is a living document with two halves: **processes** to follow, and a
**tools roadmap** to build them into this repository. Tick items off as they
land; move findings into `momentum-trend-research.md` once they are backtested.

> Not investment advice. Every rule here is a hypothesis until a backtest in
> this repository says otherwise (see §6, Phase 2).

---

## 1. Two different questions

| | Question | Nature | Reliability | Tool |
|---|---|---|---|---|
| **A** | Which sectors / industries are leading *now*? | Measurable from prices and earnings | High — it is observation | Sectors page, breadth, RS |
| **B** | Which areas will grow *next*? | A thesis about the future | Lower — it is a forecast | Thesis log, theme watchlists |

Rule that joins them: **the thesis tells you where to look; relative strength
tells you when.** Never act on B until A confirms it.

Top-down order of every decision: **market → sector → industry group → stock.**
Check the Breadth page first — in a weak market even leading groups fall.

---

## 2. Process A — analysing a sector at any point in time

Work through the layers in this order; the first three come from price data
alone and are on the Sectors page.

### 2.1 Relative strength (the most important single signal)
- Return vs the market over **1, 3, 6, 12 months**. A leader is ahead on most
  horizons, not one.
- **RS line** (group ÷ market): a new high in the RS line *before* the price
  makes one is the earliest sign of leadership.
- **RS rating 1–99** and its **change over a month**: groups jumping 20–30
  points are coming into favour before they top the table.
- **Relative Rotation Graph**: groups rotate clockwise through
  Improving → Leading → Weakening → Lagging. *Improving* is where new leaders
  appear; *Weakening* is where you tighten stops.

### 2.2 Granularity — industry, not sector
- Broad sectors hide opposite moves (semiconductors vs software vs IT services
  are all "Technology").
- Rank ~145 industry groups. O'Neil/IBD's research attributes a large share of
  a stock's move to its industry group.

### 2.3 Breadth inside the group (is the move healthy?)
- % of members above the 50- and 200-day averages; new 52-week highs vs lows.
- **Equal-weight vs cap-weight** return: EW ≥ CW = broad participation;
  CW ≫ EW = a few giants carrying it (fragile).
- Healthy leadership *broadens* week after week (more members making highs).

### 2.4 Fundamentals at group level (is it backed by earnings?)
- **Earnings revisions**: analysts raising estimates across the group — the
  most reliable fundamental signal of a sustained run.
- Revenue growth **accelerating**, margins expanding.
- Order books / backlogs (India: capital goods, defence, railways, EPC).
- Valuation is a poor timing tool: leaders look expensive; **cyclicals peak
  when P/E looks cheapest** (peak earnings).

### 2.5 Macro, cycle and policy (why is it moving?)
- Business cycle tendencies: early recovery — financials, discretionary,
  industrials; late cycle — energy, materials; slowdown — staples, utilities,
  healthcare.
- Rates: banks, real estate, long-duration growth.
- Commodities: metals, oil & gas, chemicals (input costs).
- **India: policy is often the driver** — government capex (2021–24 capital
  goods, railways, defence), PLI schemes (electronics manufacturing),
  defence indigenisation, PSU re-rating.

### 2.6 Leaders inside a leading group
Rank members by: RS vs the market and vs the group, distance from the 52-week
high (closer is better), earnings growth, quality score. Leaders are the
**first to break out and the last to break down.**

### 2.7 When a group's run is ending
- Leaders start failing (breaking 50-day lines on volume) while the group index
  still looks fine.
- Breadth narrows: fewer members at highs, EW lagging CW.
- RRG moves into *Weakening*; RS rating falls 20+ points in a month.
- Late signals of crowding: wave of IPOs in the theme, new thematic ETFs/funds,
  magazine covers.

### 2.8 Routine

**Weekly (30 min, weekend):**
1. Breadth page — market risk-on or risk-off?
2. Sectors page — top 15 industry groups by RS; note new entrants and the
   biggest RS-rating gains (Δ).
3. Rotation graph — which groups moved into *Improving* / *Leading*;
   which into *Weakening*.
4. For each top group: open the leaders, check charts; add candidates to a
   watchlist named after the group.
5. Check open positions: is each still in a top-third group? If its group
   slipped to *Weakening*/*Lagging*, tighten the stop.
6. Log changes in the journal (§5).

**Monthly:**
1. Review each active theme's thesis (§3) against new evidence.
2. Compare the group ranking with a month ago — persistence matters more than
   one week's rank.
3. Review closed trades: were the winners in top-ranked groups? (This feeds
   Phase 2.)

**Quarterly (earnings season):**
1. Read earnings commentary of the 2–3 largest companies in each top group and
   of the big *spenders* feeding it (customers' capex guidance).
2. Update order book / revision notes per theme.

---

## 3. Process B — identifying future growth areas

### 3.1 Where to look
- **Follow the capex**: who has committed multi-year budgets, and who supplies
  them? (Hyperscaler AI capex → chips → networking, power equipment, cooling,
  utilities. India infrastructure capex → cement, capital goods, EPC.)
- **Bottlenecks and pricing power**: lengthening lead times, rising backlogs,
  suppliers raising prices — demand is outrunning supply, which produces
  earnings upgrades.
- **Policy with money behind it**: subsidies, mandates, procurement
  (CHIPS Act, IRA, PLI, defence indigenisation, energy transition targets).
- **Adoption S-curves**: the steepest growth is roughly from 10% to 50%
  penetration — early enough to have runway, late enough to be real.
- **Structural shifts**: demographics and rising incomes (India consumption,
  financialisation — AMCs, brokers, insurers; healthcare).
- **Cost curves**: a falling unit cost (solar, batteries, sequencing) opens new
  markets.

### 3.2 Thesis template (one per theme)
```
Theme:              e.g. Power equipment for data centres
Date opened:        YYYY-MM-DD
Thesis (2 lines):   what demand, from whom, why now
Evidence for:       capex guidance, order books, revisions, policy
Evidence against:   capacity additions, competition, valuation, customer concentration
Industry groups:    which Yahoo industries / which stocks express it
Confirmation:       RS rating > 70 and rising; quadrant Improving/Leading; breadth broadening
Invalidation:       what would prove it wrong (and the price signal: group RS < 40, Lagging)
Status:             watching / confirmed / active / closed — with dates
```

### 3.3 Traps
- **Growth ≠ returns.** Growth attracts capital, capacity and competition
  (solar 2008–12, airlines). Look for barriers to entry.
- **Hype cycles.** Dot-com, EVs 2021, cannabis: a real story, an absurd price,
  a long drawdown. Price confirmation plus exit rules protect you.
- **Late signals**: thematic ETF launches, IPO waves, mainstream coverage.
- **Narrative without numbers**: no revisions, no order book, no margin
  expansion = not yet investable.

---

## 4. Signals reference

| Signal | Where | Meaning | Status |
|---|---|---|---|
| Group RS rating 1–99 + Δ 1M | Sectors page | Leadership and its direction | ✅ built |
| EW / CW returns 1W–12M, relative to the market | Sectors page | Strength and participation | ✅ built |
| RRG quadrant + tail | Sectors page | Rotation stage | ✅ built |
| % > 50 / 200 DMA, 52w highs vs lows | Sectors page | Breadth inside the group | ✅ built |
| Leaders ranked by RS, quality, distance from high | Sectors page | Stock selection within the group | ✅ built |
| Market breadth / risk | Breadth page | Whether to be aggressive at all | ✅ built |
| Earnings revisions by group | — | Fundamental confirmation | ⬜ Phase 4 |
| Revenue / margin trend by group | — | Fundamental confirmation | ⬜ Phase 4 |
| Group RS history & alerts | — | Catch new leaders early | ⬜ Phase 5 |
| Theme baskets | — | Track a thesis that spans industries | ⬜ Phase 6 |

---

## 5. Journal

Keep a dated entry each weekly review: top 10 groups, new entrants, groups
leaving, actions taken. After three months this becomes the data for judging
whether the process works. Template:

```
## YYYY-MM-DD  (market: US / India; breadth: risk-on/neutral/risk-off)
Top groups:      …
New / rising:    …
Weakening:       …
Actions:         …
Theme notes:     …
```

---

## 6. Tools roadmap

### Phase 1 — Sectors page ✅
- [x] Industry classification for both markets (`marketdata/industries.py`,
      table `symbol_industry`; Yahoo sectors/industries + market cap)
- [x] Group analytics (`marketdata/sectors.py`): EW/CW returns, relative
      returns, RS rating + Δ, breadth, RRG, ranked members
- [x] Web page **Sectors**: ranking table, rotation graph, group detail with
      group-vs-market chart and leaders

### Phase 2 — Test the learning (backtest) ⬜
- [ ] Point-in-time group RS rating for every historical day (store as a
      table, like `breadth_daily`)
- [ ] Add an optional gate to the swing strategies: only take setups in groups
      with RS rating ≥ N (try N = 50, 70, 80) — document it per `CLAUDE.md`
- [ ] Backtest with vs without, both markets; record in the research ledger
- [ ] Variant: rank candidates by group RS instead of filtering
- [ ] Caveat to quantify: classification is today's (look-ahead), and
      survivorship bias

### Phase 3 — Group context everywhere ⬜
- [ ] Group RS rating and quadrant as columns in screening results and the
      watchlist panel
- [ ] Chart details block: the symbol's group, its RS rating, and the stock's
      rank inside the group
- [ ] Daily summary: groups entering / leaving the top 20

### Phase 4 — Fundamentals by group ⬜
- [ ] Aggregate revenue growth, margin trend and earnings growth by industry
      from `fundamentals_raw`
- [ ] Earnings-estimate revisions (source to find: Yahoo `earnings_trend` /
      `eps_revisions` per stock, aggregated by group)
- [ ] India: order-book notes per theme (manual, in the thesis log)

### Phase 5 — History and alerts ⬜
- [ ] Store daily group RS ratings; chart a group's RS rating over time
- [ ] Alerts: group enters *Improving* / *Leading*, RS Δ ≥ 20 in a month,
      breadth broadening (members at highs rising 3 weeks running)

### Phase 6 — Themes ⬜
- [ ] Theme = named basket of stocks across industries (reuse watchlists),
      with the same analytics as a group (EW index, RS, RRG point)
- [ ] Thesis log page: the §3.2 template per theme, with status and dates

### Phase 7 — India refinements ⬜
- [ ] NSE industry classification (Nifty Total Market list) as an alternative
      grouping; NSE sectoral indices on the rotation graph
- [ ] Policy calendar notes (budget, PLI, defence procurement) per theme

---

## 7. Further reading
- William O'Neil, *How to Make Money in Stocks* — industry group ranks, leaders vs laggards.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — stage analysis, sector-first selection.
- Mark Minervini, *Trade Like a Stock Market Wizard* — leadership, relative strength.
- Julius de Kempenaer — Relative Rotation Graphs (relativerotationgraphs.com).
- Sam Stovall, *Standard & Poor's Guide to Sector Investing* — sector behaviour across the business cycle.
