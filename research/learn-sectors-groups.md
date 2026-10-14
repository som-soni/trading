# Sectors and groups — why leaders cluster, and how money rotates between them

Learning material: the level above the single stock — why a stock's group
matters, how this app rates groups, what leadership looked like in the
stored data and how it ended, and the top-down routine that uses it.
Companion to [the business-cycle guide](learn-macro-cycle.md) and
[the breadth guide](learn-health-breadth.md).

**Where this shows in the app.** Markets → **Sectors**
(`scripts/swing_screener/analytics/sectors.py`): the ranking table, the
**Rotation** graph and each group's page. Also Markets → Post-market
(Sectors tab), the chart's details panel (sector › industry group ›
sub-industry, each a link), the screen fields *Group RS rating*, *Peer group
RS* and *Rank in peer group*, and the screen **Strong stocks in leading
groups**. Background: [the sector playbook](sector-analysis-playbook.md),
[the taxonomy note](sector-taxonomy.md), [the group-strength study](group-strength-study.md).

---

## 1. Sector, industry group, sub-industry

| Level | In this app | Count | Use it for |
|---|---|---|---|
| **Sector** | Yahoo's sectors | 11 | Context: is Technology or Energy leading? |
| **Industry group** | Yahoo's industries (GICS-like) | ~145; on a typical day ~130 US and ~60 Indian groups have enough members to rate | **The main unit**: RS rating, rotation, leaders |
| **Sub-industry** | The app's own splits of large, mixed groups | dozens | Where one group holds businesses that move apart |

Both markets use Yahoo's classification, refreshed monthly. The third level
is curated (`data/sub_industries.csv` plus rules in
`marketdata/subindustries.py`; edit under System → Sub-industries): US
semiconductors into AI & compute, analog & power, RF & mobile, memory and
foundry; US regional banks by size; India's banks into **PSU**, **private**
and small-finance; India's engineering & construction into railway PSUs,
roads, power EPC and more ([the taxonomy note](sector-taxonomy.md)).

**Why granularity matters.** "Technology" holds chip makers, software and IT
services — different customers, cycles and valuations. Even one industry
group can hide two stories:

```series
title: One industry group, two stories — US semiconductors 2023–2024
from: 2023-01-01
to: 2024-12-31
line: us:grs.industry.Semiconductors | Semiconductors (industry group) RS
line: us:grs.sub.Semiconductors_›_AI_&_compute | AI & compute (sub-industry) RS
caption: Through late 2023 and early 2024 the whole group sat in the 30s–40s while its AI & compute names stayed near 90 — the group average hid where the leadership was.
```

At the end of September 2023 the Semiconductors group was rated **49** and
its AI & compute sub-industry **91**; at the end of March 2024, **35**
against **88**. Finer is not automatically better, though: with three stocks,
one stock's move *is* the group. The app rates a group only with **3+**
liquid members, and the screens compare a stock with its sub-industry only
when that has 3+ tradable stocks (else its industry group).

## 2. Why groups matter

Stocks in a group share customers, input costs, regulation and rate
exposure, and when a fund wants more of a theme it buys the whole group — so
they rise and fall together. William O'Neil **claimed that a large share of
a stock's move comes from its industry group and sector**, and that most big
winners came from leading groups; Minervini looks for the strongest stocks
*in the strongest groups*. Those are practitioners' claims. This app tested
the idea point in time over five years of month-ends
([the study](group-strength-study.md)); "strong" = peer group rated 80+,
"weak" = below 50:

| 1-month return difference | US | India |
|---|---|---|
| Tradable stocks: strong group vs weak group | +0.67% (t 1.5) | **+1.36% (t 2.9)** |
| Stage 2: strong group vs weak group | +0.46% (t 0.9) | +1.16% (t 1.7) |
| Stage 2: top 3 in its group vs the rest | +0.32% (t 0.8) | +0.17% (t 0.2) |
| "Strong stocks in leading groups" vs all Stage 2 | +0.13% (t 0.5) | +0.27% (t 0.8) |
| Rated by sub-industry vs by industry group | −0.01% (t 0.0) | +0.27% (t 0.5) |

**Group strength helps** — clearly in India, suggestively in the US (over
six months, stocks in strong groups beat the average stock by about 3.1% in
the US and 2.5% in India). **Being the group's #1 added nothing**, and
sub-industries help you *see* leadership but did not forecast better. Five
years, one regime, survivorship: suggestive, not settled.

