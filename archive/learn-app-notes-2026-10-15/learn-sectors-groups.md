# App notes moved out of learn-sectors-groups

## Intro — "Where this shows in the app" and background links (verbatim)

**Where this shows in the app.**

- Markets → **Sectors** (`scripts/swing_screener/analytics/sectors.py`): the
  ranking table, the **Rotation** graph and each group's page.
- Markets → Post-market (Sectors tab).
- The chart's details panel: sector › industry group › sub-industry, each a
  link.
- The screen fields *Group RS rating*, *Peer group RS* and *Rank in peer
  group*, and the screen **Strong stocks in leading groups**.

Background: [the sector playbook](sector-analysis-playbook.md), [the taxonomy
note](sector-taxonomy.md), [the group-strength study](group-strength-study.md).

## §1 — level table as it stood (verbatim; the 'In this app' column was removed)

| Level | In this app | Count | Use it for |
|---|---|---|---|
| **Sector** | Yahoo's sectors | 11 | Context: is Technology or Energy leading? |
| **Industry group** | Yahoo's industries (similar to GICS, the standard industry classification) | ~145; on a typical day ~130 US and ~60 Indian groups have enough members to rate | **The main unit**: RS rating, rotation, leaders |
| **Sub-industry** | The app's own splits of large, mixed groups | dozens | Where one group holds businesses that move apart |

Both markets use Yahoo's classification, refreshed monthly. The third level,
sub-industries, is chosen by hand for this app. You can edit it under System →
Sub-industries (it is stored in `data/sub_industries.csv`, plus rules in
`marketdata/subindustries.py`). Examples of the splits
([the taxonomy note](sector-taxonomy.md)):

- US semiconductors into AI & compute, analog & power, RF & mobile, memory and
  foundry;
- US regional banks by size;
- India's banks into **PSU** (government-owned), **private** and small-finance;
- India's engineering & construction into railway PSUs, roads, power EPC
  (companies that design and build power projects) and more.

## §1 — last paragraph (app-specific sentences)

- "So the app rates a group only when it has **3+** liquid members. The screens compare a stock with its sub-industry only when that has 3+ tradable stocks; otherwise they use its industry group."

## §2 — the group-strength study framing and the backtest paragraph (verbatim)

Those are practitioners' claims. This app tested the idea over five years of
month-ends ([the study](group-strength-study.md)). It used only the data
available at each month-end, with no hindsight. "Strong" means the stock's
peer group was rated 80+; "weak" means below 50. The "t" figure in brackets is
a t-statistic: roughly, how far a result stands out from chance. The bigger it
is, the less likely the difference is luck. "Stage 2" is Weinstein's advancing
stage: a stock above a rising 30-week average.

| 1-month return difference | US | India |
|---|---|---|
| Tradable stocks: strong group vs weak group | +0.67% (t 1.5) | **+1.36% (t 2.9)** |
| Stage 2: strong group vs weak group | +0.46% (t 0.9) | +1.16% (t 1.7) |
| Stage 2: top 3 in its group vs the rest | +0.32% (t 0.8) | +0.17% (t 0.2) |
| "Strong stocks in leading groups" vs all Stage 2 | +0.13% (t 0.5) | +0.27% (t 0.8) |
| Rated by sub-industry vs by industry group | −0.01% (t 0.0) | +0.27% (t 0.5) |

**Group strength helps**: clearly in India, suggestively in the US. Over six
months, stocks in strong groups beat the average stock by about 3.1% in the US
and 2.5% in India. **Being the group's #1 added nothing.** Sub-industries help
you *see* leadership, but they did not forecast better. The study covers only
five years and one kind of market, and it is exposed to survivorship bias
(stocks that later disappeared may be missing). Treat it as suggestive, not
settled.

One backtest agrees. In the superseded Minervini strategy, a backtest option
skipped signals from industry groups rated below 50 (`--min-group-rs 50` in
`backtesting/backtest.py`). It lifted the yearly return in India from 5.0% to
6.3%, and in the US from −1.7% to 1.8% (Strategies → Minervini SEPA
(superseded)).

## §3 How the Sectors page rates a group (verbatim, whole section)

## 3. How the Sectors page rates a group

Pick the market in the header, and the level with **Sectors / Industry groups
/ Sub-industries**. Everything is recomputed daily from stored prices.

**Which stocks, and the group's index.** The page uses common stocks trading at
least **$2M a day** at a price of $3+ (India: **₹2 Cr** a day at ₹10+). A
group's index is **equal-weight**: each day it takes its members' average
return, and compounds those. Any single-day move beyond ±50% is cut back to
±50%. The yardstick is the **typical stock** (the equal-weight average of all
of them), not the S&P 500 or the Nifty.

**RS rating (1–99) and Δ 1M.** The rating starts from the group's return
relative to the typical stock. The return is weighted **40% 3 months, 20% each
6, 9 and 12 months**. Groups are then ranked against each other, like IBD's
group ranks: 99 is the strongest, 50 the middle. **Δ 1M** is the change in the
rating against 21 trading days ago. A 20–30 point jump often marks a group
coming into favour before it reaches the top of the table.

Two consequences follow:

- **It is a rank, not a return.** A group rated 90 can be falling, if
  everything else falls faster.
- **It is slow.** Most of its weight is on 6–12 months. So a turn shows first
  in the RS line (the group's index divided by the typical stock's) and in Δ
  1M (§4.1).

The app rebuilds the same rating for every past day since 2013, and the charts
here draw that history (`group_rs_history`, built by
`analytics/group_history.py`). India's is rebuilt on fewer days: roughly
100–210 a year, against 210–250 for the US.

