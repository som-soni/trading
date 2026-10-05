# Index Investing Research Log

What has been tested about *when* to put money into an index — as opposed to
[`momentum-trend-research.md`](momentum-trend-research.md), which is about
*which stocks* to own. Append to the ledger as new strategies are tried; the
methodology and bias sections apply to everything in it.

**Last updated:** 2026-10-04
**Windows:** US total return 1980-01-02 → 2026-10-02 (46.7y), US price index
1927-12-30 → 2026-10-02 (98.8y), India total return 2009-01-02 → 2026-10-02
(17.7y), India price index 1997-07-01 → 2026-10-01 (29.3y).

---

## 1. Where things stand

1. **The day you contribute does not matter.** Across 30 contribution days
   the best-to-worst gap is 0.87% of terminal wealth in the US over 46.7
   years and 1.04% in India over 17.7 — but in annualised terms that is
   **0.007pp** (US) and **0.048pp** (India). The best day by terminal wealth
   is not even the best day by return.
2. **Where an ordering exists at all, it is time in the market, not a
   calendar effect.** Contributing on the 1st rather than the 28th invests
   each instalment ~27 days earlier. That mechanism alone explains **94% of
   the variation across days in the US (r = 0.970)** and **79% in India's
   clean window (r = 0.888)**, and in both cases what remains sits inside the
   randomised-day null. On India's 29-year Sensex window the ordering runs
   *against* the mechanism (r = −0.537): the noise there is several times the
   mechanical effect, so that ranking measures neither. Day-of-week shows the
   same gradient by terminal wealth — Monday best, Friday worst,
   monotonically, in *both* markets — which is what four extra days of
   exposure looks like, not a weekday anomaly.
3. **Perfect foreknowledge is worth almost nothing.** Buying every month's
   lowest close — impossible — adds **+0.085pp** of XIRR in the US and
   **+0.32pp** in India. That is the ceiling on all monthly timing. No
   implementable rule can beat it, and every rule tested lands below it.
4. **Waiting for a dip loses, and the loss grows with patience.** US: holding
   contributions for a 20% drawdown returned 10.999% against 11.211% for
   investing immediately. India is the same ordering at the 5% and 10%
   thresholds. The lump-sum version appeared to *win* on windows that open
   just before a crash — and is refuted on the 98.8-year US window, where all
   three thresholds underperform buy-and-hold and get monotonically worse the
   longer they wait (§3.5).
5. **Saving more dominates every timing decision by three orders of
   magnitude.** A 10%/yr contribution step-up turned $16.2M into **$64.5M**
   on the same 46.7-year path. The best timing rule in the whole family added
   $20k. Perfect foreknowledge added $472k.
6. **Trend overlays are insurance: they cost return and buy drawdown.** US
   over 98.8 years the 10-month rule returned 8.98% against buy-and-hold's
   8.37% with max drawdown cut from −85.5% to −51.1%. Over 1980-2026 it
   *lost* 0.62pp. In India it is far worse — 5.82% against 12.68% on the
   clean window — confirming and extending §6 of the momentum log.
7. **Tax changes the ranking, it does not merely scale it.** A buy-and-hold
   book gives up 0.4–0.7pp a year; a monthly-rebalanced or rotating book
   gives up 1.3–3.0pp. In the US, momentum rotation beats buy-and-hold on
   drawdown and *loses* by 2pp a year after tax.
8. **Adding gold to an equity index improved every risk measure in both
   markets** — but on a window (2004/2009 onward) that contains gold's best
   run in modern history. Flagged as regime-dependent, not adopted.

The practical consequence: for an accumulator, the entire Family A decision
space is worth under 0.05pp a year. The decisions that matter are how much is
contributed, whether it stays contributed through a −55% drawdown, and what
is paid in tax and fees.

---

## 2. Results ledger

### US — accumulation (SP500_TR 1980-2026, 46.7y, 2bps, monthly SIP)

Scored on XIRR, because CAGR on a contributed book is meaningless.

