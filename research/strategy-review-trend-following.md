# Strategy family review: trend following

*Written 2026-11-12. Strategies: `donchian` (v1.5), `turtle_trend` (v1.0), `ma_trend` (v2.4).
Brief: `research/strategy-family-review-briefs.md`, family 4. Procedure: `/backtest-review`.*

Everything below comes from the **optimise stage (2013-01-01 → 2021-12-31)**. None of the three
strategies has a verify run (`verify_runs` has no row for any of them), so there was no verify verdict
to quote. Legacy and full runs are used as context only. Figures marked *computed* were worked out
here from stored data (prices, `bsig_donchian__v1_5_de67ca74`, run tables) with scratchpad scripts.
They were not taken from a report. Scratchpad probes ran repo code with constants changed in memory
only. **They are trials and hypotheses, not results**, and are counted as trials below.

## In short

- **No strategy in this family has a return edge over buy-and-hold in the optimise window.** All
  five baselines trail their benchmark's CAGR. All five edge badges say "No edge".
- **`ma_trend` delivers what Faber actually claimed.** That claim is about the same Sharpe at about
  half the drawdown, not more return. It is the family's best version today. The excess-CAGR yardstick
  is the wrong judge for it, and its biggest fidelity gap is that it times one index, not Faber's
  five-asset portfolio.
- **`donchian` has a selection edge in India but not in the US.** Its book has mechanical leaks that
  cost the method's edge before the rules get a chance:
  - 11–39% of trades are "crumbs" (positions under 3% of equity) that hold a slot.
  - 74% of US fills come 2 or more sessions after the breakout, and those trades average +0.12R,
    against +0.80R for fills on the next session.
  - Ranking results sit inside path noise that has never been measured.
- **`turtle_trend` fails, and the fidelity probes do not rescue it.** Unit sizing, a 28-ETF universe
  and a looser gross cap all give Sharpe ≤ 0.25. The method's record is on diversified futures. ETF
  proxies in 2013–2021 (no long bear market, and a known weak spell for trend following in general)
  are probably not where that record can be reproduced.
- **The window under-samples trend following's payday.** 2013–2021 holds no slow, prolonged bear
  market. 2020's crash and recovery took weeks. Every pass criterion below is therefore written on
  risk-adjusted terms and drawdown, not on excess CAGR alone.

---

## 1. `donchian`: Donchian channel (Turtle System 2 on stocks)

### 1.1 Runs reviewed

| Run | Market | Version | Stage | Overrides | Role |
|---|---|---|---|---|---|
| 1735 | US | 1.5 | optimise | none (own `backtest_args`) | **baseline** |
| 1730 | India | 1.5 | optimise | none | **baseline** |
| 2356 / 2357 | US / India | 1.5 | optimise | `--market-filter` | variant tested |
| 3127 / 3124 / 3128 | US | 1.5 | optimise | `--rank-by random --market-filter` / `--rank-by setup --market-filter` / `--rank-by random --pe` | variants tested |
| 2336 / 3131 | US | 1.5 | optimise | `--equal-alloc 10` / `--max-positions 8 --equal-alloc 12.5` | variants tested |
| 1724 / 1726 | US | 1.5 | optimise | `--market-filter --pe` / `--market-filter --donchian-bars 30` | variants tested |
| 1718 / 1719 / 1721 / 2657 | India | 1.5 | optimise | `--donchian-bars 30` / `--donchian-bars 20` / `--max-open-risk 6` / `--pe` | variants tested |
| 15 runs | both | 1.4 | optimise | ranking (`random`, `momentum`, `vol_scaled`, `setup`), `--market-filter`, `--max-positions 20` (± `--risk-pct 0.005`) | earlier version, context |

v1.5 changed only the simulator (fill timing, the fill-session stop test). v1.4 runs are therefore not
comparable number-for-number. The Strategy page `status` still quotes v1.4 figures (India excess
+1.62). **That text is stale.** The v1.5 India baseline is −1.69 (see §5, shared fix F6).

### 1.2 Scorecard (optimise stage, own `backtest_args`)

| Key parameter | US (1735) | India (1730) |
|---|---|---|
| CAGR / benchmark | 3.61% / 14.01% | 11.85% / 13.54% |
| Excess CAGR (std costs) | −10.40 (−10.49) | −1.69 (−2.74) |
| Max drawdown / benchmark | −42.5% / −34.1% | −29.4% / −38.3% |
| Longest drawdown | 1,244 sessions | 750 sessions |
| Sharpe / Sortino / Calmar | 0.27 / 0.24 / 0.08 | 0.69 / 0.62 / 0.40 |
| Trades (per year) | 405 (45) | 269 (30) |
| Win rate | 23.8% | 34.0% |
| Avg R (closed) / profit factor | +0.20 / 1.03 | +0.67 / 1.46 |
| Exposure / invested *(computed)* | 99.6% of days / 95% | 99.0% / 92% |
| Turnover / costs | 3.9× / $2,371 | 2.7× / ₹132k |
| Avg days held *(computed)* | 79 | 113 |
| R by exit: STOP | 272 trades, −1.05R | 148, −1.03R |
| R by exit: TREND_EXIT | 123 trades, +2.98R, median 158 days | 111, +2.95R, 189 days |
| Years beating benchmark *(computed)* | 3 of 9 | 4 of 9 |

### 1.3 Is the edge real?

**Trials.** There are 30 optimise runs (v1.4 + v1.5, 18 US and 12 India), and 33 recorded runs with a
Sharpe once legacy runs are counted. The standard deviation of the trials' annual Sharpes is 0.25.
Deflated Sharpe follows Bailey & López de Prado, with these inputs: daily returns of the baseline
(T ≈ 2,260), its skew and kurtosis, N trials, and the trials' Sharpe variance.

