# Breadth — how many stocks are taking part

Learning material: what market breadth is and why it measures **risk more
than direction**; the measures this app stores; what divergences, washouts
and breadth thrusts looked like in the stored data, in the US and India; and
how a trader turns it into exposure. Companion to
[the trend guide](learn-health-trend.md) and
[the volatility guide](learn-health-volatility.md).

**Where this shows in the app.** Markets → **Breadth** ("How healthy is the
market — risk, not direction"), built from `breadth_daily`
(`scripts/swing_screener/analytics/breadth.py`, served by `/api/breadth` in
`web/server.py`); every reading is ranked against all trading days since 2015.
Breadth also supplies three of the six **market tone** signals on Markets →
Post-market (`analytics/postmarket.py`): *more stocks rose than fell*, *more
new 52-week highs than lows*, *half or more of stocks above their 50-day
average*.

---

## 1. What breadth is — and what it is not

An index is a weighted average: the S&P 500 gives its biggest companies a
large share of the weight, and the Nifty 50 holds only fifty stocks. An index
can rise while most stocks fall, and a trader who owns ten mid-sized
breakouts does not own the index. **Breadth asks: how many stocks are
actually going up?**

The page's framing is the right one: breadth *"helps judge how risky the
market is, **not** which way it will go."* Weak breadth means fewer stocks
carry the index and breakouts have less company; strong breadth means many
setups work at once. **The index is the weather; breadth is how many of your
trades get wet.**

## 2. How this app builds breadth

Every trading day since **2015**, `analytics/breadth.py` takes the **1,000
most-traded stocks** in each market — ranked by 20-day average turnover, so
the set follows liquidity through time — and counts:

| Field | Definition in the code |
|---|---|
| Rising / falling (`adv`, `dec`) | close above / below the previous close |
| Up / down 4%+ (`up4`, `dn4`) | the day's big movers |
| 52-week highs / lows | today's high (low) is the extreme of the last 252 bars; needs ~200 bars of history |
| Above the 5 / 50 DMA | close above its 5- / 50-day simple average |
| Month ±25% (`up25m`, `dn25m`) | up / down 25%+ over the last 21 bars (±50% is stored too) |

**Only common stocks count.** The US universe file already excludes ETFs (and
closed-end funds flagged by the `classify` job are dropped); India's symbols
are classified as equity or fund and funds are left out. Two consequences:

- **The two "1,000s" differ.** In the US the 1,000 most-traded are mostly
  large and mid caps; in India the same count reaches well into small caps,
  so India's breadth is closer to a small-and-mid-cap gauge (§8).
- **The symbol list is today's** (a frozen ticker file): stocks delisted
  since 2015 are probably missing, so old readings may lean slightly strong.

## 3. The Breadth page, card by card

Each card shows today's value, a gauge ranking it against every day since 2015
("Only N in 100 days since 2015 were…"), and a table against one week, one
month and three months ago — because *"slow changes matter most: markets
rarely turn in a day."*

| Card (its real title) | What it shows | How to read it |
|---|---|---|
| **S&P 500 against its 50 DMA?** (Nifty 50 for India) | The index's % distance from its 50-day | The index's own short-term trend — the context |
| **Stocks at a 52w high or low?** | New highs and lows, and the typical day over two weeks | Leadership against damage; ranked on the 10-day average of highs − lows |
| **Stocks above their 5 & 50 DMA?** | % above the 5- and 50-day averages | 50-day: the average stock's trend; 5-day: short-term stretch |
| **Stocks rising or falling?** | Advancers and decliners, and the two-week typical day | Participation; ranked on the 10-day average of rising − falling |
| **Leading sectors, last 3 months?** | Best and worst sector against the average stock; sectors with most stocks above the 50-day | Where the strength is, and how widely shared |
| **Options: expected vs actual?** | VIX / India VIX against the index's realised volatility | See [the volatility guide](learn-health-volatility.md) |

Below them: **What changed in the last 5 sessions** (30% / 70% crossings,
90-day extremes, the index crossing its 50-day), four **Charts** (the 50-day
one with lines at **30% washout, 70% strong**), **Sectors: where the strength
is?** and **The last 30 days**, shaded for each reading's strongest / weakest
fifth since 2015.

## 4. The measures

### 4.1 % above the 50-day — and the 5-day

The most useful single number: *for how many stocks is the trend up?*

| Since 2015 | US | India |
|---|---|---|
| Median % above 50-day | 59% | 56% |
| 10th–90th percentile | 29–77% | 21–82% |
| Days below 30% (the page's "washout") | 11% | 19% |
| Days below 15% | 3.5% | 4.8% |
| Days above 70% (the page's "strong") | 23% | 27% |

```series
title: US stocks above their 50-day average, and the S&P 500, since 2015
from: 2015-01-01
to: 2026-10-13
line: us:SPX | S&P 500 | log
line: us:breadth.pct50 | % of the 1,000 most-traded above their 50-day | pane2
mark: 2018-12-24 | 2% above
mark: 2020-03-12 | 2% above
mark: 2022-06-17 | 4.5% above
mark: 2025-04-08 | 4.9% above
caption: The lower pane swings from near 0% to over 90%. The deepest readings (2% in Dec 2018 and Mar 2020, under 5% in June and Sept 2022 and Apr 2025) came at or near the index's lows, not its highs.
```

The **5-day** version is a short-term overbought / oversold gauge (US median
54%; under 20% on about 8% of days, over 80% on about 10%). Under 20% in an
uptrend is a stretched pullback; over 80% is a poor moment to chase.

### 4.2 New 52-week highs and lows

Highs are **leadership** — stocks with no overhead supply, where breakout and
trend strategies find candidates. Lows are **damage**. A typical US day since
2015 had about **46 highs and 7 lows** among the 1,000; India about **31 and
5**. A panic looks like **660** US lows on 12 March 2020 and **692** in India
the next day. Read the **net** and its 10-day average, as the page does.

### 4.3 Advancers, decliners and the A/D line

Rising minus falling, summed day after day, is the **advance-decline line**.
Its level means nothing; its direction against the index is the point. An
index high the A/D line does not confirm means fewer stocks joined the last
leg. Unlike the all-issues NYSE line, the app's has no thin micro caps or
bond funds in it.

### 4.4 Big movers: ±4% days and ±25% months

A median US day has **24** stocks up 4%+ and **23** down; the record is
**944** down on 12 March 2020. India is lopsided — **62** up, **24** down on a
median day — until a panic (**943** down on 23 March 2020). Many stocks up 25%
in a month is a hot tape; many down 25% is forced selling.

## 5. Divergences — the index at a high, fewer stocks with it

A **divergence**: the index makes a higher high, breadth a lower one.

### 5.1 The US, 2021

```series
title: The S&P 500 rose through 2021 while its new-high count faded
from: 2020-11-01
to: 2022-03-31
line: us:SPX | S&P 500
line: us:breadth.adline | A/D line, 1,000 most-traded | right
line: us:breadth.hl@sma10 | highs − lows, 10-day average | pane2 zero
mark: 2021-05-10 | breadth peak
mark: 2022-01-03 | index peak
caption: Highs − lows (10-day average) peaked at 164 on 10 May 2021 and was 53 when the S&P 500 made its high on 3 Jan 2022. The A/D line topped on 16 Nov 2021. By late January 2022 the net was negative.
```

The S&P 500 gained about **30%** from the start of 2021 to its high on **3
January 2022**, while breadth weakened for months: net highs (10-day) peaked
at **164** in May and was **53** on the final high, with only **33** stocks at
new highs that day. The 10-day share above the 50-day fell in steps — about
**83%** in early January 2021, **73%** at the end of April, **61%** at the end
of October, **47%** at the end of December — and on **10 December 2021** the
index closed at a record with net highs *negative* (about −10). The Russell
2000 had peaked on **8 November 2021**. The divergence did not time the top
(it ran for half a year); it said risk was rising.

### 5.2 2024–2026: narrow highs come and go

Mega-cap leadership shows in the data in bursts. At the **June 2024** highs
only about **48%** of stocks were above their 50-day and net highs averaged
**28**, against **104** at the March 2024 highs. The **19 February 2025** high
had **57%** and a net of **37**; the index then fell **19%** to 8 April. Late
2024 was broad again (median **69%** above the 50-day on record days).

```series
title: S&P 500 records with fewer stocks above their 50-day, 2023–2026
from: 2023-10-01
to: 2026-10-13
line: us:SPX | S&P 500 | log
line: us:breadth.pct50@sma10 | % above 50-day, 10-day average | pane2
mark: 2024-06-18 | 48% above
mark: 2025-02-19 | 57% above
mark: 2026-10-06 | 34% above
caption: Broad records (early and late 2024) were followed by more records; narrow ones (June 2024, Feb 2025) by a stall or a fall. The record of 6 Oct 2026 came with 34% above the 50-day.
```

At the time of writing, the **6 October 2026** record had net highs (10-day)
near **−24** — the lowest participation on any S&P 500 record day since 2015.
What follows is unknown; it is the situation in which breadth says *size
down*, not *sell everything*.

## 6. Washouts — when almost nothing is above its 50-day

The page calls **below 30%** a washout. The deep version — **below 10–15%**,
under 5% of days in either market — has tended to come near important lows. Below: the first close
under 15% after a recovery above 40%, and the S&P 500 21, 42 and 63 sessions
later.

| US — first day < 15% | Low (date) | +1m | +2m | +3m |
|---|---|---|---|---|
| 24 Aug 2015 | 4.7% (25 Aug) | +2.4% | +8.4% | +10.4% |
| 7 Jan 2016 | 6.9% (20 Jan) | −4.6% | +2.4% | +5.4% |
| 11 Oct 2018 | 8.8% (26 Oct) | +1.9% | −2.8% | −5.3% |
| 17 Dec 2018 | 2.0% (24 Dec) | +3.5% | +9.2% | +10.9% |
| 27 Feb 2020 | 2.2% (12 Mar) | −14.7% | −3.9% | +1.7% |
| 9 May 2022 | 11.1% (11 May) | +3.1% | −3.4% | +3.3% |
| 13 Jun 2022 | 4.5% (17 Jun) | +1.1% | +14.1% | +4.9% |
| 22 Sep 2022 | 4.5% (26 Sep) | −0.1% | +5.1% | +3.2% |
| 3 Oct 2023 | 12.7% (27 Oct) | +0.2% | +8.6% | +11.2% |
| 4 Apr 2025 | 4.9% (8 Apr) | +10.5% | +17.1% | +22.7% |

Three months on, the S&P 500 was higher after **9 of 10** (median **+5%**),
against **75%** of all days since 2015. One month on, only 7 of 10 — and the
first washout day of February 2020 was followed by a further **15%** fall.
**A washout says the selling is mature, not that it is over.**

**India** had **13** such episodes; the Nifty 50 was higher three months later
after **11** (median **+6.4%**). The exceptions were the small-cap bear market
of 2018 (first day 28 September, low **3.9%** on 8 October, Nifty **−2.4%**
three months on) and March 2020 (low **0.6%** on 23 March; **−6.1%** from the
first day, 9 March). Two US washouts had **no Indian twin**: India's lowest
reading was **43%** in September 2022 and **32%** in October 2023.

**Small sample:** ten US and thirteen Indian episodes; no threshold here is
a buy signal.

## 7. Breadth thrusts — the other end of a washout

A **breadth thrust** goes from deeply oversold to broadly bought in days.
Martin Zweig's version: the 10-day average of advancers ÷ (advancers +
decliners) rising from below **0.40** to above **0.615** within 10 sessions.

The app does not compute one; a simple version from the stored `adv` and
`dec` (10-day exponential average) fired **11** times in the US since 2015.
The S&P 500 was higher a year later after 9 of the 10 with a full year behind them, but
three months later after only **7 of 11** — two fired inside the 2022 bear
market (March and September), with the index **18%** and **4%** lower three
months on. In India it fired 7 times: higher three months later all 7 times,
a year later only 4 of 6. **Read a thrust as "the washout is probably over",
not "the bear market is over"** — let the index's trend
([trend guide](learn-health-trend.md)) confirm it.

## 8. India against the US

India's breadth runs **broader in rallies and deeper in sell-offs**. On Nifty
50 record days in 2023 the median share above the 50-day was **80–85%**; on
S&P 500 record days in 2024–25 mostly **50–70%**. The 2023–24 rally was a mid-
and small-cap boom: from the March 2023 low to late September 2024 the Nifty
Midcap 50 rose about **106%** and the Nifty 50 about **54%**.

```series
title: India's breadth faded before the Nifty peaked, then washed out, 2024–2025
from: 2024-01-01
to: 2025-06-30
line: india:NIFTY50 | Nifty 50
line: india:breadth.pct50@sma10 | % above 50-day, 10-day average | pane2
mark: 2024-09-26 | Nifty peak, 64% above
mark: 2025-03-03 | 9% above
band: 2025-01-27 2025-03-21 | below 15%, until back above 40%
caption: About 82% of Indian stocks were above their 50-day in early July 2024 and 64% at the Nifty's high on 26 Sept. On 3 March 2025 under 7% were (the 10-day average shown here: 9%).
```

The 2024 top was a divergence of its own: net highs (10-day) peaked near
**153** in February 2024 and was about **72** at the Nifty 50's record on **26
September 2024**. The washout that followed was India's deepest since 2020 —
**6.6%** above the 50-day on 3 March 2025 — while the Nifty 50 was down only
about **16%** from its peak. Small- and mid-cap holders felt far worse than
the index said — the reason to watch India's breadth, not just the Nifty.

## 9. How a trader uses breadth

Breadth does not pick stocks; it **sets how much risk to take**.

| Breadth state | Usually means | Exposure |
|---|---|---|
| > 70% above the 50-day, highs ≫ lows | Broad uptrend, setups working | Full size and position count; buy breakouts |
| 50–70%, net highs positive | Normal | Normal size; favour the leading sectors |
| Index at highs, % above 50-day and net highs falling | Narrowing | Fewer new positions; tighten stops on laggards; strongest groups only |
| < 30% (washout) | Correction | Few or no new longs; protect open profits |
| < 15%, then a fast recovery or thrust | Selling exhausted | Start small with the first leaders to make new highs; add as the index trend repairs |

**Which signals to trust:** most — the % above the 50-day at its extremes,
and new lows expanding (damage is hard to fake); noisy — daily advancers and
decliners (use the 10-day average); least, alone — divergences as *timing*
tools (2021's ran six months) and thrusts inside a bear market (2022).
**Combine** breadth with the index trend, credit and volatility
([liquidity and credit](learn-macro-liquidity-credit.md),
[volatility](learn-health-volatility.md)): two warnings together matter far
more than one.

**What the app's strategies do with breadth.** The screener's regime
(`core/regime.py`) computes the share of its universe above the 20- and 50-day,
but **no decision uses it**: the downgrade looks only at whether the first two
broad indices (SPY and QQQ; Nifty 50 and Nifty 500) are below their 50-day,
and risk is halved only on the volatility index. Breadth is **your** filter.

## 10. What the evidence says

- **Robust:** deep washouts cluster near major lows, with better than average
  returns after — in this data and in long NYSE studies (Zweig; Desmond on
  90% down days).
- **Mostly true:** narrowing breadth precedes many tops (2021 US, 2024 India),
  but the lead runs from weeks to many months, and narrow markets can keep
  rising (mega-cap stretches of 2023–24).
- **Folklore:** that one divergence or one thrust times the market.
- **Measurement matters:** other universes give other dates and levels;
  compare a reading with its own history, as the page's ranks do.
- **Sample:** 2015 onwards holds about ten real washouts per market — §6–7
  describe what happened, not probabilities.

## 11. Checklist

- [ ] % above the 50-day: rising or falling over a month? Above 70%, below 30%?
- [ ] Net new highs (10-day): positive and expanding, or shrinking?
- [ ] New lows expanding while the index holds up?
- [ ] Index at a high with fewer stocks above the 50-day than at the last high?
- [ ] After a washout: a fast recovery or thrust, and the index back over its 50-day?
- [ ] India: is the Nifty hiding a weaker small- and mid-cap tape?
- [ ] "What changed in the last 5 sessions": any 30% / 70% crossing?
- [ ] Set this week's position count and size from the table in §9

## Further reading

- Martin Zweig, *Winning on Wall Street* — the breadth thrust.
- Gregory L. Morris, *The Complete Guide to Market Breadth Indicators*.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — breadth and stages.
- Paul Desmond, "Identifying Bear Market Bottoms and New Bull Markets" (2002) — 90% days.
- William J. O'Neil, *How to Make Money in Stocks* — leadership and the general market.
