# Sectors → stocks (draft)

Part of [my trading system](system-overview.md). The weekly step between the market and the setups: find the groups
that lead, the ones starting to lead, and the ones breaking, then narrow them to a short, dated list of stocks for each
book. Every rule is *proposed*, with its source and what this repository has measured. The [sector analysis
playbook](sector-analysis-playbook.md) is the full reference behind this page; this page is the decision procedure.

**In short**

- Four kinds of group, each measured on Markets → Sectors: **leading**, **emerging**, **weakening** and **lagging**.
  Longs come from the first two, shorts from the last.
- Group strength is the one part measured here: over five years of month-ends, stocks in strong groups beat stocks in
  weak groups — clearly in India, weakly in the US. "Emerging" is untested.
- A strong stock in a strong group is enough. Being the group's number one added nothing.
- The output is a **dated stock list** in Trade desk → Scans & reports, and one watchlist per group.
- The setup, the entry and the exit are not chosen here; the stocks go to the [Longs](system-swing-longs.md) and
  [Shorts](system-shorts.md) pages.

---

## 1. Where this step sits

| | |
|---|---|
| **Before it** | The [daily market review](system-daily-market-review.md) — the regime row decides whether longs, shorts or neither are hunted at all |
| **Cadence** | Weekly in depth (the weekend); a daily glance at the sector table during the review |
| **Reads** | Markets → Sectors (ranking, RS rating and its change, breadth inside each group, the rotation graph, each group's ranked members); Screens |
| **Writes** | A stock list stored in Trade desk → Scans & reports under its data date; a watchlist per group |
| **After it** | [Longs](system-swing-longs.md), [Shorts](system-shorts.md), and for F&O stocks the [F&O page](system-fno-leverage.md) |

**Which level.** Industry groups, not the 11 broad sectors: one sector holds opposite moves (semiconductors and software are
both "Technology"). Where a large group is split, the stock's **peer group** is its sub-industry — the same rule the screens
use ([sector playbook](sector-analysis-playbook.md) §2.2).

## 2. Four kinds of group

All four are read from the Sectors page's own columns. The thresholds are *proposed*; the source column says where each
comes from.

| Kind | Reading (proposed) | Source | Feeds | Status |
|---|---|---|---|---|
| **Leading** | Group RS rating **80 or more**; in the *Leading* part of the rotation graph; at least half the members above their 50-day; more members at new highs than at new lows | 80 is the "Leaders — in leading groups" screen's group threshold; breadth from the [playbook](sector-analysis-playbook.md) §2.3 | Longs — every book | **Measured** (§3), the RS part only |
| **Emerging** | RS rating up **20 points or more** over a month, and still under 80; moving into *Improving*; members at new highs rising for three weeks | Playbook §2.1 ("groups jumping 20–30 points are coming into favour") and Phase 5 | Longs — swing book first; a watchlist for the position book | **Untested** (§5) |
| **Weakening** | Was leading; RS rating down 20 points or more in a month, or moved into *Weakening*; its leaders closing below the 50-day on volume | Playbook §2.7 | No new longs in it; open longs are flagged for review | **Untested** |
| **Lagging** | RS rating **20 or less**; in *Lagging*; most members below their 200-day | Mirror of leading; [Stage 4 shorts](learn-strat-stage4-shorts.md) | Shorts | **Untested** |

**Why change matters as much as level.** The RS rating ranks a group's past 3 to 12 months. A group that has led for a
year scores 95 while already slowing, and a group just turning up still scores 50. The month's change and the rotation
graph's quadrant are the earlier readings; the rating confirms. "The thesis tells you where to look; relative strength
tells you when" ([playbook](sector-analysis-playbook.md) §1).

**Themes.** A theme (a basket across industries, e.g. defence or power) is read the same way: the Sectors page rates
themes on the industry groups' scale. Its own confirmation rule is RS 70 or more and rising, in *Improving* or *Leading*.

## 3. What has been measured

The [group-strength study](group-strength-study.md) formed sets of stocks at each month-end from late 2021 to late 2026,
point in time, and measured their return over the next months against the average tradable stock.

```chart
title: Six-month excess return by group strength, month-ends 2021–2026
labels: Strong group (RS 80+) | Middling group | Weak group (RS < 50)
series: US | 2.60 | 0.23 | -0.66
series: India | 2.75 | 0.32 | -1.46
unit: % over the average tradable stock, 6 months
caption: Group-strength study, "Every set" tables, tradable stocks. The order holds in both markets; only India's one-month difference (t = 3.0) is clearly more than luck. The US one-month t is 0.9.
```

| Finding | US | India | What it means here |
|---|---|---|---|
| Strong group vs weak group, 1-month difference | +0.43 points, t 0.9 | **+1.39 points, t 3.0** | Group strength is worth checking — more so in India |
| Within Stage 2, requiring a strong group | +0.10, t 0.4 | +0.46, t 1.5 | Small on top of the Trend Template: the group is a tie-breaker, not a gate |
| Within Stage 2, top 3 in the group vs the rest | −0.04, t −0.1 | +0.17, t 0.2 | **No edge in being the group's #1** — a strong stock in a strong group is enough |
| The "Leaders — in leading groups" screen vs Stage 2 | −0.05, t −0.2 | +0.33, t 0.9 | Not better than Stage 2 alone over one month |
| Sub-industry vs industry group as the peer group | +0.18, t 0.5 | +0.43, t 0.8 | Either works; the screens use the sub-industry where a group is split |

**How far to trust it.** About 60 month-ends, one regime, and the window overlaps what is now the verify period
(2022 onward): the study was run before the backtest stages existed, so it reads as *measured*, not *verified*. Today's
industry classification is used for every past date, and delisted stocks are missing — both flatter the results.

## 4. The weekly routine

| # | Step | Where | Output |
|---|---|---|---|
| 1 | **Read the regime.** The daily review's row for the week. In *Broad correction / bear*, longs stay a watchlist; in *Confirmed uptrend*, shorts are not hunted | Today; [daily review](system-daily-market-review.md) §4 | Which sides are open |
| 2 | **Rank the groups.** Industry-group level; list each group that fits a kind in §2. Note the RS change and the quadrant | Markets → Sectors | 3–5 leading, 2–3 emerging, the weakening, the lagging |
| 3 | **Check persistence.** Compare with last week's list. A group leading for 4 weeks or more is a position-book group | Trade desk → Scans & reports (last week's entry) | Each group marked new, held or dropped |
| 4 | **Narrow to stocks — longs.** In leading and emerging groups: the "Leaders — in leading groups" screen (stock RS 70+, peer group RS 80+, above the 50- and 200-day), then the Trend Template. For an emerging group, the strongest members by RS on the group's page | Screens; the group's members on Markets → Sectors | Long candidates per group |
| 5 | **Narrow to stocks — shorts.** In lagging and weakening groups: stocks in Stage 4 (below a falling 150-day), weaker than the index over 3 months, liquid; India — on the F&O list | The group's members; [Shorts](system-shorts.md) §2 | Short candidates per group |
| 6 | **Store the list.** One stock list for the week, dated by its data | Trade desk → Scans & reports; a watchlist per group | The record next week's step 3 reads |
| 7 | **Check open positions.** Is each still in a leading or emerging group? A position whose group turned *weakening* is flagged — what to do with it is a management rule, still TBD | Watchlists | Flags for the Longs / Shorts pages |

