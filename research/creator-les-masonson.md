# Les Masonson — research notes

*Raw material, synthesized: what Les Masonson said in the Tradeline podcast interview "The TQQQ Trading Strategy
of a 47+ Years Trader" (host Richard), organized by the creator template ([Martin Luk](creator-martin-luk.md) §0),
with timestamps from a local speech-to-text transcript. Everything below is **his** view and **his** numbers
unless marked otherwise. My inferences are marked **[inferred]**, audio the transcript does not settle
**[unclear]**. The speech-to-text garbles some words ("Cloid" for Claude, "slug" for slack, "$7,000" for a
setting of 7); those are read for sense and marked where it matters.*

*What went where: strategies — `masonson_tqqq` 1.0 (his TQQQ timing rule set, each part a switch) and
`sector_rotation` 1.2 (his relative-strength rules as switches); trading system — two **proposed** rows in
[sector selection](system-sector-selection.md) and one in [F&O and leverage](system-fno-leverage.md). His numbers
are not quoted in any Learn guide.*

**In short**

- A day trader of Nasdaq futures and TQQQ for 15 years, flat by the close; his edge is **one instrument** and a
  **weight-of-the-evidence** screen: act only when three or four indicators line up at an extreme.
- **Leveraged ETFs decay in flat and falling markets**; held through 2000-2009 a 3x Nasdaq fund would have been
  wiped out. So: **no longs below the 200-day**, cash (T-bills) in a bear market, and step up the leverage only
  after a rule has worked unleveraged.
- **Relative strength over weeks, not one week**: rank sectors every Friday over 4-12 weeks, keep a leader while it
  stays near the top (with slack), and sell it on a rank drop or a close below a short EMA.
- He has **never traded the sector rule** and is still building the TQQQ swing strategy; he warns against
  overfitting and says a backtest with no drawdowns is the sign of a mistake.
- Measured here (in-sample, 2013-2021): no TQQQ timing version beats QQQ with a drawdown no deeper than QQQ's, and his
  sector switches all made the existing rotation worse (§9).

---

## 1. Style at a glance

| Dimension | What he does | Evidence |
|---|---|---|
| Instrument | Nasdaq 100 only: E-mini Nasdaq futures, earlier TQQQ; "I'm a specialist" | 4:09, 15:52 |
| Horizon | Day trades on 1- and 5-minute charts, flat by the close; three to ten round trips a day | 10:12, 12:46 |
| Decision rule | Several indicators at an extreme, then a reversal; "never use one single indicator" | 12:08, 14:07 |
| Outside information | None: no news, no opinions, no pre-market work | 12:58, 16:19 |
| Stops | None while watching the screen; below the 8 EMA (others use 10) when he leaves it | 15:05 |
| Teaching | Market-timing books; a monthly ETF column; an upcoming workshop on leveraged ETFs | 7:17, 70:20 |

## 2. How he reads the market

- **Timing beats buy-and-hold for people who cannot sit through 20-50% declines**, and he disputes the "time in the
  market" consensus (8:44-9:27). The aim is a rule that "gets you out before the bear market begins" (9:20).
- **The bull market since 2009 has flattered young traders**; 2000-2009 and 1973-74 were different (17:48-18:21,
  39:44-39:58). A serious bear market is coming, timing unknown (39:51).
- **Daily and weekly as context**: above the key averages on both gives him more confidence; below the 200-day,
  no longs — "it can keep going down, down, down, like in 2022" (68:15-69:09). You will not catch the bottom; the
  middle of the run is enough (69:31).

## 3. What he trades

- Nasdaq futures for the tax treatment (US section 1256: 60% long-term, no wash-sale rule) (6:23-6:47).
- TQQQ (3x) and QLD (2x) as the ETF versions; SOXL (3x semis) noted as stronger still. SQQQ (inverse) is hard: it
  decays in a bull market and its windows are short (56:12, 59:14).
- Start unleveraged (QQQ), then QLD, then TQQQ only if the rules worked (57:16-57:39).

## 4. Setups

### 4.1 His intraday screen (10:28-15:30)

| Component | Setting he gives | Note |
|---|---|---|
| RSI | 7 ("to make it work faster") | 10:55 |
| MACD | 6, 13, 5 | 11:04 |
| CCI | not given | 11:04 |
| Keltner channels | 2 and 3 "standard deviation" bands | 11:15; Keltner bands are ATR multiples **[inferred]** |
| VWAP, 200-period average | — | 11:21 |
| Candles | Heikin-Ashi | 13:26 |

Buy: price below the 3-band, then RSI, MACD and CCI cross up; three or four of them crossing at the bottom of the
channel. Sell: the mirror — crosses down, from a high point through the 2- or 3-band (11:28-12:20, 14:47-15:05).

### 4.2 The workshop's swing rule for TQQQ (60:27, 70:20-74:40)

He lists the components and not the settings:

1. A moving average as "a line in the sand" — below it, no position.
2. The MACD **histogram**: above zero or not.
3. RSI at extreme readings.
4. Keltner channels.
5. The **% of Nasdaq stocks above their 50-day** at an extreme low — a time to watch for a buy (and the reverse).
6. The **bullish percent index** (point-and-figure buy signals), very low or very high.