One backtest agrees: in the superseded Minervini strategy, skipping signals
from industry groups rated below 50 (`--min-group-rs 50`, a backtest option
in `backtesting/backtest.py`) lifted yearly return in India from 5.0% to 6.3%
and in the US from −1.7% to 1.8% (Strategies → Minervini SEPA (superseded)).

## 3. How the Sectors page rates a group

Pick the market in the header and the level with **Sectors / Industry groups
/ Sub-industries**. Everything is recomputed daily from stored prices.

**Universe and index.** Common stocks trading at least **$2M a day** at $3+
(India **₹2 Cr** at ₹10+). A group's index is **equal-weight** — its members'
average daily return, compounded, with any single-day move beyond ±50%
clipped. The yardstick is the **typical stock** (the equal-weight average of
all of them), not the S&P 500 or the Nifty.

**RS rating (1–99) and Δ 1M.** The group's return relative to the typical
stock, weighted **40% 3 months, 20% each 6, 9 and 12 months**, ranked across
groups like IBD's group ranks: 99 strongest, 50 the middle. **Δ 1M** is the
change against 21 trading days ago; a 20–30 point jump often marks a group
coming into favour before it tops the table. Two consequences: **it is a
rank, not a return** (a group rated 90 can be falling, if everything else
falls faster), and **it is slow** — most of its weight is on 6–12 months, so a
turn shows first in the RS line and Δ 1M (§4.1). The same rating is rebuilt
for every past day since 2013 in `group_rs_history`
(`analytics/group_history.py`), which the charts here draw; India's is
rebuilt on fewer days (roughly 100–210 a year against 210–250 for the US).

**Rotation graph (weekly).** **RS-Ratio** (across) = 100 × the group's RS
line ÷ its 10-week average: right of 100, relative strength is trending up.
**RS-Momentum** (up) = 100 × RS-Ratio ÷ its value 4 weeks ago: above 100, that
trend is improving. Each group has an 8-week tail.

| Quadrant | RS-Ratio | RS-Momentum | Reading |
|---|---|---|---|
| **Leading** | ≥ 100 | ≥ 100 | Ahead, and pulling further ahead |
| **Weakening** | ≥ 100 | < 100 | Still ahead, losing pace — tighten stops |
| **Lagging** | < 100 | < 100 | Behind and falling further behind |
| **Improving** | < 100 | ≥ 100 | Behind but catching up — where new leaders show first |

Groups *tend* to move clockwise (Improving → Leading → Weakening →
Lagging), but a sell-off can drop one straight from Leading to Lagging. The
graph shows the table's top 6–20 rows; the chips filter by quadrant.

**Breadth inside the group.** **> 50D** / **> 200D** (share of members above
those averages) and **Highs / lows** (members at a new 52-week closing high
/ low) — market breadth one level down: **leadership that keeps broadening is
sturdier than a rally carried by two or three names.** A group's page adds
"Up over 3 months" and a **Returns** table with **equal-weight** (typical
member) beside **cap-weight** (big names): cap-weight far above
equal-weight means a few giants carry the group.

**Members.** The **Leaders** column shows each group's top three by the RS
composite. A group's page ranks every member with RS, returns, distance from
the 52-week high, trend and quality, charts the group against the typical
stock with its RS line, and has **Add top 10 to a watchlist…**.

**Elsewhere.** Post-market's **Group leadership changes** lists ratings
rising and falling over the last few sessions and quadrant changes since the
day before.

## 4. What leadership looks like — and how it ends

### 4.1 US energy, 2021–2022: the rating lagged the top

Oil & Gas E&P was the weakest group in 2019 (rated **2** in July). From
February 2021 it stayed 80+ for nearly two years, never below the mid-70s,
peaking at **99** in June 2022. Over 2021–2022 XLE rose about **131%**; the
S&P 500 (total return) about 5%.

```series
title: US energy leadership, 2020–2023 — sector vs market, and the E&P group's rating
from: 2020-06-01
to: 2023-12-31
line: us:XLE / us:SP500_TR | Energy (XLE) ÷ S&P 500 total return
line: us:grs.industry.Oil_&_Gas_E&P | Oil & Gas E&P group RS | pane2
band: 2021-02-08 2023-01-03 | E&P rated 80+
mark: 2022-11-07 | Relative strength peaks
caption: The RS line nearly tripled from its late-2020 low and peaked on 7 November 2022; the rating was still 95 on 1 December and collapsed only in January–February 2023.
```

