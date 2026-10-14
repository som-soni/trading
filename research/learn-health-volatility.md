# Volatility and sentiment — what fear costs, and when it matters

Learning material: what the VIX and India VIX measure and the move they
imply, their ranges, why volatility clusters and fades, why spikes tend to
mark panic lows while calm is not a sell signal, implied against realised
volatility, other sentiment gauges, and exactly how this app sizes positions
off volatility. Companion to
[the breadth guide](learn-health-breadth.md); the long VIX history chart is in
[the liquidity and credit guide](learn-macro-liquidity-credit.md), and
event-day volatility in [the calendar guide](learn-macro-calendar.md).

**Where this shows in the app.** Markets → Breadth: the **"Options: expected
vs actual?"** card and the *Expected / Actual / Exp ÷ act* columns of **The
last 30 days** (`/api/breadth`, `web/server.py`). Markets → Post-market: the
tone signal *"Volatility index fell (fear easing)"* (`analytics/postmarket.py`). The screener's regime (`core/regime.py`) flags
**high volatility** when the VIX closes above **25** (India VIX above **20**),
and live sizing then halves the risk per trade from **1%** to **0.5%**
(`core/sizing.py`, `config/us.py`, `config/india.py`).

---

## 1. What the VIX and India VIX measure

The **VIX** is the market's price of 30-day volatility on the S&P 500,
worked out from S&P 500 option prices; **India VIX** does the same from Nifty
50 options on the NSE. Both are quoted as an **annualised standard deviation
in percent**: a VIX of 20 prices a move of about 20% a year, one standard
deviation either way. It is not a forecast of direction; it is what insurance
costs — and insurance gets dear when everyone wants it at once, usually after
prices have already fallen.

**The rule of thumb.** A year has twelve months and about 252 sessions, so
the expected **one-month** move ≈ VIX ÷ √12 ≈ VIX ÷ 3.5, and the expected
**one-day** move ≈ VIX ÷ √252 ≈ VIX ÷ 16.

| VIX | One month, ±1 s.d. | One day, ±1 s.d. | Feels like |
|---|---|---|---|
| 12 | ±3.5% | ±0.75% | Calm; breakouts drift |
| 20 | ±5.8% | ±1.25% | Normal-to-nervous |
| 30 | ±8.7% | ±1.9% | Stress; gaps through stops |
| 40 | ±11.5% | ±2.5% | Panic |

With bell-shaped returns about two months in three would stay inside the
band. Real returns are not bell-shaped: most months are quieter than priced,
a few far wilder (next section).

## 2. The Breadth page's options card

**"Options: expected vs actual?"** sets **Expected** — the latest VIX (India
VIX for India) — against **Actual**, the index's **realised** volatility: the
standard deviation of the S&P 500's (Nifty 50's) daily log returns over the
last **20 sessions**, annualised with √252.

Its text turns both into a monthly move with the rule above — *"Options price
about ±X% over a month; the index has been moving about ±Y%"* — and the gauge
ranks the **ratio** expected ÷ actual against every day since 2015 ("dearer"
or "cheaper" options). The page's own note: *a ratio well above 1 means
options are dear.*

| Since 2015 | US | India |
|---|---|---|
| Median expected (VIX) | 16.6 | 15.3 |
| Median actual (20-day realised) | 12.3 | 12.3 |
| Median ratio | 1.32 | 1.25 |
| Days with ratio below 1 | 15% | 17.5% |

**Options are usually dear.** Since 2010 the VIX was above the S&P 500's
volatility over the *following* month on **84%** of days (median gap 4.5
points); India VIX on **81%** (3.4 points). That gap is the **volatility risk
premium** — what option sellers are paid to carry crash risk. It is also why
the ±1 s.d. band is breached less than a bell curve says: the S&P 500's
one-month move went beyond ±VIX/√12 on only **16%** of days, the Nifty 50's
on **26%** (more often upward, 16% against 10%).

**Reading the ratio:**

- **Well above 1** (options dear, index quiet): fear building ahead of an
  event, or a market that has calmed after a shock before options caught up.
- **Near or below 1** (the index moving more than options price): a live
  sell-off or violent rally — where stops get gapped. In the US it happened
  most in 2022 and 2018.

## 3. Ranges and regimes

From daily closes since 2010:

| | VIX | India VIX |
|---|---|---|
| Median | 16.7 | 16.4 |
| 10th–90th percentile | 12.3–26.7 | 12.0–24.5 |
| Days above 20 | 29% | 26% |
| Days above 25 | 13% | 9% |
| Days above 30 | 6% | 3% |
| Days above 40 | 1.3% | 0.7% |
| Lowest close | 9.1 (Nov 2017) | 9.2 (Dec 2025) |
| Highest close | 82.7 (16 Mar 2020) | 83.6 (24 Mar 2020) |

Regimes last years — the VIX's yearly median was **10.9** in 2017 and **25.5**
in 2022; India VIX's **23.2** in 2011 and about **12–13** in 2023 and 2025 —
so read a level against its own recent past.

## 4. Volatility clusters, then fades

Big days come in bunches. Since 2010, **5.7%** of S&P 500 sessions moved more
than 2%; after a 2% day in the previous ten sessions the chance rose to
**13.8%**, and with none it was **2.3%**. India: 5.0%, 10.4% and 2.7%. Robert
Engle's ARCH models describe exactly this clustering.

But volatility also **mean-reverts**: panics exhaust sellers, and option
prices fall as soon as the feared move fails to come.

In 2020 both indices peaked within days (VIX **82.7**, India VIX **83.6**);
the VIX did not close below 20 again until 12 February 2021, India VIX not
below 18 until 28 May 2021. From the first close above 35 back to below 20 took **7 sessions** in
February 2018 and **6** in August 2024 (positioning shocks), about **five
weeks** in 2025 and almost **a year** from February 2020 (an economic one).

## 5. Spikes mark panic lows more often than tops

Each of these spikes came *after* the index had already fallen about 8–20%. The
first close above 35 (counted again only after the VIX had been back
under 20), and the S&P 500 1 and 3 months (21, 63 sessions) later:

| First VIX close > 35 | VIX | S&P 500 off 52-week high | +1m | +3m |
|---|---|---|---|---|
| 7 May 2010 | 41.0 | −8.7% | −4.4% | +1.0% |
| 8 Aug 2011 | 48.0 | −17.9% | +7.1% | +11.9% |
| 24 Aug 2015 | 40.7 | −11.2% | +2.4% | +10.4% |
| 5 Feb 2018 | 37.3 | −7.8% | +2.9% | +0.9% |
| 24 Dec 2018 | 36.1 | −19.8% | +13.3% | +19.3% |
| 27 Feb 2020 | 39.2 | −12.0% | −14.7% | +1.7% |
| 7 Mar 2022 | 36.5 | −12.4% | +7.7% | −1.9% |
| 5 Aug 2024 | 38.6 | −8.5% | +6.4% | +10.5% |
| 4 Apr 2025 | 45.3 | −17.4% | +10.5% | +22.7% |

Three months later the index was higher after **8 of 9** (median **+10%**,
against +3.9% for any 63-session window since 2010). But the first spike of
2020 was followed by another **15%** fall, and March 2022 came mid-bear-market.
India VIX's first closes above 30 (seven episodes since 2010) were followed by
a higher Nifty 50 three months later five times (median **+9%**); the
exceptions were August 2011 and March 2020.

```series
title: April 2025 — the VIX peaked on the S&P 500's closing low
from: 2025-01-15
to: 2025-07-31
line: us:SPX | S&P 500
line: us:VIX | VIX | right
mark: 2025-04-08 | VIX 52.3, index low
caption: The S&P 500 fell 19% from 19 Feb to 8 April 2025, the day the VIX closed at 52.3. The VIX was back under 20 by 12 May, and the index made a new closing high on 27 June.
```

**Small sample:** nine US spikes and seven Indian ones. The lesson is not
"buy VIX 40" but that **a spike is late information**: selling into it is
usually selling low, and good entries come as the VIX *falls back*.

## 6. Low volatility is not a sell signal

On the 311 days since 2010 with the VIX under 12, the S&P 500 was higher
63 sessions later **80%** of the time, against **75%** for all days; the median
gain was a little lower (+3.3% against +3.9%) and the spread of outcomes much
narrower. India VIX under 12: higher three months later **77%** of the time,
against **66%**.