| rule | XIRR | after-tax XIRR | terminal | contributed |
|---|---|---|---|---|
| PERFECT hindsight monthly low *(lookahead)* | **11.296** | 10.833 | 16,659,677 | 562,000 |
| dip: deploy at −5% from peak | 11.215 | 10.752 | 16,207,251 | 562,000 |
| **immediate (baseline)** | **11.211** | **10.749** | 16,187,136 | 562,000 |
| invest only above 200DMA | 11.162 | 10.700 | 15,919,036 | 562,000 |
| dip: deploy at −15% | 11.152 | 10.691 | 15,866,024 | 562,000 |
| dip: deploy at −10% | 11.087 | 10.626 | 15,522,077 | 562,000 |
| dip: deploy at −20% | 10.999 | 10.540 | 15,063,663 | 562,000 |
| 0.5× above / 2× below 200DMA | 10.870 | 10.412 | 14,424,315 | 562,000 |
| value averaging (10% path) | 10.798 | 10.055 | 14,076,677 | 562,000 |
| *control:* +5%/yr step-up | 11.242 | 10.733 | **27,675,877** | 2,118,565 |
| *control:* +10%/yr step-up | 11.488 | 10.896 | **64,523,496** | 10,303,339 |

### India — accumulation (NIFTY50_TR 2009-2026, 17.7y, 10bps, monthly SIP)

| rule | XIRR | after-tax XIRR | terminal |
|---|---|---|---|
| PERFECT hindsight monthly low *(lookahead)* | **11.108** | 10.279 | 31,440,057 |
| dip: deploy at −20% | 10.817 | 10.037 | 30,507,225 |
| dip: deploy at −15% | 10.809 | 10.011 | 30,482,170 |
| **immediate (baseline)** | **10.793** | **9.976** | 30,431,844 |
| dip: deploy at −5% | 10.705 | 9.894 | 30,157,360 |
| dip: deploy at −10% | 10.680 | 9.877 | 30,078,048 |
| value averaging (10% path) | 10.566 | 9.749 | 29,727,396 |
| invest only above 200DMA | 10.475 | 9.672 | 29,449,747 |
| 0.5× above / 2× below 200DMA | 10.361 | 9.587 | 29,104,834 |

### Contribution frequency — same annual amount

| frequency | US XIRR | India XIRR |
|---|---|---|
| daily | 11.210 | 10.781 |
| weekly | 11.208 | 10.789 |
| fortnightly | 11.210 | 10.786 |
| monthly | 11.210 | 10.771 |
| quarterly | **11.224** | 10.726 |
| annual | 11.216 | 10.490 |

Spread: 0.016pp (US), 0.30pp (India). Quarterly topping the US table is noise,
not a finding — it is inside the day-of-month null band.

### Lump sum vs DCA — 10-year holds, every quarter-start

| DCA months | US win rate | US median adv. | India (TR) win | India (29y) win |
|---|---|---|---|---|
| 3 | 63.3% | +1.07% | 48.4% | 44.9% |
| 6 | 68.0% | +2.22% | 54.8% | 52.6% |
| 12 | 74.1% | +4.89% | 71.0% | 59.0% |
| 24 | 78.2% | +8.69% | 77.4% | 70.5% |
| *starts* | 147 | | 31 | 78 |

Lump sum wins more often the longer the alternative spreads, in both markets.
Its worst case is also worse (−25% vs DCA at 12 months in the US), which is
the actual trade: higher median, fatter left tail.

### US — lump-sum overlays (SP500_TR 1980-2026, 46.7y)

| strategy | CAGR | after-tax | maxDD | Sharpe | Calmar | exposure |
|---|---|---|---|---|---|---|
| wait for −20% then buy *(start-date artefact, §3.5)* | 11.92 | 11.53 | −55.3 | 0.73 | 0.22 | 95% |
| **buy & hold** | **11.50** | **11.11** | **−55.3** | 0.70 | 0.21 | 100% |
| 8-month SMA → cash | 10.94 | 9.20 | −33.8 | 0.82 | 0.32 | 75% |
| 10-month SMA → cash | 10.88 | 9.25 | −33.8 | **0.82** | 0.32 | 75% |
| 12-month absolute momentum | 10.57 | 9.22 | −33.1 | 0.82 | 0.32 | 79% |
| 50/200 golden cross | 10.39 | 9.09 | −33.8 | 0.79 | 0.31 | 76% |
| vol target 15% | 10.17 | 8.74 | −40.2 | 0.77 | 0.25 | 89% |
| 200-DMA daily → cash | 9.63 | 8.03 | −33.1 | 0.81 | 0.29 | 76% |
| Nov–Apr only (sell in May) | 9.07 | 7.22 | −33.8 | 0.75 | 0.27 | 49% |
| vol target 10% | 8.78 | 7.14 | **−27.2** | **0.86** | 0.32 | 72% |