XLE's strength against the market peaked on **7 November 2022**; the group
was still rated **95** on 1 December, **44** at the end of January and **6**
by mid-February, while XLE fell about 18% from mid-November to mid-March.
**The RS line turns first; the rating confirms later.** Watch Δ 1M and the
group page's RS line for the turn. Oil's own drivers are in
[the commodities guide](learn-macro-commodities.md).

### 4.2 Same rate shock, opposite groups

Homebuilders and regional banks are both "rate-sensitive"
([the rates guide](learn-macro-rates.md)); in 2023 they sat at opposite ends.

```series
title: Homebuilders vs regional banks, 2022–2024 — group RS ratings
from: 2022-07-01
to: 2024-12-31
line: us:grs.industry.Banks—Regional | Regional banks RS
line: us:grs.industry.Residential_Construction | Homebuilders (Residential Construction) RS
mark: 2023-03-10 | Silicon Valley Bank fails
caption: Regional banks were already rated in the 20s before SVB failed and spent spring 2023 near the bottom; homebuilders were rated 80+ from January 2023 to May 2024.
```

Regional banks were rated **21** at the end of January 2023 and **24** on 8
March, *before* Silicon Valley Bank failed on 10 March; **3** at the end of
March and **2** in early May. The rating did not predict the failure, but it
kept a group-aware trader out beforehand. Homebuilders were rated 80+ from
January 2023 to May 2024 (about 16 months, averaging 96) and **17** by the
end of 2024. **A macro label does not tell you the direction; the rating
tells you what the market is doing.**

### 4.3 Semiconductors: leadership lost twice, and regained

Semiconductors were 80+ from July 2016 to September 2017 (about 14 months),
fell to **9** in October 2018, and broke twice more this decade:

```series
title: Semiconductors' rating and the S&P 500, 2021–2026
from: 2021-06-01
line: us:SP500_TR | S&P 500 total return | log
line: us:grs.industry.Semiconductors | Semiconductors group RS | pane2
band: 2021-12-01 2022-09-15 | RS 95 → 16
band: 2025-01-17 2025-04-10 | RS 88 → 13
caption: Both breaks came with a falling market. In 2025 the group was back above 80 within three months and has held around 80 or higher since October 2025.
```

- **2022:** **95** on 1 December 2021, **16** by mid-September 2022, as the
  S&P 500 (total return) fell about 25% from January to October.
- **2025:** **88** in mid-January, **13** on 10 April, as the S&P 500 fell
  about 19% from February to early April; **83** by the end of June, 79 or
  higher since October 2025, **98** in May 2026.

A leader that breaks in a sell-off is not necessarily finished; a quick
return to 80+ as the market recovers is how one often re-announces itself.

### 4.4 India: railways and defence, 2022–2024

India's biggest recent group runs had policy behind them: government
capital spending on railways and infrastructure, and the push to build
defence equipment at home.

```series
title: India's policy-driven leaders — defence and railway PSU ratings, 2022–2025
from: 2022-01-01
to: 2025-12-31
line: india:grs.industry.Aerospace_&_Defense | Aerospace & defence RS
line: india:grs.sub.Engineering_&_Construction_›_Govt._&_railway_infra_(PSU) | Railway & govt. infra PSUs RS
caption: Both were rated 80+ for most of late 2022 to September 2024. Then railway PSUs fell to 7 by February 2025, while defence dipped and recovered.
```

**Aerospace & defence** was 80+ from May 2022 to September 2024 (27 months,
averaging 92), dipped to **33** in February 2025 and was **97** by the end of
June 2025. **Railway & govt. infra PSUs** (RVNL, IRCON and peers) went from
**14** in mid-2022 to **96** by December, held 80+ to September 2024 apart
from a dip into the 60s–70s in February 2023, peaked at **98** in July 2024,
then fell to **50** by the end of October and **7** by the end of February
2025 — and have not led since. One theme carried both; only one recovered.

### 4.5 India IT, 2022: know your yardstick