```series
title: Calm can last — 2017, then the February 2018 spike
from: 2016-11-01
to: 2018-04-30
line: us:SPX | S&P 500
line: us:VIX | VIX | right
mark: 2018-02-05 | VIX 37.3
caption: The VIX's median in 2017 was 10.9 and its highest close 16.0; the S&P 500 rose about 19% with no pullback over 3%. From the 26 Jan 2018 high (VIX 11.1) the index fell 10% in nine sessions.
```

What low volatility *does* mean: smooth trends, and a calm that ends fast —
**11.1** to **37.3** in six sessions in 2018. The worst outcomes were real
(−17.5% three months after 21 September 2018; India −34% after 2 January
2020). Low volatility is a reason to **keep stops honest**, not to sell.

## 7. A VIX that stays high is a bear market

The other regime is a VIX that never quite spikes but never relaxes:

```series
title: 2022 — no panic spike, but a VIX that would not settle
from: 2021-11-01
to: 2023-03-31
line: us:SPX | S&P 500
line: us:VIX | VIX | right
band: 2022-01-03 2022-10-12 | S&P 500 peak to closing low
caption: The VIX's highest close in 2022 was only 36.5, yet it closed above 20 on 91% of the year's sessions while the S&P 500 fell 25% to 12 October.
```

A VIX that holds **20–35 for months** is a grinding bear market, and the
"buy the spike" lesson does not apply: in 2022 every pop above 30 (January,
February, April, June, September) was followed by a lower index low, until
October. With a weak index trend
([trend guide](learn-health-trend.md)) and weak breadth, a high VIX is a
regime, not an opportunity.

## 8. India VIX — events, and what it does not see

India VIX rises **before** scheduled uncertainty and collapses after it. Ahead
of the 2014 general-election result it closed at **37.7** on 9 May 2014 —
with the Nifty 50 at a record close, not falling — and was **16.3** by 30 May. The
2024 election and Budget days are worked through in
[the calendar guide](learn-macro-calendar.md).

It also measures only the **Nifty 50**. India's breadth washout of early 2025
was its deepest since 2020, yet India VIX stayed in the teens:

```series
title: India's 2025 small- and mid-cap washout, with India VIX in the teens
from: 2024-07-01
to: 2025-06-30
line: india:NIFTY50 | Nifty 50
line: india:INDIAVIX | India VIX | right
line: india:breadth.pct50 | % of stocks above 50-day | pane2
mark: 2025-03-03 | 6.6% above 50-day
caption: Between Oct 2024 and March 2025 India VIX peaked at 18.6 (29 Jan) and was 13.8 on 3 March, when only 6.6% of the 1,000 most-traded stocks were above their 50-day.
```

The app's high-volatility switch (India VIX above 20) would **not have
fired** at any point in it; small- and mid-cap traders needed
[breadth](learn-health-breadth.md) to see it.

## 9. Other sentiment gauges (not stored in the app)

Widely followed, none in the database — check them at source.