### US — the 98-year window (^GSPC 1927-2026, price + 1.89%/yr dividend)

| strategy | CAGR | after-tax | maxDD | Sharpe | exposure |
|---|---|---|---|---|---|
| 200-DMA daily → cash | **9.65** | 8.11 | −46.2 | **0.80** | 70% |
| 10-month SMA → cash | 8.98 | 7.70 | −51.1 | 0.69 | 70% |
| **buy & hold** | 8.37 | **8.19** | −85.5 | 0.52 | 100% |
| wait for −10% then buy | 8.31 | 8.13 | −85.5 | 0.52 | 99% |
| wait for −20% then buy | 8.27 | 8.09 | −82.3 | 0.52 | 98% |
| wait for −30% then buy | 8.14 | 7.96 | −82.3 | 0.51 | 98% |
| Nov–Apr only | 7.71 | 5.87 | −61.6 | 0.65 | 49% |

The 1980-2026 and 1927-2026 windows **disagree on the sign** of the trend
overlay. That disagreement is the finding; see §3.3.

### India — lump-sum overlays

| strategy | window | CAGR | after-tax | maxDD | Sharpe |
|---|---|---|---|---|---|
| **buy & hold** | 2009-26 | **12.68** | **11.95** | −36.3 | 0.77 |
| vol target 15% | 2009-26 | 10.14 | 8.90 | −28.7 | 0.75 |
| vol target 10% | 2009-26 | 8.19 | 6.91 | **−22.0** | **0.79** |
| 200-DMA daily → cash | 2009-26 | 5.85 | 4.97 | −23.6 | 0.52 |
| 10-month SMA → cash | 2009-26 | 5.82 | 5.14 | −38.8 | 0.48 |
| Nov–Apr only | 2009-26 | 4.61 | 3.45 | −36.3 | 0.43 |
| **buy & hold** | 1997-26 | **11.00** | **10.53** | −60.5 | 0.59 |
| 10-month SMA → cash | 1997-26 | 10.11 | 9.02 | −41.1 | 0.66 |
| 200-DMA daily → cash | 1997-26 | 9.60 | 8.14 | −47.0 | 0.68 |

### Static allocation

| mix (annual rebalance) | US CAGR | US maxDD | US Sharpe | India CAGR | India maxDD | India Sharpe |
|---|---|---|---|---|---|---|
| 100% equity | 10.90 | −55.3 | 0.64 | 12.68 | −36.3 | 0.77 |
| 70/30 equity/gold | **11.14** | −37.9 | 0.81 | 13.32 | −25.6 | 1.03 |
| 60/40 equity/gold | 11.12 | −34.8 | 0.84 | **13.40** | −23.0 | **1.10** |
| 80/20 equity/bond | 9.61 | −43.3 | 0.71 | 10.99 | −29.1 | 0.81 |
| 60/40 equity/bond | 8.14 | −29.9 | 0.81 | 9.19 | −21.8 | 0.88 |
| 50/30/20 eq/bond/gold | 8.89 | **−24.4** | **0.93** | 10.40 | **−18.2** | 1.11 |

US window 2004-11 onward, India 2009-01 onward (both set by the gold series).

### Rebalancing cadence (60/20/20 equity/bond/gold)

| cadence | US pre-tax | US after-tax | India pre-tax | India after-tax | US trades |
|---|---|---|---|---|---|
| never (drift) | **9.78** | **9.08** | **11.57** | 10.87 | 3 |
| monthly, 5% band | 9.77 | 8.93 | 11.38 | **10.73** | 29 |
| annual | 9.68 | 8.80 | 11.36 | 10.67 | 72 |
| annual, 5% band | 9.66 | 8.85 | 11.26 | 10.56 | 18 |
| quarterly | 9.63 | 8.64 | 11.33 | 10.64 | 270 |
| monthly | 9.57 | 8.47 | 11.29 | 10.52 | 795 |

### Rotation