| Run | Sharpe | Expected max Sharpe of N null trials | DSR (N=30) | DSR (N=33, incl. legacy) | P(Sharpe > benchmark's) *(PSR)* |
|---|---|---|---|---|---|
| US baseline 1735 | 0.27 | 0.53 | 0.22 | 0.23 | 0.03 |
| India baseline 1730 | 0.69 | 0.53 | 0.68 | 0.69 | 0.31 |
| India `--market-filter` 2357 (best trial) | 0.99 | 0.53 | 0.91 | 0.91 | 0.65 |
| US `--rank-by random --market-filter` 3127 | 0.61 | 0.53 | 0.59 | 0.60 | 0.21 |

No run clears 0.95 on DSR. None is confidently above its benchmark's Sharpe either (0.88 US,
0.86 India).

**Selection vs timing.** This is a matched random-entry null *(computed, 500 draws)*. For each closed
trade it draws a stock from the pre-filter pool on the signal date (null A), or from the part of that
pool above its 200-day average (null B). The draw is held from the trade's entry open to its exit
close.

| Run | n | Trade mean | Same stock, same dates, no stop | Null A mean [5–95%] | Trade percentile vs A / B |
|---|---|---|---|---|---|
| US 1735 | 395 | +1.04% | +2.12% | +2.76% [1.34, 4.16] | **2.4 / 5.6** |
| India 1730 | 259 | +5.84% | +6.58% | +3.46% [1.23, 5.98] | 94.4 / 98.8 |
| US 3127 (random rank + filter) | 285 | +3.68% | +4.28% | +2.01% [0.30, 3.86] | 92.6 / 91.0 |
| India 2357 (filter) | 227 | +4.99% | +5.75% | +1.10% [−0.97, 3.30] | 98.8 / 97.8 |

- In the US, the baseline's momentum-ranked trades did **worse than random stocks held over the same
  dates**.
- The same signals with a random tie-break and the market filter sit at the 93rd percentile.
- India shows a selection edge in both runs.
- The stop costs about 0.6–1.1 points per trade against holding to the same exit date. Exits are
  not the leak.

**Signal edge vs portfolio mechanics** *(computed)*. "Tradeable" means S1 with both gates and no watch
flag. Returns run from the next open. Stored prices go to 2021-12-31.

| Set | US n | US f5 / f20 / f60 | US MFE60 / MAE60 | India n | India f5 / f20 / f60 |
|---|---|---|---|---|---|
| All pre-filter bars (base rate) | 2,870,168 | +0.23 / +1.05 / +3.27% | — | 255,752 | +0.09 / +0.98 / +3.61% |
| Bars above the 200-day (G1) | 1,840,468 | +0.19 / +0.88 / +2.93% | — | 168,527 | +0.14 / +1.09 / +4.28% |
| All tradeable S1 signals | 63,625 | −0.03 / +0.36 / +2.49% | +12.8 / −10.7% | 6,974 | +0.06 / +1.39 / +4.62% |
| Traded | 402 | **−1.25 / −1.02** / +2.54% | +16.8 / **−15.3%** | 262 | −0.30 / +1.13 / +4.83% |
| Not traded, not held | 62,241 | −0.02 / +0.38 / +2.50% | +12.7 / −10.6% | 5,816 | +0.12 / +1.48 / +4.90% |
| First signal of a run (>30 days) | 25,555 | +0.05 / +0.45 / +2.45% | — | 2,685 | +0.06 / +1.41 / +4.51% |

- In the US, a 55-day breakout has **no forward-return edge** at 5, 20 or 60 sessions over the
  pre-filter base rate. It is slightly worse than a random bar above the 200-day.
- In India the breakout adds about +0.3 points over 60 sessions. That is small.
- The traded US signals were the most volatile ones: deeper MAE, and worse 5- and 20-session returns.
- Skipped signals were as good as the traded ones in both markets. The book (slots and ranking)
  adds nothing over a random draw from the signals.
- Repeat signals and first breaks do the same.

**What does separate signals** *(computed, all tradeable signals, f60 / share with f120 > 30%)*:

| Slice | US | India |
|---|---|---|
| ATR% quintile 1 (quiet) | +0.29% / 2.1% | +1.25% / 6.3% |
| ATR% quintile 5 (volatile) | +6.04% / 24.2% | +7.31% / 24.1% |
| 12-1 momentum, same-day bottom quintile | +1.98% / 10.9% | +2.48% / 15.5% |
| 12-1 momentum, same-day top quintile | +2.66% / 14.4% | +6.25% / 19.2% |
| At a 52-week high vs below it | +2.29% vs +2.88% | +4.67% vs +4.52% |

Volatility is the strongest separator in both markets: it gives a fatter right tail, and pays for it
with a deeper MAE. Momentum is monotonic in India and flat in the US. "At a 52-week high" adds
nothing.

**Concentration** *(computed)*.

| | US 1735 | India 1730 | India 2357 |
|---|---|---|---|
| Best 5% of trades' share of net R / net P&L | 213% / 454% | 85% / 93% | 103% / 115% |
| Best year / worst year | 2013 +54.1% / 2015 −26.0% | 2021 +69.1% / 2016 −15.9% | 2021 +117.4% / 2019 −16.5% |
| CAGR without 2021 (2013–2020) vs Nifty 500 price 11.7% | — | 6.2% | 8.5% |

India's in-sample margin is **2021 alone**. Without it, both the baseline and the filter variant trail
the index by 3–5 points a year.

**Verdict.**
- US: no edge of any kind as built, and negative selection.
- India: a real but modest selection edge. Every excess return comes from one year.
- The method (Turtle System 2 / Donchian breakouts) has a long documented record on diversified
  futures, and a practitioner record on stocks (see §1.4). So this is treated as an implementation
  and universe gap first.

### 1.4 The method: fidelity check

Sources:
- the original Turtle rules as published by former Turtles and in Curtis Faith, *Way of the Turtle*
  (2007);
- Richard Donchian's 4-week rule;
- Michael Covel, *The Complete TurtleTrader*.