```series
title: Nifty IT against the Nifty 50, and the IT services group's rating, 2020–2023
from: 2020-01-01
to: 2023-06-30
line: india:^CNXIT / india:^NSEI | Nifty IT ÷ Nifty 50
line: india:grs.industry.Information_Technology_Services | IT services group RS | pane2
caption: The equal-weight rating was already falling through late 2021, while the cap-weighted Nifty IT kept gaining on the Nifty 50 until the last days of the year.
```

Nifty IT rose about **250%** from the March 2020 low to its 4 January 2022
peak. The IT services group was rated **98** in December 2020 but **71** at
the end of 2021 and **65** in mid-January 2022, while Nifty IT ÷ Nifty 50
peaked only on **30 December 2021**. In 2022 Nifty IT fell about 27% while
the Nifty 50 rose about 4%; the group was rated **5** by September. They
disagreed because they compare different things: the rating is the
*typical* IT stock against the *typical* Indian stock (small and mid caps
were racing ahead); the ratio is the *big* IT names against the *big* Nifty
names. The equal-weight view warned first.

### 4.6 How the end usually looks

| Stage | What you see | Where in the app |
|---|---|---|
| Early warning | RS line rolls over; Δ 1M turns negative | Group page RS line; Δ 1M column |
| Rotation | Leading → Weakening | Rotation graph; Post-market rotation changes |
| Leaders fail | Top names break their 50-day lines while the group looks fine | Leaders column; members table |
| Breadth narrows | Fewer members at highs; > 50D falling; cap-weight carrying equal-weight | > 50D, Highs / lows; Returns table |
| Confirmation | Rating below 50; Lagging | RS column |

## 5. How fast leadership changes

Method: from `group_rs_history`, the last stored day of each month, 2013 to
October 2026. For every industry group rated 80+ that day, its rating 1, 3,
6 and 12 months later (only groups rated on both dates; about 4,300 US and
1,800 India group-months).

| Of groups rated 80+ … | still 80+ | still 50+ | fell below 50 |
|---|---|---|---|
| US, 1 month later | 72% | 96% | 4% |
| US, 3 months later | 54% | 84% | 16% |
| US, 6 months later | 41% | 72% | 28% |
| US, 12 months later | 25% | 53% | 47% |
| India, 3 months later | 57% | 89% | 11% |
| India, 6 months later | 40% | 76% | 24% |
| India, 12 months later | 23% | 57% | 43% |

About 20% of groups are rated 80+ at any time and 50% are 50+, so:
**leadership persists for a few months** (after three, over half the top
groups are still on top, 2½ times the base rate), but **after a year it is
mostly gone** (25% against 20%; about as likely bottom half as top half).
**Laggards turn too:** of US groups rated below 20, 22% were 80+ twelve
months later and 38% touched 80+ at some month-end within the year (India
15% and 21%). Sub-industries behaved almost the same (US: 54% still 80+
after 3 months, 24% after 12).

Caveats: the 1-month figure is inflated by construction (the 6–12-month
windows barely move in a month); month-ends overlap, so these are not
independent; small groups are noisier. **For the trader:** reassess groups
every few months; last year's leaders are not this year's by default.

## 6. Rotation: where the money goes next

**Defensives vs cyclicals.** Expecting growth, money favours cyclicals
(discretionary, industrials, materials, banks); fearing a slowdown, it
favours staples, utilities and healthcare. The live read is a ratio of two
sector ETFs — [the business-cycle guide](learn-macro-cycle.md) draws XLY/XLP
and maps who tends to lead in each phase. On the Sectors page at sector
level, Utilities, Staples and Healthcare moving into Leading says the same.

**Rates and commodities move whole groups**
([rates](learn-macro-rates.md), [commodities](learn-macro-commodities.md)),
but not uniformly (§4.2) — confirm with the ratings.

**Late in a run, money moves from leaders to laggards:** the old leaders'
Δ 1M turns negative while low-rated groups post big positive Δ and move into
Improving — the index can rise while your leaders stall. Rotation into
*defensive* laggards is a warning; into *cyclical* ones, often healthy
broadening.

## 7. India specifics

- **Sector indices** (Nifty Bank, IT, Pharma are stored) are cap-weighted
  and dominated by a few names; the Sectors page shows the typical member
  (§4.5).
- **PSUs are their own story.** Government-owned banks, lenders, railway,
  defence and power companies often move together on policy, disinvestment
  and dividend news, which is why the app splits **PSU banks** from
  **private banks** and the **govt. infra & power lenders** from other NBFCs.
  Both bank groups were rated 90+ at the end of 2022; by the end of
  September 2023 PSU banks were **90** and private banks **26**.