| strategy | window | pre-tax | after-tax | maxDD | Sharpe |
|---|---|---|---|---|---|
| US buy & hold | 2004-26 | **10.90** | **10.17** | −55.3 | 0.64 |
| US top 1 of 5, 12mo | 2004-26 | 10.68 | 8.21 | −32.0 | 0.64 |
| US top 3 of 5, 12mo | 2004-26 | 10.44 | 8.71 | −25.2 | **0.80** |
| US GEM (SPY/EFA/IEF) | 2002-26 | 8.56 | 7.06 | −26.7 | 0.67 |
| India buy & hold | 2009-26 | 12.68 | **11.95** | −36.3 | 0.77 |
| India top 1 of 5, 12mo | 2009-26 | 13.92 | 11.69 | −33.6 | 0.82 |
| India top 1 of 5, 6mo | 2009-26 | **17.19** | 14.21 | −33.6 | **0.97** |

India's 6-month rotation is the one result in the whole suite that beats its
benchmark after tax by a wide margin. It is also the most-fitted: five
sleeves, two lookbacks, one 17.7-year window. Treat as a hypothesis.

---

## 3. What each experiment established

### 3.1 The day-of-month question, answered

The spread across 30 contribution days is 0.87% of terminal wealth in the US
and 1.04% in India. Three separate checks say it is not exploitable:

* **The randomised-day null.** Contributing on a random day each month, 200
  times, produces a distribution of outcomes. India's clean window: observed
  best-to-worst spread 0.029 against a null 95th percentile of 0.033 —
  *inside* the null, so the test returns NOISE outright. The US window and
  India's long window do exceed their nulls, with a "best" day 3.0 and 2.4 sd
  above the random-day mean — but that is the maximum of 30 draws, a ~2 sd
  event under the null by construction, and in the US case the excess is
  fully accounted for by §3.2.
* **The two windows disagree.** India's best day is the 6th on the clean TR
  window and the 23rd on the 29-year Sensex window. An effect that does not
  survive a change of window is not an effect.
* **The ordering is mechanical.** See §3.2.

Decisive version: measured as a *return* rather than terminal wealth, the
spread is **0.007pp** (US) and **0.048pp** (India). The best day by terminal
wealth (US day 1) is not the best day by return (US day 19).

### 3.2 The apparent effect is time in the market

Contributing on the 1st rather than the 28th puts each instalment to work
about 27 days earlier. At each market's own drift that is worth roughly 0.8%
per instalment — the same order as the entire observed spread. Regressing
each day's observed gain on the gain predicted by extra days invested alone:

| window | r | r² | spread before | after | null 95th pct |
|---|---|---|---|---|---|
| US SP500_TR 1980-2026 | **0.970** | 0.94 | 0.2298 | 0.0917 | 0.2485 |
| India NIFTY50_TR 2009-2026 | **0.888** | 0.79 | 0.0214 | 0.0151 | 0.0330 |
| India SENSEX 1997-2026 | **−0.537** | — | 0.1056 | 0.1490 | 0.0987 |

On both total-return windows the mechanism explains most of the ordering and
the residual falls inside the null. **The Sensex window contradicts it**: a
negative correlation means the observed ordering runs *against* the only
mechanism known to produce one, so there the noise (0.1056) simply swamps the
mechanical effect and the ranking measures neither. That is why the Sensex
"best day" (the 23rd) sits at the opposite end of the month from the other
two windows' winners.

Either way the conclusion for an investor is the same, and the disagreement
strengthens rather than weakens it: the ordering is a head start where it is
anything at all, and noise where it is not.

The day-of-week table is the same story in a second place: by terminal wealth,
Monday best and Friday worst, **monotonically, in both markets**. That is not
a weekday anomaly; it is four extra days of exposure.

It also explains why XIRR shows almost no spread while terminal wealth does.
XIRR discounts by actual flow dates, so it already nets out the head start —
which is precisely why the annualised spread (0.007pp US, 0.048pp India) is
the honest number and the terminal-wealth spread is not.

### 3.3 Trend overlays: the sign depends on the window