| Rule | Originator | This code | Kind | Plausibly matters? |
|---|---|---|---|---|
| Market | 20+ liquid futures across asset classes, long and short | One country's stocks, long only, 10 slots | different | **Yes**: diversification and the short side are where the record lives (code caveat says so) |
| Entry | Intraday touch of the 55-day high (System 2) | Close above the 55-day high, buy-stop next session; **order rests 10 business days** | simplified + added | **Yes**: 301 of 405 US trades filled ≥2 sessions after the last signal (avg R +0.12 vs +0.80 for next-session fills, n=104); India +0.79 (n=138) vs +0.92 (n=131) |
| Unit size | 1% of equity per 1 N (so 2% to a 2N stop) | 1% to the 2N stop, capped at 25% notional, **then scaled to the cash left** | different | **Yes**: median realised risk 0.74% (US), 0.98% (India); 17% / 11% of trades are under 3% of equity, holding 19% / 16% of slot-days |
| Pyramiding | Add 1 unit every ½ N, up to 4; raise all stops to 2 N under the latest unit | None | missing | Probably: it is how the Turtles concentrated in the few big trends; `--pyramid` exists in the simulator, untested here |
| Stop | 2 N from entry | 2 ATR14, min 2%, never moves | same (ATR14 vs N20) | No |
| Exit | 20-day low (System 2); Donchian: 4-week low | 50-day low in the backtest; **20-day low on the live screen** | different (known choice) | Chosen from 8 exit policies on 879 signals (+0.095R); 20 and 30 bars tested in India (20 worse, 30 better), 30 + filter in the US (worse) |
| Portfolio limits | 4 units/market, 6 closely correlated, 10 loosely, 12 per direction | 10 slots, no correlation limit | different | Moderately: 10 stocks in one market are one correlated bet |
| Drawdown rule | Cut notional equity 20% per 10% drawdown | None | missing | Untested |
| Trend filter | None (both directions) | G1: close above the 200-day | added | Needed for long-only; it adds no forward-return edge (above) |
| Chase cap | None | G2: close ≤ channel + 1 ATR | added | Drops 15k US bars; small |
| Volume / wide-stop caps | None | W1, W2, the 15% stop rule | added | Removes 57k of 121k triggered US setups; untested |
| Ranking | None needed (all markets traded) | 12-1 momentum tie-break | added | Results move ±6 CAGR points between rankings, with no noise band measured |
| Market regime | n/a (shorts) | None in the backtest; live downgrade only | missing for a long-only book | Tested: `--market-filter` helps CAGR in 2 markets × 2 versions × 2 rankings |

**Literature.**
- Time-series momentum is documented across 58 futures and forwards (Moskowitz, Ooi & Pedersen,
  2012), and over a century of data (Hurst, Ooi & Pedersen, 2017). Its returns come from
  diversification across asset classes and from crisis periods.
- On single stocks, the evidence is thinner and mostly practitioner work:
  - Wilcox & Crittenden ("Does trend following work on stocks?", 2005, a fund white paper) found
    positive expectancy for all-time-high entries with wide trailing ATR stops;
  - George & Hwang (2004) document a 52-week-high effect, but as a cross-sectional ranking, not a
    timing entry.
- Practitioner consensus (Clenow, Covel) is that a single-asset-class book loses most of the
  diversification that makes trend following pay. Treat that as lore, not tested evidence.

**Known choices** (not re-proposed):
- the 50-day exit;
- removing the price floor (v1.1);
- the momentum tie-break (v1.3, measured only on India legacy data);
- the ranking variants and the `--max-positions 20` variants (v1.4);
- `--donchian-bars 20/30`, `--pe`, `--max-open-risk 6`, `--equal-alloc`, `--market-filter`
  (all already run).

### 1.5 Diagnosis

1. **The book is cash-bound, not slot-bound, and the leftover cash buys crumbs.** The simulator
   "buys what it can" with no minimum. 65 US trades (16%) were under 1% of equity, and their slots
   could not take a full-size breakout until they exited (median 29 days). The random-rank run
   (3127) had 39% crumbs. That is part of why `--equal-alloc 10` (7.00% vs 3.61% CAGR, US) did
   better: 10 × 10% fits the cash, so no crumbs.
2. **Stale fills.** An order rests for 10 business days and fills when a slot or cash frees up. By
   then the open can sit well above the channel, which the G2 chase cap never re-tests. US fills on
   the next session: +0.80R (n=104). Later fills: +0.12R (n=301). India: +0.92R (n=131) vs +0.79R
   (n=138). Both groups are over 30 trades. The US gap is large; the India gap is small.
3. **Ranking is a lottery we have not sized.** Each run trades about 0.6% of 63,607 US signals.
   - Without the filter, random beats momentum by +6.2 CAGR points (v1.4: 1405 vs 1233).
   - With the filter, they tie (2356 9.31% vs 3127 9.11%).
   - With PE, they tie (1724 7.41% vs 3128 7.51%).
   - India's +7.8 for momentum is a legacy figure.
   The ranking code takes a fixed seed (`rerank_signals(seed=20260101)`), so the seed-to-seed spread
   has never been measured.
4. **The market filter is the one robust lever already in hand.**
   - US: 3.61 → 9.31% CAGR. India: 11.85 → 17.23%.
   - It holds on v1.4 too, and with random ranking.
   - Drawdown is mixed: US −42.5 → −46.2% (momentum) but −26.2% (random). India −29.4 → −41.8%.
   - At signal level it does not select better signals (risk-off signals, n=2,409 US, did better).
     It works by keeping the book out of 2015-type tapes, which is portfolio mechanics.
5. **Losers are the stop, as designed.** STOP is 272 trades at −1.05R (US) and 148 at −1.03R (India),
   with a median of 11–19 days. Winners are the channel exit at about +3R. The shape is right. The
   US problem is that the winners are not selected better than random.

### 1.6 Improvements, ranked per key parameter