| Gauge | What it is | How it is read |
|---|---|---|
| **VIX term structure** | VIX against longer-dated volatility (e.g. Cboe's 3-month VIX) or VIX futures | Normally upward sloping. Short-term above long-term (inversion) means acute fear — usually near a short-term low |
| **Put/call ratio** | Puts traded ÷ calls traded (Cboe in the US; NSE's Nifty options PCR in India) | Extremes are contrarian: very high = fear, very low = complacency. Noisy day to day; use an average |
| **AAII Sentiment Survey** | Weekly poll of US individual investors: bullish / neutral / bearish | Contrarian at extremes (bears far above bulls near lows); useless in the middle |
| **Fear & Greed Index** (CNN) | A composite of several of the above plus momentum and breadth | A convenient summary; read extremes only |

One rule covers all of them: **sentiment is contrarian only at extremes, and
only as a condition, not a trigger** — the trend decides when fear has passed.

## 10. How the app uses volatility — exactly as coded

| Setting | US | India |
|---|---|---|
| Volatility index (`vol_index_symbol`) | `^VIX` | `^INDIAVIX` |
| Threshold (`vol_threshold`) | 25 | 20 |
| Risk per trade (`risk_pct`) | 1% | 1% |
| Risk per trade, high volatility (`risk_pct_high_vol`) | 0.5% | 0.5% |
| Max position (`max_position_pct`) | 25% of the account | 25% |
| Days above the threshold since 2010 | 13% | 26% |

The mechanics:

1. The daily screener (`screening/pipeline.py`) reads the **last close** of the
   volatility index and `compute_market_regime` sets `high_vol` when it is
   **strictly above** the threshold.
2. `size_position` (`core/sizing.py`) then uses `risk_pct_high_vol`:
   risk amount = account × 0.5% instead of 1%; shares =
   floor(risk ÷ (entry − stop)), capped by the max-position notional.
3. That is all it changes. **`high_vol` does not change any decision tier**
   (the regime *downgrade* depends only on the broad indices being below their
   50-day), and **backtests always size at the normal risk** — the backtester
   calls `size_position` with `vix_above_threshold=False`.

India's threshold has been exceeded on twice the share of days, so India
sizing halves more often. The `trend_pullback` parameter table on the
Strategies page shows the setting as *"Risk per trade, high volatility"*.

## 11. Volatility and your position size

The app's sizing is already **volatility-aware per stock**: the stop sits
under a structural level, so a volatile stock with a wide stop gets fewer
shares for the same 1% risk. The screener also requires ATR(14) above **1.5%**
of price (both markets). On top of that:

- **Market volatility scales everything.** At VIX 30 an index day is about
  ±1.9%; a stock three times as volatile moves 5–6% on an ordinary day, so a
  5% stop is one day away. Use a wider structural stop with fewer shares, or
  skip the trade — never keep the size and tighten the stop.
- **Halve risk and position count.** Correlations rise in high volatility.
- **Gaps ignore stops.** Size for the gap, not the stop.

ATR-based stops, portfolio heat and risk of ruin belong to a separate guide on
risk management.

## 12. What a trader does

| Volatility state | What to do |
|---|---|
| VIX under ~15, rising trend, good breadth | Normal size; trends are smooth; keep stops honest |
| 15–25, normal | Normal; watch the options card for a ratio below 1 |
| Sudden spike from calm | Stop new buying for a few days; it is late news; see if it was positioning |
| Above the threshold (25 US, 20 India) | Risk per trade halves in the app; also cut position count |
| Spike peaking and falling back, breadth washed out | Prepare the watchlist; first entries small, as the VIX falls and leaders reclaim highs |
| VIX holding 20–35 for weeks, index below its 200-day | Bear-market regime: little or no new long risk |

## 13. What the evidence says

- **Robust:** volatility clusters (Engle's ARCH work) and mean-reverts;
  implied volatility is usually above what follows (the volatility risk
  premium; Carr and Wu among many). Both hold in this data.
- **Mostly true:** extreme VIX readings come near lows rather than tops, and
  three-month returns after them have been above average — with 2020 and 2022
  as the warnings that a spike can come early in a decline.
- **Folklore:** that a low VIX predicts a crash ("complacency"); in this data
  low-VIX days were followed by *more* frequent gains, if smaller ones. And
  that India VIX tracks the whole Indian market — it prices the Nifty 50 only.
- **Lags:** the VIX moves with the market, not ahead of it — a gauge of
  current risk for sizing, not a timing signal.

## 14. Checklist

- [ ] VIX / India VIX: level, and above or below the app's threshold (25 / 20)?
- [ ] Rising from calm (a shock) or holding high for weeks (a regime)?
- [ ] Options card: expected ÷ actual above 1 (dear) or below 1 (moves outrunning options)?
- [ ] One-month expected move (VIX ÷ 3.5) against your stop distances
- [ ] India: India VIX calm but breadth falling? Trust breadth for small caps
- [ ] Scheduled events this week (see [the calendar guide](learn-macro-calendar.md))?
- [ ] Sentiment extremes (put/call, AAII, term structure inversion) — a condition, not a trigger
- [ ] Set risk per trade and position count for the week

## Further reading

- **Cboe** — the VIX methodology white paper; **NSE** — India VIX methodology and data.
- Robert E. Whaley, "The Investor Fear Gauge", *Journal of Portfolio Management* (2000).
- Robert F. Engle, "Autoregressive Conditional Heteroscedasticity…", *Econometrica* (1982).
- Peter Carr and Liuren Wu, "Variance Risk Premiums", *Review of Financial Studies* (2009).
- Sheldon Natenberg, *Option Volatility and Pricing*.
- **AAII** — the weekly Sentiment Survey and its history (aaii.com).