| period | buy & hold | 10-month rule | difference |
|---|---|---|---|
| 1930s | −3.38% (DD −82.3%) | **+4.66%** (DD −34.8%) | **+8.03** |
| 1940s | 4.84% | 7.32% | +2.48 |
| 1950s | **15.82%** | 13.00% | −2.82 |
| 1960s | **6.36%** | 4.83% | −1.53 |
| 1970s | 3.44% | **8.04%** | +4.60 |
| 1980s | **15.00%** | 13.48% | −1.52 |
| 1990s | **17.33%** | 15.53% | −1.80 |
| 2000s | −0.77% (DD −55.6%) | **+6.95%** (DD −15.8%) | **+7.73** |
| 2010s | **13.18%** | 8.93% | −4.25 |
| 2020-26 | **15.80%** | 13.87% | −1.94 |

The rule pays in exactly three decades — the 1930s, 1970s and 2000s — and
costs in the other seven. It wins over 98.8 years because those three decades
are where the −85% drawdown lives. The 1980-2026 window contains only one of
them (the 2000s, worth +7.73pp there) against four losing decades, which is
why the same rule loses 0.62pp over that window and wins 0.61pp over the
century. **It is insurance: a premium paid in most
decades for a payout in a few.** Judging it on average CAGR over a window
that excludes a crash is judging insurance by whether the house burned down.

India's version is far more hostile: −6.86pp on the clean window and −0.89pp
over 29 years, with drawdown relief of only 19pp. The Indian market mean-
reverts faster than the rule can re-enter.

### 3.4 Tax reorders the table

Per-year cost of tax, by how much the strategy trades:

| behaviour | US drag | India drag |
|---|---|---|
| buy & hold | 0.39pp | 0.73pp |
| annual rebalance | 0.88pp | 0.69pp |
| monthly rebalance | 1.10pp | 0.77pp |
| trend overlay (10-month) | 1.64pp | 0.68pp |
| 200-DMA daily | 1.60pp | 0.88pp |
| momentum rotation | 2.47pp | 2.23pp |

Two consequences that a pre-tax table hides entirely: in the US, momentum
rotation goes from roughly matching buy-and-hold (10.68 vs 10.90) to losing
by 2pp (8.21 vs 10.17); and **never rebalancing wins the cadence table in
both markets after tax**, because it realises nothing.

### 3.5 "Wait for the crash" is a start-date artefact

US 1980-2026: waiting for a −20% drawdown returned 11.92% against
buy-and-hold's 11.50%. India 1997-2026: −30% returned 12.39% against 11.00%,
and the deeper the threshold the better it looks — monotonically, which is
itself the warning sign.

Both are start-date accidents, and the 98.8-year window settles it:

| strategy | 1980-2026 | 1927-2026 |
|---|---|---|
| buy & hold | 11.50 | **8.37** |
| wait for −10% | 11.54 | 8.31 |
| wait for −20% | **11.92** | 8.27 |
| wait for −30% | 11.22 | 8.14 |

The ordering **inverts**. Over a century every threshold loses, and loses
monotonically more the longer it waits — which is what a rule that spends
time out of a rising market should do. The 1980-2026 result comes from the
window opening in January 1980, so the strategy sat in T-bills yielding
14–16% through the 1980-82 bear and bought near the bottom; India's 1997
window opens immediately before the Asian crisis and shows the same flattery
(−30% "returns" 12.39 against 11.00). Exposure for all of these is 95–99%:
they are buy-and-hold with one lucky entry, not a repeatable rule.

Two independent confirmations that this is the right reading: the
accumulation version (§2, Family A), which must make the decision 562 times
rather than once, **loses at every threshold in the US**; and the monotonic
improvement with depth on the short windows is itself the signature of a
single lucky entry rather than an edge.

### 3.6 Gold flattered both markets, on a window that would

70/30 equity/gold beat 100% equity on return *and* drawdown *and* Sharpe in
both markets. The US window starts 2004-11 and India's 2009-01, both set by
when a gold series exists. Gold returned roughly 9%/yr over that span against
a long-run real return near zero. This is a window artefact until it is
tested on a window that includes 1980-2000, when gold lost two-thirds of its
value — and no such series is available here.

### 3.7 Contribution frequency barely registers

0.016pp of XIRR across daily/weekly/monthly/quarterly/annual in the US,
0.30pp in India where the annual case is genuinely worse (10.49 vs 10.78) —
large enough to say *don't contribute annually in India*, and nothing more.

---

## 4. Methodology

