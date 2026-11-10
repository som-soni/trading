# F&O and leverage (draft)

Part of [my trading system](system-overview.md). When a trade the system has already chosen is better expressed with
futures or options, which ones, and how they are sized. Every rule is *proposed*. **Nothing on this page has been
tested here** — see §6 for what that would take. The mechanics are in the Learn guides, starting with [Futures &
options — the map](learn-fno-overview.md); this page holds only the decisions.

**In short**

- F&O **expresses** a decision the playbook already made — the market row, the group, the stock, the setup. It is never
  the reason for a trade.
- Four uses are in scope, all in **India (NSE)**: a stock future for a long, a stock future for an overnight short,
  a bought option or debit spread where gap risk is too large for a future, and an index hedge on the long book.
- **Out of scope:** naked option selling, straddles and strangles, expiry-day and same-day trades, and US options
  (their history is paid). In the US a short is a borrowed share or an inverse ETF ([Shorts](system-shorts.md) §0.1).
- **Size by the maximum loss, never by the margin.** A future's risk is its stop plus a gap through it; an option's is
  the premium; a spread's is its net cost.
- The leverage limits — notional, margin in use, open F&O risk — are on [risk and exposure](system-risk-exposure.md) §6.

---

## 1. The four uses

| # | Use | Instrument | When it is the right tool | Most I can lose | Status |
|---|---|---|---|---|---|
| F1 | **Leveraged long** | Long stock future | A long from the [Longs](system-swing-longs.md) page in an F&O stock, when capital, not risk, is what limits size | Not fixed: the stop, plus any gap through it | Untested |
| F2 | **Overnight short (India)** | Short stock future | Any [short](system-shorts.md) held past the close — a cash short in India must close the same day | Not fixed: no ceiling on a rising price | Untested |
| F3 | **Defined-risk directional** | Bought call or put; a debit spread to cut the cost | A long or short whose holding period crosses results or a scheduled event, or a probe-size trade on a doubtful day | The premium (or the spread's net cost) | Untested |
| F4 | **Index hedge** | Bought Nifty puts; or a short Nifty future | The daily review drops a rung while I still hold longs I don't want to sell | Puts: the premium. Short future: not fixed | Untested |

**Not in the system, and why**

| Excluded | Why |
|---|---|
| Naked option selling, short straddles and strangles | A loss with no fixed ceiling, taken in exchange for frequent small gains; one bad day can undo a year ([the map](learn-fno-overview.md) §5; [income strategies](learn-fno-income.md)). It cannot be tested here until an options simulator exists |
| Selling an option spread for a credit | Defined risk, so a candidate for later — after the simulator (§6) |
| Expiry-day and same-day option trades | Same-day trading is out of the system ([overview](system-overview.md) §1), and the prices that drive them are not stored |
| US options | No history is stored (it is paid), so no rule could ever be tested |

**The base rate.** SEBI's study of the three financial years to March 2024 found about 93% of individual F&O traders lost
money, about ₹1.8 lakh crore in all ([the map](learn-fno-overview.md) §5). The four uses above are chosen to keep F&O a tool
of a tested equity decision, not a separate game.

## 2. When — by the daily review's row

| Daily-review row | F1 long future | F2 short future | F3 bought option | F4 index hedge |
|---|---|---|---|---|
| Confirmed uptrend, broad | Best setups | — | Event crossings | — |
| Uptrend, narrowing | — | — | Best setups | Consider, if the long book is large |
| Correction in one area | — | Probe size, breaking group | Puts at probe size | — |
| Broad correction / bear | — | Normal size | Puts | On any longs still held |
| Bottoming | — | — | Calls at probe size | Lift |
| Recovery confirmed | Step up with the rungs | — | — | — |

*Proposed, untested.* The logic: leverage (F1) only when the market is paying; defined risk (F3) where the tape or an event
is doubtful, because a bought option cannot lose more than its premium, which suits a probe.

## 3. Choosing the instrument

Take the first row that applies.

| Situation | Instrument |
|---|---|
| The stock has no F&O contracts | Cash only. In India no overnight short |
| The stock is in the F&O **ban period** | No new position |
| Results or a scheduled event fall before the planned exit | F3, or skip — not a future |
| One lot risks more than one R at the planned stop | F3, a smaller expression, or skip — never round up |
| The planned hold runs past the current month's expiry | Plan the roll; or choose the next month's contract from the start |
| Otherwise, long | Cash, or F1 if capital limits size |
| Otherwise, short (India) | F2 |

**Stock F&O settles by delivery.** An open stock future or in-the-money option at expiry becomes a real purchase or sale
of shares ([India rules](learn-fno-india-rules.md)). Close or roll before expiry week.

## 4. Sizing

The rule is the same as for shares — risk per trade is one R, from [risk and exposure](system-risk-exposure.md) §1 — and
only the worst case changes ([sizing in F&O](learn-fno-risk-sizing.md) §2):

| Instrument | Loss per lot if wrong | Lots |
|---|---|---|
| Future (F1, F2) | (entry − stop) × lot size + costs, **then a gap scenario** | Round down. If a 10% gap through the stop would cost more than **to decide** R, fewer lots |
| Bought option (F3) | The premium × lot size | Round down; if one lot is more than one R, a debit spread or no trade |
| Debit spread (F3) | The net premium × lot size | Round down |
| Index put (F4) | The premium — paid as a hedge budget, not a trade's R | From the hedge budget (§5) |

**Why a gap scenario.** Among today's F&O stocks, since 2015, an open more than 10% away from the previous close came about
once in eight years per stock, and about 4 in 10 of them had at least one such gap down ([sizing in F&O](learn-fno-risk-sizing.md)
§3). A stop is not the price a future gets.

**Then the totals** (risk page §6): the worst-case loss of all open F&O positions together, the notional against equity, and
the margin in use against the account. Margin is checked last: it limits how much I *can* hold, never how much I *should*.

## 5. Hedging the long book (F4)

| Part | Rule (proposed) | Source |
|---|---|---|
| Trigger | The daily review drops to *Uptrend, narrowing* or below while the long book is above **to decide** % of equity | Daily review §4 |
| Size | Notional of the puts (or short future) ≈ the long book's value × its beta to the Nifty | [Hedging](learn-fno-hedging.md) §1 |
| Budget | Puts cost at most **to decide** % of equity a year | Hedging §3 |
| Lift | The review steps back up a rung, or the long book is cut instead | — |

The alternative is always on the table: **selling longs is a hedge too**, and cheaper. A hedge earns its place when the longs
are leaders I want to keep through a correction in the index, not in the stock.

## 6. What it would take to test

| Step | What | Status |
|---|---|---|
| Data | NSE's daily derivatives prices: index futures and options are stored from January 2012 (settle prices, open interest); stock futures and options are not ingested yet | Built 15 Oct 2026 ([F&O scope](fno-scope.md)) |
| 2 | A continuous futures series, so the existing long strategies can be run with leverage | Not built |
| 3 | An options simulator: legs, expiry, assignment, margin | Not built |
| 4 | Strategies: long calls as a leveraged form of a tested signal; covered calls; hedges | Not built |

F1 and F2 can be tested once step 2 exists, with stock futures added to the ingest; F3 and F4 need step 3.

## 7. Decisions for me to make

1. The notional and margin caps, and the share of total risk allowed in F&O (risk page §6).
2. The gap allowance for a future: how many R a 10% gap through the stop may cost.
3. The hedge trigger and the yearly hedge budget.
4. Whether to ask for step 2 (stock futures in the ingest, and a continuous series) next.