| Priority | Change | Parameter | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | **Minimum fill**: skip a fill below 50% of its intended size instead of buying crumbs (shared fix F1) | excess CAGR, avg R, trade count | 1735/1730/2356/2357/3127: 11–39% of trades under 3% of equity, holding 16–39% of slot-days; `--equal-alloc 10` (no crumbs) +3.4 pts US | more full-size trades in slots; fewer meaningless trades | fewer trades; more cash idle on some days | both markets, every run inspected; mechanism, not a fit | mechanics (code) |
| 2 | **Enter at the breakout only**: order expiry 1 session (`ENTRY_EXPIRY_BDAYS`, signal-exempt) | avg R, excess CAGR | US +0.80R (n=104) vs +0.12R (n=301); India +0.92R (131) vs +0.79R (138); the Turtle rule | higher avg R per trade; fewer late, extended entries | fewer fills; slots free longer | both markets same sign, US strong, India weak; untested at 2–3 sessions | from the method (code) |
| 3 | **Ranking noise band**: seeded random ranking, 10 seeds per market (shared fix F2) | trust in every ranking result | ±6 CAGR points between rankings; one fixed seed | tells whether any ranking beats chance | 20 extra runs (cheap; signals cached) | is itself the robustness test | mechanics (code: `--rank-seed`) |
| 4 | **Adopt `--market-filter` in `backtest_args`** | excess CAGR | +5.7 (US), +5.4 (India) CAGR points, v1.4 and v1.5, momentum and random | as measured | India drawdown −29 → −42%; slower re-entry after V-bottoms | 2 markets × 2 versions × 2 rankings; DD fragile | mechanics (already tested, adopt with 1–2) |
| 5 | **Pyramiding, 2 tranches** (`--pyramid 0.5 --pyramid-add-pct 2`) | avg R of winners, concentration in trends | Turtle rule; untested here; volatile signals carry the right tail | larger winners, same loser count at half size | adds need cash (cash-bound book); stop not raised to the add | untested | from the method (no code) |
| 6 | Volatility-aware ranking (ATR% rank) instead of 12-1 momentum, only if priority 3 shows ranking matters | avg R | ATR% quintile 5 vs 1: f60 +6.0 vs +0.3% (US), +7.3 vs +1.3% (India), n≈12k/1.3k each | fatter tail | deeper MAE; more stops | both markets, monotonic; untested in the book | parameter / existing `--rank-by vol_scaled` was worse (1410, 1421), so **contradicted in the book**, ranked last |
| 7 | Align the live exit (20-day) with the backtest (50-day) | live/backtest consistency | caveat in the strategy's own docs | the live screen trades what was tested | none | n/a | doc + code (`exit_channel`) |

What is **not** proposed: more entry filters. There is no signal-level edge to sharpen in the US.
Neither is another exit window: 20, 30 and 50 bars are already tried, and the result is a peak in
India and worse in the US.

---

## 2. `turtle_trend`: cross-asset Turtle breakouts on 13 ETFs

### 2.1 Runs reviewed

| Run | Market | Version | Stage | Overrides | Role |
|---|---|---|---|---|---|
| 1186 | US | 1.0 | optimise | none (System 2) | **baseline** |
| 3518 | US | 1.0 | optimise | `--system 1` | variant tested |
| 1187 | US | 1.0 | optimise | `--system both` | variant tested |

There is no India universe by design.

### 2.2 Scorecard (1186, System 2, base costs)

| Key parameter | Value | Benchmark (60/40 TR) |
|---|---|---|
| CAGR / excess | 1.38% / −9.46 | 10.84% |
| Max drawdown / longest | −34.8% / 1,028 sessions | −19.0% |
| Sharpe / Sortino / Calmar | 0.17 / 0.17 / 0.04 | 1.16 |
| Trades (per year) | 483 (54) | |
| Win rate / avg win / avg loss | 30.9% / +2.82R / −0.99R | |
| Avg R / profit factor | +0.19 / 1.08 | |
| Gross exposure (avg / max) | 163% / 231%; **306 entries skipped at the 200% gross cap** | |
| Turnover / costs | 14.2× / $11,861 | |
| Long / short P&L | +$17,622 / −$8,802 | |
| R by exit | STOP 262 trades, −1.09R, median 9 days; CHANNEL 217, +1.73R, median 63 days | |
| Cost ×0.5 / ×2 | CAGR +2.70% / −0.26% | |
| Correlation of monthly returns | SPY −0.09; 60/40 −0.03; momentum book −0.10 | |
| By year | 2014 +13.0%, 2020 +38.6%; the other 7 years sum to −30% | |

System 1 (3518) made −8.58% CAGR with a −68% drawdown. Both systems together (1187) made −3.46%.

### 2.3 Is the edge real?

