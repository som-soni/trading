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

*First batch, 2026-11-10: the exit variants and the trend-break reset (optimise, 2013–2021). Each changes one
thing against the 1.57 baseline. The sizing, gate, lean-exit and follow-up-buy variants are still running.*

| Variant | India CAGR | Sharpe | Max DD | Trades | US CAGR | Sharpe | Max DD | Trades |
|---|---|---|---|---|---|---|---|---|
| Baseline 1.57 (#3754 / #3758) | 3.71% | 0.50 | −20.1% | 323 | −3.30% | −0.26 | −40.3% | 1255 |
| Breakeven and partial at +3R, not +2R (#3752 / #3738) | 3.57% | 0.47 | −20.3% | 319 | −2.75% | −0.20 | −33.8% | 1201 |
| Strength sale halved (#3753 / #3750) | 3.43% | 0.51 | −18.1% | 323 | −3.26% | −0.29 | −39.2% | 1258 |
| Base anchoring: trend break resets (#3764 / #3761) | 4.15% | 0.55 | −17.6% | 350 | −3.05% | −0.23 | −36.8% | 1307 |
| Trend exit needs volume (#3769 / #3765) | 8.59% | 0.93 | −21.0% | 273 | −1.15% | −0.05 | −32.7% | 1083 |
| Two closes under the 50-day (#3770 / #3766) | 5.55% | 0.67 | −20.8% | 300 | −0.82% | −0.01 | −29.2% | 1095 |
| **After +3R, the 100-day** (#3771 / #3767) | **8.89%** | **1.00** | −24.4% | 265 | 1.24% | 0.17 | −22.7% | 1042 |
| **After +3R, the 150-day** (#3772 / #3768) | 8.26% | 0.96 | −20.9% | 251 | **3.08%** | **0.31** | **−23.9%** | 962 |
| *Earlier: always full size (v1.55, #2350 / #3281)* | 5.17% | 0.53 | −21.5% | 329 | −1.45% | −0.04 | −37.1% | 1192 |

**Reading.**

- **The replay was right about exits.** Giving a trade that reached +3R room to its 100- or 150-day more than
  doubles India's CAGR (3.7% → 8.3–8.9%), and is the first change in this series to turn the US positive (+3.1%,
  with the drawdown nearly halved). The 150-day is the one that works in both markets.
- **Trims at +2R barely matter in a portfolio.** Moving the partial and breakeven to +3R, or halving the strength
  sale, moves CAGR by under half a point either way. The cost of the early sales in the replay comes mostly from
  the light-volume and time-stop exits, which the lean variants test.
- Requiring volume on the trend exit (one close under the 50-day only counts on heavy volume) is nearly as good in
  India (8.6%) and helps the US less. It is a different route to the same thing: fewer exits on a quiet dip.
- The trend-break reset is a small gain in both markets (+0.4 / +0.25 points): adopt it on the book-case
  evidence, not for CAGR.

*Second batch, 2026-11-10: sizing, the segment gate, lean exits, follow-up buys and no near-miss setups (optimise,
2013–2021). Each again changes only what it names against the 1.57 baseline (3.71% India, −3.30% US).*

| Variant | India CAGR | Sharpe | Max DD | Trades | US CAGR | Sharpe | Max DD | Trades |
|---|---|---|---|---|---|---|---|---|
| Always full size (#3778 / #3782) | 5.17% | 0.53 | −21.5% | 329 | −1.45% | −0.04 | −37.1% | 1192 |
| Full size, 1.5% risk, 9% open risk (#3779 / #3790) | 4.27% | 0.39 | −28.4% | 324 | −0.20% | 0.06 | −39.5% | 1072 |
| Segment trend added to the gate (#3776 / #3780) | 5.34% | 0.67 | **−15.6%** | 293 | −3.63% | −0.31 | −42.4% | 1145 |
| Segment trend alone, index and breadth dropped (#3777 / #3781) | 4.80% | 0.60 | −17.3% | 351 | −0.46% | 0.01 | **−22.4%** | 1225 |
| No near-miss setups (#3775 / #3774) | **6.70%** | 0.82 | −19.0% | 308 | −2.88% | −0.25 | −41.5% | 1288 |
| Lean exits (#3791 / #3804) | 8.04% | 0.82 | −21.5% | 260 | 2.42% | 0.26 | −20.3% | 507 |
| Lean + 150-day after +3R (#3796 / #3820) | 6.12% | 0.70 | −24.1% | 209 | **5.02%** | **0.44** | −25.9% | 369 |
| Follow-up buys (#3823 / #3825) | 5.49% | 0.61 | −24.9% | 325 | −3.29% | −0.25 | −37.8% | 1259 |
| Follow-up buys + 150-day after +3R (#3824 / #3827) | 7.03% | 0.71 | −28.9% | 289 | −1.74% | −0.10 | −31.2% | 1075 |
| *For comparison: 150-day after +3R alone (#3772 / #3768)* | *8.26%* | *0.96* | *−20.9%* | *251* | *3.08%* | *0.31* | *−23.9%* | *962* |

**Reading.**

- **More risk did not buy more return.** At 1.5% risk with a 9% open-risk cap, India's CAGR *fell* (5.2% → 4.3%) and
  its drawdown deepened by 7 points. The scaling estimate in section 1 assumed the extra risk would go into the same
  trades; in the portfolio it goes into more, weaker trades and larger losses in the bad stretches. That estimate was
  wrong, and the sizing lever is closed until the average trade is better. Full size at 1% helps a little (+1.5 points).
- **Exits remain the lever.** In India, the 150-day after +3R alone (8.26%) beats every combination with it. Dropping
  the early sales too (lean + 150) loosens too far: the win rate falls to 26% and CAGR to 6.1%. In the US the order
  reverses: lean + 150 is the best US result so far (+5.0%, Sharpe 0.44), because the US trades' early sales cost more
  than India's.
- **The segment gate helps the drawdown more than the return.** In India it adds 1.6 points and cuts the maximum
  drawdown from −20.1% to −15.6%. In the US, the segment trend alone in place of the index test turns −3.3% into
  −0.5% and halves the drawdown (−40% → −22%). Adding it on top of the index test does nothing there.
- **The near-miss setups cost India 3 points.** Taking them out raises CAGR from 3.7% to 6.7% with a shallower
  drawdown. In the US the effect is small (+0.4).
- **Follow-up buys do not pay in the portfolio.** With or without the 150-day exit they lower CAGR and deepen the
  drawdown in both markets. The book cases showed Minervini adding; in this backtest the adds mostly arrive late in
  the move and get stopped out.

**Next: the combined candidate.** Each change was measured alone, so the gains need not add up. Queued on the same
window, both markets:

- **A:** 150-day after +3R + no near-miss setups;
- **B:** A + the segment trend added to the gate;
- **C:** A + the segment trend in place of the index test;
- **D (US only):** lean exits + 150-day + segment trend in place of the index test, the US's own best levers.

The pick among them follows a rule fixed now: the highest CAGR in India whose maximum drawdown is no deeper than
−22%, provided the same configuration does not lower the US result against the US baseline. That one candidate
becomes a new version and gets its single verify run, with pass criteria written before it runs.

## The gap-day backstop (1.60), queued 2026-11-10

From the [Minervini team's June 2026 trade review](creator-mark-minervini.md) §12: once a trade is well in profit, a
gap up moves the stop to the gap day's low and ratchets it on each later gap. Built as a research switch
(`GAP_BACKSTOP_R`, `GAP_BACKSTOP_ATR` = 1 ATR; off). Optimise stage, both markets:

| Variant | Compared with |
|---|---|
| Backstop from +3R, with the 150-day after +3R | 150-day after +3R alone (#3772 India 8.26%, #3768 US 3.08%) |
| Backstop from +2R, with the 150-day after +3R | the same |
| Backstop from +3R alone | the 1.57 baseline (3.71% / −3.30%) |
| US only: backstop from +3R with lean exits and the 150-day | lean + 150-day (#3820, 5.02%) |

**Decision rule, fixed now:** the backstop joins the combined candidate only if, at the same R level, it raises CAGR
in **both** markets against its comparison run without deepening the maximum drawdown by more than 1 point.
Otherwise it is recorded as a failure.

## The add on a natural reaction (1.61), queued 2026-11-10

From [Minervini's ANF clip](creator-mark-minervini.md) §13: a held winner that pulls back to its 20-day average is
added to as it turns up over the previous session's high. Each add has its own stop under the reaction low; the first
buy keeps its stop. Built as a research switch (`REACTION_ADD`, a fraction of the first buy; at most
`REACTION_ADD_MAX` = 2; a pullback of 5%+ whose low comes within 2% of the 20-day, closing above the 50-day and the
cost; off). On ANF alone it adds on 3 Feb 2021 ($23.91) and 11 Feb ($25.04), his two dates. A rough replay on
existing trades (that section) was positive in India and not in the US, so India leads. Optimise stage:

| Variant | Compared with |
|---|---|
| India: add half the first buy, with the 150-day after +3R | 150-day after +3R alone (#3772, 8.26%) |
| India: add the full first buy, with the 150-day after +3R | the same |
| India: add half, alone | the 1.57 baseline (#3754, 3.71%) |
| US: add half, with the 150-day after +3R | 150-day after +3R alone (#3768, 3.08%) |
| US: add half, alone | the 1.56 baseline (#3758, −3.30%) |

**Decision rule, fixed now:** the add joins the combined candidate only if it raises India's CAGR beside the 150-day
exit with the maximum drawdown no more than 2 points deeper (an add is extra exposure, so some extra drawdown is the
price), **and** the same setting does not lower the US CAGR against #3768. A win in India alone is recorded as an
India-only result, not adopted, because the replay already showed the US does not support it.

## A tighter stop cap (SL-03), queued 2026-11-10

From the Manappuram 2018 review ([creator notes](creator-mark-minervini.md) §9.3): an early failed-breakout exit lowered
average R in both markets. The narrower idea is to skip wide-stop entries instead, nearer Minervini's 5–6% average loss.
`MAX_STOP_PCT` (10%) skips a fill whose stop is further below it; the power play keeps its own 20% cap. The constant is
read after the scan, so these runs copy the cached signals.

| # | Market | `MAX_STOP_PCT` | Compared with |
|---|---|---|---|
| 1440 | India | 8 | #3754 (3.71%) |
| 1441 | India | 6 | #3754 |
| 1442 | US | 8 | #3758 (−3.30%) |
| 1443 | US | 6 | #3758 |

**Decision rule, fixed before the results:** a cap is adopted only if the same value raises CAGR in both markets against
its comparison run, with max drawdown no more than 1 point deeper. A win in one market only is recorded, not adopted.