The playbook's routine (§2.8) adds a monthly ranking comparison and a quarterly read of the top groups' earnings — those
stay there.

## 5. From the list to each book

| Book | Groups | Stocks | Next |
|---|---|---|---|
| **Position** (months) | Leading for 4+ weeks | Leaders that also pass the Trend Template; quality as a tie-breaker (Screens → Quality companies) | [Longs](system-swing-longs.md) §1 |
| **Swing** (days to weeks) | Leading and emerging | The narrowed list from step 4 | Longs: setups under study |
| **Short-term** (1–5 days) | The week's strongest groups by 1-week and 1-month return | The fastest movers in them | Longs §1 — the short-term book |
| **Shorts** | Lagging and weakening | Step 5 | [Shorts](system-shorts.md) |
| **F&O** | Any of the above | India stocks on the F&O list only | [F&O and leverage](system-fno-leverage.md) |

## 6. What to test

Each study follows the backtest stages: tune on 2013–2021, verify once on 2022 to today, with the pass criteria written
before the run. The point-in-time group RS from the group-strength study can be rebuilt back to 2013 from stored prices.

| Idea | Question | How |
|---|---|---|
| **Emerging groups** | Do members of a group whose RS rose 20+ points in a month from under 80 beat (a) the average stock and (b) members of groups already at 80+, over 1–6 months? | Event study on monthly group RS; optimise stage first |
| Breadth confirmation | Inside leading groups, do groups with half or more members above the 50-day do better than narrow ones? | Split the leading set by breadth |
| Weakening as an exit | After a leading group's RS falls 20 points in a month, do its members lag? | Same data, the opposite event |
| A group gate in a strategy | Do a strategy's trades in groups rated 80+ beat its others? | A research switch on a long strategy (playbook Phase 2), with the stage discipline |
| Weekly sector ranking with slack *(proposed, [Masonson](creator-les-masonson.md) 33:45-35:31)* | Ranked every Friday over 4-12 weeks, does keeping a leader while it stays in the top four (buying the top three), and selling on a close below the 20-day EMA, beat the month-end top three? He has not traded it (35:44) | `sector_rotation` 1.2 switches `--weekly`, `--lookback-weeks`, `--hold-rank`, `--ema-exit`; optimise runs #1498-1513 |
| Six sectors, not eleven *(proposed, Masonson 36:06)* | Does dropping the weakest long-run sectors (utilities, real estate…) help, or only reflect hindsight? | `--six` (US; the six are partly inferred, see the creator note §4.4) |

## 7. Decisions for me to make

1. The thresholds: 80 for leading, +20 a month for emerging, 20 for lagging, 4 weeks for persistence.
2. How many groups to follow at once (the proposal: 3–5 leading, 2–3 emerging).
3. Whether to run the emerging-group study before using that kind for real money.