His slide example: indicators drop to extremes, reverse up, "you get back in" — April 2025 (60:46-60:57). Exit: a
close below the 8, 10 or 20 EMA, whichever you are comfortable with (61:26).

His backtest claims (73:00-73:15): one version had a 45% drawdown at a 29% CAGR, against TQQQ's own 81% drawdown;
he is still working on a lower drawdown. These are **his** AI-assisted backtests, not checked here.

### 4.3 The long-term rule (55:02-55:32)

Put a small amount (he says $1,000 of a few thousand) into TQQQ **only after it has fallen 25% or more**, and hold
it for at least 20 years. Otherwise you will sell it in the intermediate term and probably lose it.

### 4.4 Sector relative strength (25:00-36:55)

- Rank by trailing return in a **weekly table**, reviewed **every Friday** (33:45).
- **One week is useless** — it changes colour all the time; use at least four weeks, better eight or 12 (35:05).
  He also mentions 16 and 19 weeks and 52 weeks for individual stocks (28:21, 33:09).
- **Keep a leader while it stays near the top**: if energy is in the top three of 11, "I'm not going to touch it"
  (34:23). Two sell criteria: a drop in rank below about three or four — with slack, because no leader is top every
  week — or a cut below a moving average (8, 10, 12 or 20 EMA on the ETF's chart) (34:26, 35:14-35:31).
- **Six sectors, not 11**: the ones that have done best over time — he reads out the consumer, XLY, XLE, XLC, XLK
  and XLI, and drops utilities and real estate (36:06-36:37). **[unclear]** which six: "the consumer, the XLY"
  may be one sector or two, and at 32:42 he calls XLY "healthcare". `sector_rotation --six` takes XLV as the sixth
  **[inferred]**.
- **He has not traded it**: "I have not employed this at all, personally" (35:44); he plans to backtest it.

## 5. Execution

- At the desk at 9:29 for the 9:30 open (16:25). Takes positions off before Fed announcements, or brackets the
  market with orders on both sides (16:38-17:15).
- Heikin-Ashi candles to see the trend through the gaps (13:26).

## 6. Risk and sizing

- **Leveraged-ETF decay**: 3x is a one-day multiple only; a flat or falling market erodes it every day; three 10%
  down days need a 37% gain to recover (51:09-52:05). TQQQ fell 61% in 2022 (59:05); its drawdowns have been 50%,
  70% and 80% (53:56).
- **TQQQ's record is a timing accident** **[his point]**: it listed in February 2010, a year after the 2009 low
  (58:42-58:58). He had an AI estimate TQQQ over 2000-2009 — "you would have lost all your money twice" (54:05).
- **Cash in a bear market**: money market funds, T-bill ETFs (SGOV, BIL) (59:50-60:16).
- Wins at least twice the losses in dollars (65:11); start a new method with small money (18:41).

## 7. Management and exits

- Hard sell rules, written before the trade; a "soft" rule you can postpone is a mistake (63:11-63:43).
- Put the stop in immediately after the purchase; a trailing stop or a moving average works (65:55-66:08).
- Adjust averages to the instrument (a 21, 22 or 24 instead of a 20) **[his advice; not followed here]** (15:25).

## 8. Process

- Backtests with AI: feed it your own split- and dividend-adjusted data, spell out every rule, have it ask
  questions first, and check one AI with another (19:02-23:16).
- Expect live results to fall short of the backtest (21:33).
- **Overfitting**: "the more variables you have, the more risk that it will never work in real time" (73:45). A
  backtest equity line that goes "straight to heaven" means something is wrong; a 10-20% drawdown is healthy (74:03).
- Read widely; separate the trading and investing accounts (75:27).

## 9. Nuances worth keeping — and what the data here says

*Measured here, not his claims. Every rule's setting was fixed before the first run; the pass rules were written
before any result was read. Optimise stage = 2013-2021, **in-sample**; 2000-2012 is **context** only. No verify run
has been made.*

**TQQQ timing** (`masonson_tqqq` 1.0, a synthetic 3x Nasdaq 100 that tracks the real fund at 0.9986 daily
correlation; pass = beat QQQ, drawdown no deeper than QQQ's, 20+ round trips):

| Run (optimise, in-sample) | CAGR % | vs QQQ | Max DD % | Sharpe | Win % | Trades | Invested |
|---|---|---|---|---|---|---|---|
| QQQ held | 23.01 | — | -28.6 | 1.16 | — | — | 100% |
| Synthetic 3x held | 57.32 | +34.31 | -69.9 | 1.07 | — | — | 100% |
| 3x bought after a 25% fall, held | 43.80 | +20.79 | -69.9 | 0.94 | — | — | 71% |
| Default: 200-day + exit below 20 EMA | 21.13 | -1.88 | -55.5 | 0.73 | 43 | 139 | 68% |
| + MACD 12,26,9 | 11.43 | -11.58 | -49.9 | 0.50 | 40 | 91 | 57% |
| + MACD 6,13,5 (his) | 19.52 | -3.49 | -43.9 | 0.70 | 43 | 112 | 63% |
| + RSI(7) < 30 | 11.83 | -11.18 | -28.8 | 0.73 | 53 | 40 | 22% |
| + Keltner 2-ATR | 8.86 | -14.15 | -15.7 | 0.73 | 57 | 21 | 12% |
| + breadth < 20% | 11.64 | -11.37 | -19.3 | 0.77 | 60 | 5 | 7% |
| No trend filter | 25.70 | +2.69 | -50.8 | 0.82 | 44 | 143 | 72% |
| 200-day on the 3x series | 14.22 | -8.79 | -62.1 | 0.57 | 42 | 138 | 65% |
| Exit below 8 EMA | 15.27 | -7.74 | -50.0 | 0.59 | 43 | 210 | 63% |
| Exit below 10 EMA | 17.56 | -5.45 | -50.0 | 0.65 | 43 | 191 | 64% |
| All extremes together | 17.33 | -5.68 | -28.2 | 0.86 | 59 | 27 | 22% |

| Run (2000-2012, context) | CAGR % | Max DD % | Trades |
|---|---|---|---|
| QQQ held | -2.40 | -83.0 | — |
| Synthetic 3x held | -36.06 | -99.98 | — |
| 3x after a 25% fall | -34.03 | -99.98 | — |
| Default | -12.40 | -90.0 | 188 |
| All extremes together | +3.31 | -34.4 | 34 |

- **His decay warning is right** **[measured]**: held through 2000-2012 the 3x is wiped out, and the 25%-fall entry
  does not save it (the first 25% fall came in 2000).
- **No version passes in-sample.** The plain 200-day rule keeps most of the 3x run-up in 2017-2020 but gives it
  back in 2015-16 chop (-55%), deeper than QQQ's worst. Adding his oversold extremes cuts the drawdown to QQQ's
  level, at three-quarters of QQQ's return and 22% time invested. Tighter EMA exits, his favoured 8 and 10, were
  worse than 20.
- **Inferred:** his claimed 29% CAGR at a 45% drawdown (73:00) is not reproduced by these textbook settings; his
  own settings may differ, and his figures are his.

**Sector rotation switches** (`sector_rotation` 1.2; pass = beat the benchmark, no deeper drawdown, beat the 1.1
default; optimise, in-sample):

| Run | US CAGR % | Excess | DD % | Trades | India CAGR % | Excess | DD % | Trades |
|---|---|---|---|---|---|---|---|---|
| Benchmark | 14.01 | — | -34.1 | — | 13.54 | — | -38.3 | — |
| 1.1 default (month-end, 6 months) | 11.47 | -2.54 | -30.7 | 98 | 15.11 | +1.57 | -31.4 | 42 |
| Weekly, 12 weeks | 5.99 | -8.02 | -37.9 | 313 | 9.88 | -3.65 | -38.1 | 160 |
| Weekly, 8 weeks | 7.65 | -6.36 | -33.9 | 365 | 11.31 | -2.22 | -33.7 | 175 |
| Weekly, 4 weeks | 6.25 | -7.75 | -35.8 | 473 | 11.89 | -1.65 | -38.9 | 242 |
| Hold while top 4 | 10.38 | -3.63 | -34.4 | 66 | 12.16 | -1.38 | -39.8 | 18 |
| Exit below 20 EMA | 0.88 | -13.13 | -34.2 | 239 | 2.49 | -11.04 | -50.3 | 199 |
| All three | 1.22 | -12.79 | -25.7 | 483 | 4.92 | -8.61 | -64.7 | 362 |
| Six sectors | 15.15 | +1.14 | -29.9 | 40 | — | | | |
| All three + six | 2.98 | -11.03 | -20.3 | 374 | — | | | |

- **Every one of his switches made the rule worse, in both markets.** Weekly ranking triples the trading; the EMA exit
  sells a leader on a dip and leaves the money idle until month-end.
- **Six sectors passes in the US only, and it is hindsight**: he picked the six in 2026 for having done best.

## 10. How it compares

- His sector rule is the same relative-strength idea as `sector_rotation` (month-end, six months, top 3), at a
  weekly cadence with a rank buffer and an EMA exit; the buffer is the same device as momentum books' "hold while in
  the top N".
- His 200-day rule for leveraged longs is Faber's moving-average idea (`ma_trend`) applied to a 3x fund, on daily
  closes.
- Minervini is cited as the model for never breaking your rules (64:07-64:43).

## 11. Open questions

- Which six sectors (§4.4)?
- What settings the workshop strategy uses, and how its indicators combine (all at once, or a count)?
- Whether bullish percent adds anything the breadth reading does not (not built: it needs a point-and-figure
  signal per member).

## 12. Source log

- Tradeline podcast (powered by Deepview), interview with Les Masonson, host Richard; recorded autumn 2026 (the
  slides are dated August 7 and October 16). Transcript: local speech-to-text, 76 minutes.