- **Total returns throughout.** Series are fetched with `auto_adjust=True`
  into a separate `index_series` table. The screener's `prices` table stays
  unadjusted because stops and pivots need real traded levels; dividends
  (1.89%/yr US, 0.83%/yr India, both measured) would otherwise swamp every
  effect tested here, *and would do so asymmetrically* — a strategy sitting in
  cash forgoes less dividend income than buy-and-hold, so dropping dividends
  silently flatters every timing rule.
- **Dividend yields are calibrated, not assumed.** Implied yield = TR CAGR −
  price CAGR over the overlap: 1.89%/yr from ^GSPC vs VFINX (1980-2026),
  0.83%/yr from ^NSEI vs NIFTYBEES (2009-2026).
- **Cash earns a real rate, on calendar days.** 13-week T-bill (^IRX, 1960
  onward) for the US; realised LIQUIDBEES yield for India, with a flat 6.5%
  before 2009 where no series exists. Accrual is per calendar day — accruing
  per *trading* bar pays only ~69% of real interest and penalises exactly the
  waiting strategies under test.
- **Tax is simulated separately from the pre-tax run.** A taxed run pays its
  bill out of the book as it goes, so that run's CAGR *is* the after-tax
  number and cannot double as the pre-tax one. Every strategy runs twice.
  Terminal unrealised gains are settled at the end, or a 46-year holder would
  be compared against a rebalancer while never paying any tax at all.
- **FIFO lots**, because whether a sale is taxed at 20% or 12.5% depends on
  how long *that* lot was held.
- **Signals are lagged.** A signal on date *t* uses only prices to *t−1*;
  monthly rules are shifted on the monthly series, not the daily one.
  `tests/test_index_investing.py` asserts that moving any bar's price does not
  change the signal on that bar.
- **Costs:** 2bps/side US, 10bps/side India, on top of each series' own
  expense ratio charged daily. These are ETF/index-fund costs, not the
  25bps/side the stock strategies pay.
- **Calendars are intersected, not unioned.** Union-plus-ffill would invent
  prices on days a market was shut and let a strategy trade on them.

### Vendor data repair

Yahoo applies some NSE splits to only part of a series. NIFTYBEES printed
−89.9% on 2019-12-19 and +896.9% on 2019-12-23 (a 1:10 split); GOLDBEES −99%
then +9900%; MON100 −90% then +892%; Nifty Midcap 50 has a +179.6% second
bar. **Unrepaired, India buy-and-hold showed a −89.9% max drawdown on a
market that fell 38%** — every India number in this document would have been
wrong.

`index_data.repair` handles three artefact shapes (spike-reversal, persistent
unapplied split, opening artefact), logs every repair, and is tested against a
fabricated −20.5% crash to confirm it leaves real history alone.
`--validate` now reports the worst day per series: ^GSPC −20.5% (1987-10-19)
and +16.6% (1933-03-15), which are the correct records.

---

## 5. Known biases — read before trusting any number

1. **Survivorship bias does not apply here**, unlike the stock-level
   backtests. An index series has no selection step. Index *reconstitution* is
   inside the index's own return, which is a real (small) upward bias in any
   index, not an artefact of this code.
2. **One path.** 46.7 years is a single realisation, and 17.7 years is barely
   one regime. Sub-period and second-window tables exist throughout because a
   ranking that only holds on the full window is a fit to it — and twice here
   the second window overturned the first (§3.2, §3.5), which is the whole
   argument for keeping them.
3. **Data-snooping.** The thresholds (−5/−10/−15/−20%), lookbacks (6/8/10/12
   months) and sleeve sets were chosen by convention, but the *reporting* of
   the best of each family is still a selected maximum. The placebo band
   exists for exactly this reason in Family A; Families B–D have no equivalent
   and their winners should be read as hypotheses.
4. **Tax rates are a stated assumption**, not a fact about any investor: US
   24%/15% in a taxable account (0 inside a 401k/IRA, where most US index
   money actually sits), India 20%/12.5% with the ₹1.25L LTCG exemption. Loss
   carry-forward is not modelled, which *overstates* tax for strategies that
   book losses and gains in different years.
5. **India's dividend accrual is a lower bound.** 0.83%/yr is measured against
   NIFTYBEES, whose own expense ratio and tracking error sit inside the
   difference; NSE's published Nifty yield has run 1.1–1.4%. India's absolute
   CAGRs are therefore ~0.3–0.5pp conservative. Relative comparisons, where
   both arms carry the same accrual, are unaffected.