- **Trials:** 3. DSR 0.41 (SR 0.17, expected max of 3 null trials 0.25). P(Sharpe > 60/40's) 0.00.
- **Selection vs timing** *(computed, 1,000 draws)*:

| Null | Mean of trade return | Trade (+0.38%) percentile |
|---|---|---|
| Random ETF, same direction and dates (selection) | +0.07% [−0.41, 0.54] | 85.7 |
| Same ETF and direction, same length, random dates (timing) | +0.36% [−0.17, 0.87] | **51.7** |

The breakout entries carry **no timing edge** on these 13 ETFs in 2013–2021, long or short. Shorts
beat a random ETF short (+0.36% vs −0.09%) but not random timing.
- **Signals vs traded:** 306 entries were skipped at the gross cap. Probe P4 below lifts the cap.
- **Concentration:** the top 5% of trades made 243% of net R. Two years (2014, 2020) carry it all.
  This is the shape the method predicts, but the base is too small.

### 2.4 The method: fidelity check and probes

| Rule | Turtle original | This code | Kind |
|---|---|---|---|
| Universe | About 20 futures: rates, currencies, metals, energy, softs, stock indices | 13 ETFs; 4 equity, 2 Treasury, few currencies (UUP only) | different (stand-ins, caveat) |
| Leverage | Futures margin | 200% gross, 50% per position: a Treasury position is often capped below its unit | different |
| Unit | 1% of equity per N | 1% to 2N (half a unit) | different threshold |
| Pyramiding | +1 unit per ½N, up to 4 | none | missing |
| System 1 filter | Skip a 20-day breakout after a winning one; 55-day failsafe | none | missing |
| Unit limits | 4 / 6 / 10 / 12 | 10% open-risk cap | different |
| Entry | Intraday touch | close, next open | simplified |
| Drawdown rule | Cut notional 20% per 10% drawdown | none | missing |
| Exits | 2N stop; 10/20-day opposite extreme | same, on the close, next open | same |

**Scratchpad probes** *(computed with `turtle_trend.run`, constants changed in memory, frames cut at
2021-12-31; 7 more trials)*:

| Probe | Trades | CAGR | Max DD | Sharpe | CAGR at 2× costs |
|---|---|---|---|---|---|
| P0 baseline (reproduces 1186) | 483 | 1.38% | −34.8% | 0.17 | −0.26% |
| P1 Turtle unit: 1% per N (`RISK_PCT=2`, open risk 20%) | 462 | −3.90% | −46.6% | −0.06 | −5.48% |
| P2 28 ETFs (+ IWM, 7 country ETFs, VNQ, SHY, TIP, LQD, HYG, EMB, CPER) | 809 | 2.87% | −25.6% | 0.24 | −0.53% |
| P3 28 ETFs at 0.5% risk | 933 | 1.76% | −31.2% | 0.19 | −1.20% |
| P4 13 ETFs, gross cap 300% | 516 | 3.08% | −39.2% | 0.25 | −0.81% |
| P5 28 ETFs, 0.5% risk, gross 300% | 1,045 | 0.34% | −38.6% | 0.13 | −4.14% |
| P6 System 1, 28 ETFs, 0.5% risk | 1,569 | −8.08% | −56.8% | −0.47 | −11.63% |

Yields for the added ETFs are flat assumptions, as in the strategy's own `ASSETS`. None of the
fidelity changes that can be tested without code gets near the strategy's own pass criterion
(Sharpe ≥ 0.3 and CAGR > 0 at 2× costs). Pyramiding and the System 1 filter need code and are
untested.

**Literature.** The documented record (Moskowitz, Ooi & Pedersen, 2012; Hurst, Ooi & Pedersen,
2017) is for futures. Those studies use volatility-scaled positions, 1-to-12-month return signals and
monthly rebalancing, not channel breakouts. Practitioner and index experience widely describes
2012–2019 as a weak stretch for managed-futures trend following. That is context, not tested here.

**Known choices.** The 13-ETF universe, ETF stand-ins, cost levels and the pre-registered criterion
(caveats, 2026-10-25) are deliberate. The run failed that criterion, and the result was reported.

### 2.5 Diagnosis

- The book is long equity in practice: equity longs made +$16.1k of the +$8.8k net.
- Metals shorts (−$6.5k) and currency trades (−$2.5k) lost money.
- The gross cap and the position cap shrink the bond and currency trends the method needs most.
- Costs are heavy: 14× turnover, and the result turns negative at 2× costs.

The sleeve test is judged against `momentum_baseline` **v1.0** (run 1165: −2.11% CAGR, −79.9%
drawdown). The current US momentum_baseline optimise run is v1.4 (run 2337: +4.27%, −75.4%).
Criterion (c) was therefore measured against a stale long book (shared fix F5).

### 2.6 Improvements, ranked

| Priority | Change | Parameter | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | **Stop refining the channel ETF book.** Keep v1.0 as the recorded failure | — | 3 runs + 7 probes, best Sharpe 0.25 | saves trials | none | the probes span universe, unit, leverage | decision |
| 2 | **Time-series momentum, the published form**: monthly, sign of 12-month excess return, each ETF sized to equal volatility, on the 28-ETF set (new `--system tsmom`) | Sharpe, correlation | Moskowitz, Ooi & Pedersen 2012; Hurst, Ooi & Pedersen 2017; **untested here** | a diversifier with lower turnover than breakouts | leverage needs (bond legs); an ETF borrow on shorts | untested; one pre-set trial | from the literature (code) |
| 3 | Sleeve test against the **current** momentum_baseline run | criterion (c) | the long book is v1.0 (1165) where v1.4 exists (2337) | a correct verdict | none | n/a | mechanics (code) |
| 4 | Pyramiding (4 units at ½N, stops raised) on System 2 | right tail | Turtle rule; untested | larger trend winners | more gross; the cap binds more | untested; P4 shows the gross cap already binds | from the method (code), ranked low |

---

## 3. `ma_trend`: Faber moving-average timing

### 3.1 Runs reviewed

| Run | Market | Version | Stage | Overrides | Role |
|---|---|---|---|---|---|
| 2335 | US | 2.4 | optimise | none (index mode, lookbacks 6/8/10/12) | **baseline** |
| 3826 | India | 2.4 | optimise | none | **baseline** |
| 3256 / 1331 | US / India | 2.2 | optimise | `--lookbacks 10` (Faber's single rule) | variant tested |
| 1254 / 1253 | US / India | 2.1 | optimise | none | identical to 2.4 in index mode |

v2.2–2.4 changed only stocks mode, so index-mode results are identical across 2.1–2.4. Stocks mode has
never been run on the optimise stage.

### 3.2 Scorecard

| Key parameter | US (2335) | India (3826) |
|---|---|---|
| CAGR / buy-and-hold TR | 11.71% / 16.08% | 12.71% / 14.46% |
| Excess CAGR (std costs) | −4.36 (−4.28) | −1.75 (−2.05) |
| Max drawdown / buy-and-hold | **−17.1% / −33.7%** | **−16.9% / −38.2%** |
| Longest drawdown | 440 sessions | 690 sessions |
| Sharpe / buy-and-hold | 0.97 / 0.99 (report: 0.95) | 1.12 / 0.91 |
| Sortino / Calmar | 0.84 / 0.68 | 0.91 / 0.75 |
| Volatility | 12.2% | 11.5% |
| Sleeve round trips (per year) | 25 (2.8) | 34 (3.8) |
| Win rate / avg trade return / PF | 60% / +12.2% / 5.5 | 32% / +5.4% / 2.2 |
| Exposure (days with ≥1 sleeve in) | 89.9% | 78.2% |
| Turnover / costs | 0.6× / $1,016 | 0.8× / ₹53k |
| Years beating buy-and-hold *(computed)* | 1 of 9 (2018) | 3 of 9 |

### 3.3 Is the edge real?

- **Trials:** 6 optimise runs. Two pairs are duplicates, so there are 4 distinct ones. The design was
  chosen on 1981–2026 and 2010–2026 data (changelog 2.0), which covers this window and the verify
  window. The real trial count is higher and unknown.
- **DSR** (Sharpe > 0) is 0.99 in both markets. That is trivial for an index-timing rule. The test
  that matters is the next one.
- **Timing null** *(computed, monthly approximation of the four-sleeve rule; cash at the stored cash
  rate)*:

| | US | India |
|---|---|---|
| Strategy (monthly approx) | CAGR 12.5%, Sharpe 1.18, max DD −12.4% | 13.0%, 1.11, −14.8% |
| Buy-and-hold TR | 16.4%, 1.21, −19.5% | 14.6%, 0.88, −29.1% |
| Percentile vs circular-shift null (107) / permutation null (2,000): Sharpe | 64 / 62 | 87 / 80 |
| Percentile: max drawdown (shallower) | **98 / 97** | 87 / 85 |
| Sharpe(strategy) − Sharpe(B&H), 6-month block bootstrap 90% CI | −0.03 [−0.31, +0.19], P(>0) 0.32 | +0.23 [−0.19, +0.65], P(>0) 0.79 |

- In the US, the drawdown control is real: about the 98th percentile against random timing with the
  same exposure. The return cost is too: about the 4th–9th CAGR percentile.
- In India, the Sharpe gain points the right way but is not significant over 108 months.
- **Concentration:** not applicable. The rule earns by being out during 2015–16, 2018 and March 2020.
  These are few events.

**Verdict.** This is exactly Faber's claim: about the same risk-adjusted return as the index with
roughly half the drawdown, and not more return. On that claim, the rule largely holds in both markets in this
window, though it narrowly misses one pre-set criterion in each (§5). The "No edge" badge measures something Faber never claimed. The real limits are the sample
(roughly 4 sell-offs in 9 years, none of them a slow bear market) and the trial count behind the
lookback set.

### 3.4 The method: fidelity check

Source: Mebane Faber, *A Quantitative Approach to Tactical Asset Allocation* (Journal of Wealth
Management, 2007; updated 2013).

| Rule | Faber | This code | Kind | Matters? |
|---|---|---|---|---|
| Portfolio | **5 asset classes equal-weighted** (US stocks, foreign stocks, 10y Treasuries, REITs, commodities), 20% each, each timed separately | One index (SPY / Nifty 500) | **missing** | **Yes**: the headline result (equity-like return, bond-like volatility) is a portfolio result |
| Signal | Monthly close vs the 10-month SMA of monthly closes | Same, but 4 sleeves at 6/8/10/12 months | different (known choice) | Tested: the single 10-month rule makes about the same CAGR with a deeper drawdown (US −20.8%, India −20.3%) |
| Out of market | T-bills | Cash rate | same | — |
| Returns | Total return | Total return (India: dividend estimate) | same / approximated | small |
| Execution | At the signal month's close | Same | same | — |
| Stocks mode | not Faber | the guide's 4 conditions, unranked | added | never run on optimise |

**GTAA probe** *(computed, monthly, stored ETF prices + flat yield assumptions, 10 bps costs,
2013–2021; 3 more trials)*:

| Portfolio | CAGR | Volatility | Sharpe | Max DD (monthly) |
|---|---|---|---|---|
| GTAA 5 (VTI, EFA, IEF, VNQ, DBC), 10-month | 5.62% | 5.7% | **0.99** | **−5.9%** |
| Equal-weight buy-and-hold, same 5 | 7.00% | 9.7% | 0.75 | −17.8% |
| GTAA 5, lookbacks 6/8/10/12 | 5.28% | 5.5% | 0.96 | −6.3% |
| 7 assets (+ GLD, TLT), 10-month | 4.55% | 4.8% | 0.95 | −6.5% |

The faithful portfolio reproduces Faber's shape: Sharpe +0.24 over its buy-and-hold, and a third of
the drawdown. Its absolute return is low because 2013–2021 punished commodities and foreign stocks.
That is a hypothesis to test properly, not a result: flat yields, monthly approximation.

**Literature.**
- Faber (2007/2013): the reduction in volatility and drawdown is the result. Return was close to
  buy-and-hold over a century, not above it.
- Zakamulin (*Market Timing with Moving Averages*, 2017) finds MA-timing gains concentrated in
  prolonged bear markets and sensitive to the test period.
- Clare, Seaton, Smith & Thomas (2016) find trend following improves risk-adjusted returns in
  multi-asset allocation.
- Known failure mode: whipsaw in sideways or V-shaped markets (2015–16, 2018, 2020 here).

### 3.5 Diagnosis

- Return trails because the window had no bear market long enough for a monthly rule to pay. The
  rule cost return in 7 of 9 US years.
- India's lower exposure (78%) reflects 2013, 2015–16 and 2018–19 weakness, and is where its Sharpe
  gain comes from.
- With 25–34 sleeve trades, no pattern in the trades is a finding (under 30 per market).

### 3.6 Improvements, ranked

| Priority | Change | Parameter | Evidence | Expected effect | Side effects | Robustness | Type |
|---|---|---|---|---|---|---|---|
| 1 | **Judge it on Faber's claim**: a pre-set criterion on Sharpe, Calmar and drawdown vs buy-and-hold, written into `caveats` / `status` | verdict | timing null: DD 98th pct (US); Sharpe ≈ B&H (US), +0.23 (India) | a verdict that tests the method | none | n/a | doc only (no behaviour change) |
| 2 | **GTAA mode** (`--mode gtaa`): the 5-asset portfolio, each timed by the existing rule, cash at the T-bill rate, ETF distributions credited | Sharpe, drawdown | scratchpad probe: Sharpe 0.99 vs 0.75, DD −5.9 vs −17.8% | Faber's actual result | lower absolute CAGR; ETF yields need a source (flat assumptions today) | US only (no India multi-asset ETFs stored); untested in the engine | from the method (code; new mode, version bump) |
| 3 | Run stocks mode once on the optimise stage | coverage | never run | tells whether the stock rule adds anything | — | — | mechanics (no code) |

---

## 4. The family's best version today

**`ma_trend` in index mode is the family's best version.** It is the only strategy whose result
matches its originator's documented claim:
- Sharpe about equal to the index in the US (0.97 vs 0.99) and above it in India (1.12 vs 0.91);
- maximum drawdown about half of buy-and-hold in both (−17.1% vs −33.7%, −16.9% vs −38.2%);
- the drawdown control beats random timing at the 97th–98th percentile (US).

It is a risk-control edge, not a return edge. The faithful five-asset GTAA is its natural next
version.

**For a return edge, the closest candidate is `donchian` in India with the market filter (2357).**
- It shows a genuine selection edge (98th percentile against random stocks over the same dates).
- But: DSR 0.91 at N=30, a deeper drawdown than the index (−41.8%), and all of its excess comes
  from 2021.
- It needs the mechanical fixes (minimum fill, entry at the breakout) and a measured noise band
  before it can be judged.

The US donchian book and turtle_trend show no edge of any kind.

## 5. Ranked improvement plan (family)

Pass criteria are fixed here, **before any run**. "Baseline" means the runs in §1.1–3.1. Every run is
optimise stage. Every new variant counts as a trial: there are 20 noise-band runs plus at most 10
candidate runs below.

| # | Change | Strategies | Type | Needs code? |
|---|---|---|---|---|
| 1 | F2: seeded random-ranking noise band | donchian (then every slot strategy) | mechanics | yes: `--rank-seed N` passed to `rerank_signals` (simulator CLI only; no strategy fingerprint moves) |
| 2 | F1: minimum fill fraction | donchian (shared simulator) | mechanics | yes: `--min-fill-frac` in `portfolio_sim` (default off, so other strategies are untouched); donchian's `backtest_args` gains it → bump to 1.6, `signal_version` pinned to 1.4 (post-scan only), changelog, `sizing_rules` text |
| 3 | D-entry: order expiry 1 session | donchian | from the method | yes: `ENTRY_EXPIRY_BDAYS` constant in `strategies/donchian.py` passed as `meta["expiry_bdays"]`, listed in `signal_exempt_consts` (as `earnings_gaps` does) → version bump, changelog, `entry_rules` with `{ENTRY_EXPIRY_BDAYS}` |
| 4 | Adopt `--market-filter` in donchian's `backtest_args` (with 2 + 3) | donchian | mechanics (tested) | yes: `backtest_args` → version bump by hand, `regime_note`, `status` |
| 5 | ma_trend's verdict on Faber's claim | ma_trend | doc | no behaviour change: `caveats` / `status` text |
| 6 | GTAA mode | ma_trend | from the method | yes: `ma_trend.py` new mode; ETF distribution yields as constants; version 2.5, changelog, `how_it_works`, `entry_rules` |
| 7 | Pyramiding, 2 tranches | donchian | from the method | no |
| 8 | TSMOM system | turtle_trend | from the literature | yes: `turtle_trend.py` `--system tsmom`, version 1.1 |
| 9 | Docs and consistency: stale `status`, live exit 20 vs 50, turtle's stale long book | donchian, turtle_trend | doc / code | doc; `exit_channel` (version bump); `find_long_book` (mechanics) |

### Pass criteria and commands

**1. Noise band** (no pass/fail; it sets the bar for 2–4 and 7). Run donchian with `--rank-by random`
and seeds 1–10, in both markets, on the candidate configuration (baseline flags plus
`--market-filter`). Record the 10th–90th percentile spread of CAGR, Sharpe and max drawdown.
- Rule fixed now: a later change "beats" another only if its gain exceeds the 80% seed spread (90th
  minus 10th percentile).
- After the code:
  `python -m jobs enqueue backtest --market us --strategies donchian --stage optimise --market-filter --bt '--rank-by random --rank-seed 1'`
  … through `--rank-seed 10`. Then the same with `--market india`.

**2 + 3 + 4. Donchian candidate (v1.6: minimum fill 0.5, entry expiry 1, market filter)**

Run each change alone first, then the combination:
```
python -m jobs enqueue backtest --market us    --strategies donchian --stage optimise --market-filter --bt '--min-fill-frac 0.5'
python -m jobs enqueue backtest --market india --strategies donchian --stage optimise --market-filter --bt '--min-fill-frac 0.5'
python -m jobs enqueue backtest --market us    --strategies donchian --stage optimise --market-filter --const ENTRY_EXPIRY_BDAYS=1
python -m jobs enqueue backtest --market india --strategies donchian --stage optimise --market-filter --const ENTRY_EXPIRY_BDAYS=1
# neighbours (plateau check), combination only: ENTRY_EXPIRY_BDAYS=2 and --min-fill-frac 0.33 / 0.75
python -m jobs enqueue backtest --market us    --strategies donchian --stage optimise   # after v1.6 ships both in backtest_args
python -m jobs enqueue backtest --market india --strategies donchian --stage optimise
```

The candidate passes only if **all** of these hold, in each market, against the `--market-filter`
runs (US 2356, India 2357):

| Criterion | US (vs 2356: 9.31%, −46.2%, Sharpe 0.51, +0.48R) | India (vs 2357: 17.23%, −41.8%, Sharpe 0.99, +1.21R) |
|---|---|---|
| Excess CAGR improves by more than the noise band, and is ≥ 0 at std costs | from −4.70 to ≥ −4.70 + band, **and** ≥ 0 for "edge" | ≥ +3.70 + band |
| Max drawdown no deeper than the benchmark's + 5 points | ≥ −39.1% | ≥ −43.3% |
| Avg R (closed trades) | ≥ +0.48 | ≥ +1.21 |
| Closed trades | ≥ 150 | ≥ 150 |
| Excess CAGR without the best year | ≥ −3 | ≥ −3 (2021 removed) |
| Neighbours (expiry 2; min fill 0.33 / 0.75) | same sign, each within half the gain | same |
| Random-entry null (same method as §1.3) | trades ≥ 90th percentile | ≥ 90th percentile |

If only India passes, India alone may go to verify (once, v1.6). The verify pass criterion is written
before that run: excess CAGR > 0 at std costs, max drawdown no deeper than the index's, and
≥ 60 closed trades.

**7. Pyramiding** (after the candidate passes or fails, on top of it):
`python -m jobs enqueue backtest --market india --strategies donchian --stage optimise --market-filter --pyramid 0.5 --bt '--pyramid-add-pct 2'`
(and `--market us`). It passes if the TREND_EXIT avg R rises by ≥ 0.5R, total CAGR rises by more than
the noise band, and max drawdown worsens by ≤ 3 points. Neighbours: `--pyramid-add-pct 1` and `3`.

**5–6. ma_trend.** Criterion fixed now, for index mode and GTAA mode alike, on the optimise stage:
- Sharpe ≥ buy-and-hold's − 0.05;
- Calmar ≥ 1.5 × buy-and-hold's;
- max drawdown ≤ 0.6 × buy-and-hold's;
- the timing-null drawdown percentile ≥ 90;
- unchanged at 2× costs (`--bt '--cost-bps 20'`).

Measured against these criteria, index mode does **not** pass everywhere, and that is reported
as-is (the criteria were not loosened to fit):
- US passes Sharpe (0.97 vs 0.99), drawdown ratio (0.51) and the timing null (98th percentile), but
  fails Calmar: 0.68 is 1.43 × buy-and-hold's 0.48, short of 1.5 ×.
- India passes Sharpe (1.12 vs 0.91), Calmar (0.75 is 1.98 × 0.38) and drawdown ratio (0.44), but
  fails the timing null (85th–87th percentile, short of 90).

Record both as in-sample near-misses. GTAA must meet the same
criteria against equal-weight buy-and-hold of its five assets.
- After the code:
  `python -m jobs enqueue backtest --market us --strategies ma_trend --stage optimise --bt '--mode gtaa'`
  plus the neighbour `--bt '--mode gtaa --lookbacks 10'`.
- Stocks mode, once:
  `python -m jobs enqueue backtest --market us --strategies ma_trend --stage optimise --bt '--mode stocks'`
  (and India).

**8. turtle_trend TSMOM.** The strategy's existing criterion applies unchanged, as one pre-set trial:
- (a) CAGR > 0 and Sharpe ≥ 0.3;
- (b) SPY correlation ≤ 0.3;
- (c) the 20% sleeve beats cash beside the *current* momentum book;
- (d) CAGR > 0 at 2× costs.

After the code:
`python -m jobs enqueue backtest --market us --strategies turtle_trend --stage optimise --bt '--system tsmom'`.
If it fails, retire turtle_trend as a standalone strategy and keep the run as the record.

## 6. Shared fixes

| ID | Fix | Where | Who benefits |
|---|---|---|---|
| F1 | Minimum fill: never fill a crumb that holds a slot | `backtesting/portfolio_sim.py` (opt-in flag) | donchian; every slot-limited strategy |
| F2 | A seed for random ranking, and a noise band before any ranking claim | `backtest.rerank_signals` / CLI | donchian; every slot-limited strategy |
| F3 | Judge trend following on its claim: risk-adjusted terms and drawdown, pre-registered | strategy `caveats` / `status` | all three |
| F4 | Name the window's regime gap: 2013–2021 has no prolonged bear market; read every trend verdict in this family as conditional on that | `status` texts | all three |
| F5 | Sleeve and comparison tests read the current version of the comparison book | `turtle_trend` (`find_long_book`) | turtle_trend; any sleeve test |
| F6 | Refresh `status` after a mechanics version | donchian (`status` quotes v1.4) | donchian |

## 7. Paper-trading gate

No paper book exists for any of the three strategies. `paper_orders` holds only `dual_momentum`,
`momentum_baseline` and `momentum_dual_combo` rebalances.

**`ma_trend` index mode, India and US** (the family's best version):

| Requirement | Level |
|---|---|
| Length | 24 month-end decisions per market |
| Rule fidelity | Every decision matches the backtest rule computed after the fact (0 mismatches); fills within 0.2% of the month-end close |
| Drawdown | Paper drawdown ≤ 0.6 × the index's over the same months, judged only if the index falls ≥ 10% at some point (otherwise the gate stays open) |
| Return | Sharpe ≥ the index's − 0.2 over the period; stated, not a pass condition on its own, because 24 months is a small sample |

**`donchian` India v1.6** (only if §5 passes, and before verify money is real):

| Requirement | Level |
|---|---|
| Closed trades | ≥ 60 (about 2½ years at 26 a year) |
| Avg R / profit factor | ≥ +0.4R / ≥ 1.3 |
| Win rate | 20–40% (outside it the trade shape has changed) |
| Fills | ≥ 90% on the session after the signal; slippage ≤ 2× the modelled 10 bps |
| Drawdown | no deeper than the Nifty 500's over the same period + 5 points |

## 8. What could not be determined

- **Whether any donchian ranking beats chance.** This needs the seed band (F2).
- **Whether the US breakout's missing signal edge is the market or the window.** 2013–2021 US
  small and mid caps lagged mega caps. A second window is out of bounds (verify), so only forward
  data settles it.
- **Pyramiding and the System 1 filter** need code and are untested in both books.
- **GTAA with real distributions.** Stored ETF prices exclude distributions. The probe used flat
  yields. A total-return ETF series would settle it.
- **ma_trend's true trial count.** The lookback set was chosen on 1981–2026 data. The number of sets
  tried is not recorded.
- **Bear-market behaviour.** None of the three strategies saw a slow bear market in the optimise
  window. That is the regime trend following is documented to be paid in.