**Rotation graph (weekly).** It plots each group on two measures:

- **RS-Ratio** (across) = 100 × the group's RS line ÷ its 10-week average.
  Right of 100, the group's relative strength is trending up.
- **RS-Momentum** (up) = 100 × RS-Ratio ÷ its value 4 weeks ago. Above 100,
  that trend is improving.

Each group has a tail showing its path over the last 8 weeks.

| Quadrant | RS-Ratio | RS-Momentum | Reading |
|---|---|---|---|
| **Leading** | ≥ 100 | ≥ 100 | Ahead, and pulling further ahead |
| **Weakening** | ≥ 100 | < 100 | Still ahead, losing pace — tighten stops |
| **Lagging** | < 100 | < 100 | Behind and falling further behind |
| **Improving** | < 100 | ≥ 100 | Behind but catching up — where new leaders show first |

Groups *tend* to move clockwise (Improving → Leading → Weakening → Lagging).
But a sell-off can drop one straight from Leading to Lagging. The graph shows
the table's top 6–20 rows; the filter buttons ("chips") show one
quadrant at a time.

**Breadth inside the group.** **> 50D** / **> 200D** is the share of members
above those averages. **Highs / lows** counts members at a new 52-week closing
high / low. This is market breadth one level down. **Leadership that keeps
spreading to more members is sturdier than a rally carried by two or three
names.** A group's page adds "Up over 3 months", and a **Returns** table. It
shows **equal-weight** returns (the typical member) beside **cap-weight**
returns (dominated by the big names). Cap-weight far above equal-weight means a
few giants are carrying the group.

**Members.** The **Leaders** column shows each group's top three by the RS
composite score. A group's page ranks every member by RS, returns, distance
from the 52-week high, trend and quality. It charts the group against the
typical stock with its RS line, and has **Add top 10 to a watchlist…**.

**Elsewhere.** Post-market's **Group leadership changes** lists ratings
rising and falling over the last few sessions and quadrant changes since the
day before.

## §4.1 — app sentence

- "Watch Δ 1M and the group page's RS line for the turn."

## §4.6 — table with the 'Where in the app' column (verbatim)

| Stage | What you see | Where in the app |
|---|---|---|
| Early warning | RS line peaks and turns down; Δ 1M turns negative | Group page RS line; Δ 1M column |
| Rotation | Leading → Weakening | Rotation graph; Post-market rotation changes |
| Leaders fail | Top names break their 50-day lines while the group looks fine | Leaders column; members table |
| Breadth narrows | Fewer members at highs; > 50D falling; cap-weight carrying equal-weight | > 50D, Highs / lows; Returns table |
| Confirmation | Rating below 50; Lagging | RS column |

## §5 — method sentence

- "Method: take the stored history of group ratings (`group_rs_history`) on the last stored day of each month, 2013 to October 2026."

## §6 — app sentence

- "On the Sectors page, at sector level, Utilities, Staples and Healthcare moving into Leading says the same thing."

## §7 India specifics — app sentences

- "**Sector indices** (Nifty Bank, IT, Pharma are stored) are cap-weighted and dominated by a few names. The Sectors page shows the typical member instead (§4.5)."
- "That is why the app splits **PSU banks** from **private banks**. It also splits the **govt. infra & power lenders** from other NBFCs (non-bank lenders)."
- "One or two stocks can swing a small group, so check the **Stocks** column."

## §8 What the trader does — top-down routine (verbatim)

**The top-down routine.**

1. **Market**: is the index in an uptrend, and is breadth healthy?
   ([trend](learn-health-trend.md), [breadth](learn-health-breadth.md)). The
   rating is relative, so in a falling market leading groups fall too.
2. **Sector**: at the Sectors level, find the two or three leaders, and what is
   moving into Improving.
3. **Group**: at the Industry groups level, sorted by RS, look at the top
   15–20, the biggest Δ 1M gains and the Improving quadrant. Open large, mixed
   groups at the sub-industry level.
4. **Leaders**: on each top group's page, look for Stage 2 charts near their
   52-week highs, forming proper bases ([the bases guide](learn-bases.md)). Use **Add top 10
   to a watchlist…**. The **Strong stocks in leading groups** screen does steps
   3–4 in one pass. Its conditions: tradable, peer group RS **80+**, stock RS
   rank **70+**, above the 50- and 200-day (`screens/definitions.py`).
5. **Entry**: only now look for setups in those names.

## §9 — backtest sentence

- "A group filter also improved one superseded strategy's backtest."
- "This app's persistence numbers (§5) agree."

## §10 Checklist (verbatim)

## 10. Checklist

- [ ] Market first: index trend and breadth (Markets → Breadth)
- [ ] Sectors level: the leading sectors; anything new in Improving
- [ ] Industry groups: top 15–20 by RS; biggest Δ 1M gains and losses
- [ ] Large, mixed groups: check the sub-industry level
- [ ] Each top group: > 50D and highs vs lows broadening; equal-weight
      keeping up with cap-weight
- [ ] Post-market → Sectors: group leadership and quadrant changes
- [ ] Watchlist: RS 70+ stocks in groups rated 80+, Stage 2, near highs
- [ ] No more than two or three positions from one group
- [ ] Holdings: each one's group still above 50 and not Weakening?
- [ ] Groups that ran far and fast: wait for a base, do not chase
- [ ] Journal the top groups and what changed

## Further reading — app documents

- This app: [the sector playbook](sector-analysis-playbook.md),
  [the group-strength study](group-strength-study.md),
  [the taxonomy note](sector-taxonomy.md).