6. **Applying a 1980-2026 dividend yield back to 1927** understates the
   1930s–70s, when the yield ran 3–5%. The 98.8-year total returns are
   conservative, and conservative *against buy-and-hold specifically*.
7. **Gold and bond windows are short** (2004/2009 onward), set by when the
   ETFs listed. Family C conclusions inherit that limit.
8. **`max_dd_pct` on an accumulation run is drawdown of the portfolio value,
   contributions included**, so an incoming SIP mechanically softens it. It is
   not comparable to the lump-sum drawdowns in Family B.
9. **India's inverse-vol rotation result (4.46%) is an artefact**, not a
   finding: the sleeve set includes a liquid fund whose volatility is near
   zero, so inverse-vol weighting puts nearly everything in cash. Excluded
   from the conclusions.

---

## 6. Open questions / experiment queue

| # | experiment | needs | why |
|---|---|---|---|
| 1 | India 6-month rotation, out of sample | a pre-2009 India sleeve set | The only after-tax winner in the suite, and the most fitted (§2) |
| 2 | Gold on a window containing 1980-2000 | a long gold series (not on yfinance) | Family C's best result rests on gold's best 20 years (§3.6) |
| 3 | Valuation timing (CAPE / Nifty P/E) | point-in-time P/E series from NSE | The one major "main" index strategy not tested; same data blocker as the fundamentals work in the momentum log |
| 4 | Trend overlay with a re-entry buffer | small change to `index_signals` | India's overlay loses to whipsaw; a band might separate "costs less" from "works" |
| 5 | Contribution timing against a *salary* constraint | nothing new | Every Family A variant assumes money can wait. Real cash arrives on payday and often cannot |
| 6 | US results inside a tax-deferred account | run with `--no-tax` | Most US index money sits in 401k/IRA, where §3.4's reordering does not apply |
| 7 | Why the Sensex window's day ordering runs against time-in-market | sub-window decomposition on 1997-2011 vs 2011-26 | r = −0.537 is either noise or a pre-2009 microstructure effect; the suite cannot currently tell which (§3.2) |

---

## 7. Reproducing anything here

```bash
cd scripts

# once: fetch the total-return series, then check them
PYTHONPATH=. python3 -m swing_screener.marketdata.index_data --refresh
PYTHONPATH=. python3 -m swing_screener.marketdata.index_data --validate
PYTHONPATH=. python3 -m swing_screener.marketdata.index_data --calibrate-dividends

# everything in this document
PYTHONPATH=. python3 -m swing_screener.backtesting.index_investing --market us
PYTHONPATH=. python3 -m swing_screener.backtesting.index_investing --market india

# one family, pre-tax only
PYTHONPATH=. python3 -m swing_screener.backtesting.index_investing \
    --market india --family A --no-tax

# the checks, including lookahead safety (no database needed)
PYTHONPATH=. python3 -m tests.test_index_investing
```

Reports land in `reports/<market>/index_investing/<run>/` — `report.md`, one
CSV per table, `equity_family_*.csv`, and `figures/`.

---

## 8. Changelog

| date | change |
|---|---|
| 2026-10-04 | Suite built; Families A–D run on both markets with pre- and after-tax columns |
| 2026-10-04 | Day-of-month answered: 0.007pp (US) / 0.048pp (India) of annualised return, ~79% of it explained by time in the market |
| 2026-10-04 | Found and repaired yfinance split artefacts that produced a fake −89.9% India drawdown |
| 2026-10-04 | Fixed cash accrual to calendar days — it had been paying ~69% of real interest |
| 2026-10-04 | Trend overlay's sign shown to depend on the window: +0.61pp over 98.8y, −0.62pp over 46.7y, −6.86pp in India |
| 2026-10-04 | "Wait for a −X% dip" refuted out of sample: wins on 1980-2026 and 1997-2026, loses at every threshold over 98.8 years (§3.5) |
| 2026-10-04 | Corrected: the time-in-market explanation holds on both total-return windows (r = 0.970 US, 0.888 India) but is contradicted on the 29-year Sensex window (r = −0.537), where noise dominates both (§3.2) |