- **Policy-driven rotations.** Railway, road and power spending in the Union
  Budget, production-linked incentive (PLI) schemes from 2020, and defence
  procurement from domestic makers have each been behind group runs. The
  thesis tells you where to look; the rating tells you whether the market
  agrees, and when it stops (§4.4).
- **A small universe** (about 60 rateable groups against 130 in the US): one
  or two stocks can swing a small group — check the **Stocks** column. Results
  season and the Budget reshuffle groups quickly
  ([the calendar guide](learn-macro-calendar.md)).

## 8. What the trader does

**The top-down routine.**

1. **Market** — is the index in an uptrend, is breadth healthy?
   ([trend](learn-health-trend.md), [breadth](learn-health-breadth.md)). The
   rating is relative: in a falling market leading groups fall too.
2. **Sector** — Sectors level: the two or three leaders; what is moving into
   Improving.
3. **Group** — Industry groups, sorted by RS: the top 15–20, the biggest
   Δ 1M gains, the Improving quadrant; open large, mixed groups at the
   sub-industry level.
4. **Leaders** — each top group's page: Stage 2 charts near their 52-week
   highs, forming proper bases ([the bases guide](learn-bases.md)); **Add top
   10 to a watchlist…**. The **Strong stocks in leading groups** screen
   (`screens/definitions.py`: tradable, peer group RS **80+**, stock RS rank
   **70+**, above the 50- and 200-day) does steps 3–4 in one pass.
5. **Entry** — only now look for setups in those names.

**Rules of thumb.**

- **A strong stock in a strong group** — RS 70+ in a group rated 80+. It
  need not be the group's #1.
- **Be wary of strong stocks in weak groups.** In the study, US Stage 2
  stocks in weak groups beat the average stock by about 1.4% over six
  months, against about 5.0% for those in strong groups. In India the
  1-month gap was larger (+1.16% a month) but did not hold at six months. A
  lone strong stock in a weak group can be a real special situation
  (takeover, turnaround) — size it smaller and expect less help.
- **Two or three names per group** — five chip stocks are close to one big
  position.
- **When a group is extended, wait** (nearly every member above its 50-day,
  many up 25%+ in a month, headlines everywhere) for the next base, or look
  to an Improving group that has not run.
- **Manage holdings with the group.** If its group slips into Weakening or
  its rating drops 20+ points in a month, tighten the stop; Lagging and
  below 50 means the reason you bought is gone.

## 9. What the evidence says

- **Robust:** stocks in a group move together, and group momentum persists
  for months. Moskowitz and Grinblatt (1999) found that industry momentum
  accounts for much of the stock-momentum effect; this app's persistence
  numbers (§5) agree.
- **Supported here, modestly:** buying in strong groups and avoiding weak
  ones helped in the five-year study — clearly in India (t 2.9),
  suggestively in the US (t 1.5) — and a group filter improved one
  superseded strategy's backtest.
- **Not supported here:** the group's #1 did not beat its other strong
  stocks; sub-industries did not forecast better than industry groups.
- **Folklore:** the neat clockwise rotation and the cycle's sector map are
  tendencies, often broken. How much of a stock's move its group
  "explains" depends on period and method — quote O'Neil's claim as his.
- **Lags and failures:** the rating confirms weeks after the RS line
  (§4.1); leadership mostly fades within a year (§5); strong groups still
  fall in a falling market (§4.3) and policy stories can end abruptly (§4.4).

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

## Further reading

- William O'Neil, *How to Make Money in Stocks* — industry group ranks,
  leaders vs laggards.
- Mark Minervini, *Trade Like a Stock Market Wizard* — leadership and
  relative strength.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — stage
  analysis, the sector before the stock.
- Sam Stovall, *Standard & Poor's Guide to Sector Investing* — sectors
  across the business cycle.
- Julius de Kempenaer — Relative Rotation Graphs (relativerotationgraphs.com).
- Tobias Moskowitz and Mark Grinblatt, "Do Industries Explain Momentum?",
  *Journal of Finance*, 1999.
- This app: [the sector playbook](sector-analysis-playbook.md),
  [the group-strength study](group-strength-study.md),
  [the taxonomy note](sector-taxonomy.md).
