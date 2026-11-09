# Why a 40% win rate makes only 7.9% a year — the Minervini strategy's CAGR gaps

*2026-11-10. A diagnosis of the best India optimise run (#2778: v1.41 with looser cheat rules, 7.91% CAGR, 39.6% wins,
2013–2021), checked against the current baselines (1.57: India #3754, 3.71%; US #3758, −3.30%). All numbers are
in-sample (the optimise window). Each proposed change is queued as an optimise-stage variant; anything adopted then
gets one verify run as its own version.*

**In short**

- **The trades are not the main problem; the capital is.** The average trade earns +0.37R. But the book is only 29%
  invested on average (median 18%), each trade risks about 0.68% of equity (half size most of the time), and the
  market gate is open on 43% of days. 30 trades a year × 0.37R × 0.68% ≈ 7.5% a year: the CAGR follows from that.
- **Idle cash earning nothing costs about 5.7 points.** Parked in India's liquid-fund index, the same run makes
  13.6% a year with a −14% drawdown: level with the Nifty 500's 13.5%, at a third of its −38% drawdown.
- **The trade-management rules give the edge away.** Replaying every trade on its own, the plain 50-day exit beats
  the strategy's full rule set (India 1.57: +0.48R against +0.20R per trade). Letting a trade that reached +3R run
  to a close under its 100- or 150-day roughly doubles expectancy, in both markets and all three runs. Every
  tighter exit tried does worse.
- **Stock selection at entry adds nothing measurable.** Not RS rank, not the RS line, not how the stock held up in
  the market's last correction. What does sort the trades is the **market segment's** trend. Trades taken while the
  small/mid-cap index was flat or falling over three months lost money in every run.
- **The US has no edge to scale.** It averages −0.04R per trade over 1,255 trades, and its winners rarely move:
  the median best open gain is 0.55R. Only the looser exits turn it slightly positive. India is where the levers apply.

## 1. The arithmetic of CAGR

A trading book's return is roughly **trades per year × average R × risk per trade (% of equity)**, plus whatever
the idle cash earns.

| | Run #2778 |
|---|---|
| Trades a year | 30.2 |
| Average R | +0.365 |
| Risk per trade, as taken | median 0.5%, mean 0.68% of equity (configured 1%, halved by progressive exposure most of the time) |
| Position size | median 8.4% of equity |
| Positions held | 3.2 on average (cap 8) |
| Share of equity invested | mean 29%, median 18%; by year 3% (2013) to 65% (2021) |
| Market gate open | 43% of days |
| Cash yield | none (the simulator credits nothing on cash) |

30.2 × 0.365 × 0.68% ≈ 7.5% a year, against the 7.9% measured. To beat the index, at least one of the factors has
to grow, or the cash has to earn.

The run's Sharpe ratio (0.85) equals the index's (0.86). Its advantage is the shallow drawdown: −15.9% against −38.3%.
A strategy with the index's risk-adjusted return and a third of its drawdown can carry more risk per trade. A rough
scaling of the run's daily returns, with the extra exposure taken out of idle cash:

| Risk per trade | CAGR | Max drawdown |
|---|---|---|
| As run (≈0.68%) | 7.9% | −15.9% |
| ×1.5 | ≈16.8% | ≈−21% |
| ×2 | ≈20.1% | ≈−27% |

That is an estimate: the portfolio's own limits (8 slots, 6% open risk, 25% per position) are not in it. The queued
sizing variants measure it properly.

## 2. Idle cash

On average 71% of the equity sat in cash earning nothing. India's liquid-fund index (`CASH_FUND`) returned about 7%
a year over 2013–2021. Crediting that on each day's idle cash:

| | CAGR | Max drawdown |
|---|---|---|
| Run #2778, cash earns nothing | 7.91% | −15.9% |
| The same, idle cash in the liquid fund | **13.58%** | −14.0% |
| Nifty 500, buy and hold | 13.54% | −38.3% |

This is not an edge in the strategy. It is what a trader does with money not in a trade. But comparing a book that
earns nothing on 71% of its capital with an index that is always invested understates the strategy. US T-bills
paid far less over these years, so the effect there is small.

**Proposal:** a simulator option to credit the market's cash series on idle cash, reported beside the plain figure.

## 3. Exits: the management rules give the edge away

Every trade of three runs was replayed on its own from its real entry and initial stop, under different exit rules.
Mean R per trade:

| Exit (trades replayed alone) | IN #2778 | IN 1.57 | US 1.57 |
|---|---|---|---|
| Actual (the strategy's full rules) | +0.37 | +0.20 | −0.04 |
| Close below the 50-day, nothing else | +0.49 | +0.48 | −0.00 |
| Two closes below the 50-day | +0.49 | +0.50 | −0.01 |
| After +3R, close below the 100-day | **+0.82** | +0.86 | +0.08 |
| After +3R, close below the 150-day | +0.71 | **+0.97** | **+0.09** |
| After +3R, close below the 21-day (tighter) | +0.29 | +0.37 | −0.03 |
| Chandelier: 3 ATR under the highest close | +0.33 | +0.21 | +0.02 |
| Lock +1R at 3R, trail 2R under the high from 5R | +0.33 | +0.26 | −0.02 |

Each rule on top of a plain 50-day exit, India 1.57 / US 1.57:

| Rule added | IN | US |
|---|---|---|
| None (50-day only) | +0.48 | −0.00 |
| Breakeven stop at +2R | +0.47 | +0.00 |
| A third sold at +2R | +0.38 | −0.01 |
| A third sold 25% above the 50-day | +0.43 | −0.00 |
| Time stop: +1R within 15 sessions | +0.41 | −0.01 |
| Light-volume fill sold next open (applied to every trade here; the strategy applies it to S2/S8 only) | +0.26 | −0.04 |

**Reading.** Winners kept only a third to two-fifths of their best open gain (India: median best +2.5R, median
result +0.67R). India's trend exits gave back a median 1.8R from the peak. The cure is not a tighter exit — every
tighter one did worse — but fewer early sales and more room once a trade has proven itself. The big winners pay
for everything (India: the top 5% of trades), and each early sale takes a piece of exactly those.

Holding longer costs little here: the book averages 3.2 positions against a cap of 8, so a held winner rarely
blocks a new trade.

Book support: Minervini holds a stock that acts right and raises his stop to protect a gain, and David Ryan's MVP
is his reason not to sell an extended leader. Selling a third at +2R is closer to a short-term trader's rule than
his.

## 4. Selection: what predicts a trade, and what does not

For each trade, entry-time measures were bucketed into quarters, with mean R per quarter, in three runs (IN #2778,
IN 1.57, US 1.57). None of these ordered the trades the same way in all three:

- RS rank (70–99);
- RS line at a 52-week high (India: *worse*, +0.01R against +0.28R; US: no difference);
- the stock's return over the market's worst decline of the past year, minus the market's (your notes' "held up
  in the downturn"), and its own drawdown in that decline;
- 6-month return, distance below the 52-week high, extension above the 50-day, ATR, stop width, traded value;
- the SEPA earnings verdict (ACCEPTABLE beat WEAK in one India run and lost in the other).

That fits the [breakout anticipation study](breakout-anticipation-study.md): once a stock has passed the Trend
Template and formed a VCP, more filters of the same kind add little. The "held up in the downturn" idea works at a
different level: it decides **which stocks reach the watchlist** (the Trend Template and RS ≥ 70 already do this).
It does not rank the survivors. The watchlist built on 2026-11-09 ("Held up in the 2026 decline") is that use.

**What did sort the trades: the segment's trend.** The 3-month return of the small/mid-cap index at entry (here the
Nifty Midcap index for India and IWM for the US; the gate switch below reads the Nifty Smallcap 250, which gives the
same ordering):

| Small-cap index, 3-month return | IN #2778 | IN 1.57 | US 1.57 |
|---|---|---|---|
| ≤ 0% | −0.34R (n 25) | −0.36R (n 25) | −0.05R (n 204) |
| 0–3% | −0.23R (n 26) | −0.22R (n 29) | −0.11R (n 190) |
| 3–10% | +0.40R (n 101) | +0.13R (n 98) | −0.06R (n 598) |
| > 10% | +0.61R (n 120) | +0.39R (n 171) | +0.08R (n 263) |

Our market gate reads the **benchmark** (Nifty 500, SPY) above a rising 50-day, plus breadth. The benchmark can rise
while the stocks a breakout book holds fall. India 2018: the Nifty rose, small caps fell by a third, and the
strategy's 14 trades that year won once.

## 5. The levers, ranked, and how each is being tested

| # | Lever | Why | Test (optimise, both markets) |
|---|---|---|---|
| 1 | **Exits: drop the early sales, give proven winners room** | Replay: +0.2 to +0.5R a trade | "Lean" (no partial at +2R, no strength sale, no time stop, no light-volume exit, no breakeven), and lean + after 3R the 150-day: #1364–1367. Looser alone: #1345/1346, #1349/1350 |
| 2 | **Deploy the capital** | 29% invested; risk halved most of the time | Full size always (`--pe-pilot 1.0`): #1358, #1362. Plus 1.5% risk and a 9% open-risk cap: #1359, #1363 |
| 3 | **Credit idle cash** | +5.7 points on #2778, in India | A simulator option (proposed) |
| 4 | **Gate on the segment, not the benchmark** | Only measure that sorted trades in every run | Segment's 3-month trend added to the gate: #1356, #1360. Segment trend alone, benchmark and breadth dropped: #1357, #1361 |
| 5 | **Follow-up buys into winners** | Book; only matters once winners are held | `ADD_ON_NEW_BASE=0.5`, with the 150-day exit (queued after the smoke test) |
| — | Selection filters (RS line, "held up") | No signal at the trade level | Not tested as filters; RS-line study (Q2) for the closed-gate case |

The levers multiply. If exits lift the average trade from +0.37R to +0.6R, full size lifts risk from 0.68% to 1%,
and idle cash earns the liquid-fund rate, India's 7.9% becomes roughly 30 × 0.6 × 1% ≈ 18%, plus the cash yield.
That is an estimate to be measured, not a forecast: costs, slots and the open-risk cap will take some of it, and every
number here is in-sample.

## 6. What this does not fix

- **The US.** Its setups have shown no edge in 2013–2021 under any exit or filter tried here. The best version
  measured is +0.09R a trade. Scaling it up scales the loss. It needs its own work, starting from why US breakouts
  in this universe rarely follow through.
- **In-sample risk.** Every comparison is on 2013–2021. A combination of levers chosen from these results gets one
  verify run on 2022 on, as a new version, with pass criteria written first.

## Results

*To be filled in as the queued runs land.*
