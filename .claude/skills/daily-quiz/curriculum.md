# Curriculum — what the quiz covers

Sixteen dimensions. "Learn" names the portal guides that cover part of a dimension
(`research/learn-<name>.md`); everything else comes from the wider literature. A dimension is never
limited to its Learn guides.

## 1. Market review and regime (live)
Reading today's market: index trend vs 50/200-day, breadth (advance/decline, % above averages, new
highs vs lows), volatility (VIX / India VIX, realised vs implied), distribution and follow-through days,
sector and group leadership, leaders' behaviour, macro strip, FII/DII flows (India). Regime calls,
conflicting signals, exposure by regime, what changes the call.
Learn: health-trend, health-breadth, health-volatility, health-distribution, strat-regime-filters.

## 2. Macro and intermarket
Central banks and policy rates, the yield curve and inversions, inflation (CPI/WPI, core), growth and
consumption data, currencies (USD/INR, DXY), commodities (oil, gold, copper), liquidity and credit
spreads, the economic calendar, how each moves equities and sectors, India-specific (RBI, monsoon,
budget, FPI flows), global spillovers.
Learn: macro-*.

## 3. Sectors, groups and rotation
Sector classification, the business cycle and sector rotation, group relative strength, theme cycles,
defensives vs cyclicals, rate-sensitive sectors, commodity-linked sectors, why leaders cluster in groups.
Learn: sectors-groups, strat-sector-rotation.

## 4. Fundamentals and valuation
Reading results (revenue, margins, EPS, guidance, surprises), quality (ROE, ROCE, cash conversion,
debt), growth (CANSLIM C and A, acceleration), valuation (P/E, PEG, EV/EBITDA, P/B, DCF intuition,
earnings yield vs bond yield), accounting red flags, corporate governance (India: promoter holding and
pledging, related-party deals), corporate actions (splits, bonuses, buybacks, demergers, dividends).
Learn: fund-*.

## 5. Price action and technical analysis
Stages (Weinstein), trend structure, volume analysis, relative strength, moving averages, indicators
and oscillators (RSI, MACD, ATR, Bollinger, ADX) and their failure modes, candlesticks, chart
patterns (cup with handle, flags, triangles, head and shoulders, double bottoms), bases and VCP,
support/resistance, supply/demand zones, gaps, multiple time frames. What the evidence says about each.
Learn: price-*, candlestick-patterns, chart-patterns, bases, vcp, support-resistance, supply-demand,
order-flow-smc.

## 6. Strategies — the wide catalog (see below)
How each works, its edge and why it might persist, when it fails, typical win rate and payoff shape,
holding period, what regime suits it, how to test it.

## 7. Risk: expectancy, sizing and drawdowns
R multiples, expectancy, payoff ratio and break-even win rate, fixed-fractional sizing, the position
cap, gaps, ATR sizing, drawdown and recovery maths, losing streaks, Kelly, risk of ruin, progressive
exposure, pyramiding.
Learn: risk-expectancy, risk-sizing.

## 8. Stops, exits and trade management
Initial stop placement (structural vs volatility), trailing stops (MA, chandelier, swing lows), profit
targets vs letting winners run, partial exits, time stops, breakeven stops, selling into strength vs
weakness, holding through earnings, re-entries.
Learn: risk-stops-exits.

## 9. Portfolio construction
Correlation and concentration, total open risk ("heat"), sector limits, number of positions, cash as a
position, combining strategies, rebalancing, asset allocation, index investing vs active, factor
investing (value, momentum, quality, low volatility, size), SIPs and long-term compounding.
Learn: risk-portfolio, strat-combining.

## 10. Execution and market structure
Order types (market, limit, stop, stop-limit, GTT, bracket, AMO), bid-ask, slippage, liquidity and
impact cost, pre-open and closing auctions, circuit limits and market-wide circuit breakers, T+1
settlement, margin and leverage, short selling (and India's restrictions), who trades (FII, DII,
retail, market makers, HFT), how indices are built and rebalanced, ETFs and their creation mechanism.

## 11. Derivatives (F&O)
Futures and basis, rollover, open interest, options payoffs, Black–Scholes intuition, Greeks, implied
vs historical volatility, the volatility smile and skew, option chain reading, PCR and max pain (and
their limits), spreads, straddles/strangles, iron condors, covered calls, protective puts, hedging a
portfolio, expiry dynamics, event trades, India F&O rules and SEBI's retail-loss studies, sizing
derivatives.
Learn: fno-*.

## 12. Testing, statistics and evidence
Backtesting pitfalls (look-ahead, survivorship, overfitting, data snooping, costs, unrealistic fills),
in-sample vs out-of-sample, walk-forward, sample size and standard error, Sharpe/Sortino/Calmar, max
drawdown, CAGR vs XIRR, deflated Sharpe and multiple testing, base rates, regression to the mean,
correlation vs causation, how to read a research paper's claims.
Learn: test-backtesting, system-filters.

## 13. Psychology, process and journaling
Cognitive biases (loss aversion, disposition effect, recency, confirmation, overconfidence, sunk cost,
hindsight), tilt and revenge trading, following rules through drawdowns, the trading plan, the
journal and the weekly review, process vs outcome, the routine (pre-market, post-market), when to stop
trading.
Learn: process-plan, process-journal, process-biases.

## 14. Tax, costs and regulation
India: STT, stamp duty, exchange and SEBI fees, GST, DP charges; STCG/LTCG on equity, F&O income as
business income, speculative intraday income, set-off and carry-forward of losses, advance tax, tax
audit thresholds; SEBI rules (insider trading, front-running, finfluencers, F&O eligibility, margin
pledge). US: short- vs long-term gains, wash sale, pattern-day-trader rule. Always check current figures
before asking.

## 15. Market history and case studies
Crashes and bubbles (1929, 1987, 2000, 2008, 2020; India 1992 Harshad Mehta, 2001 Ketan Parekh, 2008,
2020), famous trades and traders (Livermore, Soros 1992, Turtles, LTCM, Archegos), what each teaches
about leverage, liquidity, crowding and regime change. Long-run return facts (equity premium, how long
drawdowns lasted, the cost of missing the best days).

## 16. The business of trading
Benchmarking against just owning the index, opportunity cost, capital and time required, realistic
returns, scaling up, paper → small live → full size, when a method is "broken" vs in a normal drawdown,
keeping records, the cost of mistakes.

---

## Strategy catalog

Rotate through these. Mark nothing as "proven" because the portal has built it; the portal's own list
is in `scripts/swing_screener/strategies/` and only a subset of this.

**Trend following:** moving-average crossovers and filters (Faber 10-month), Donchian/Turtle channel
breakouts, time-series momentum (Moskowitz–Ooi–Pedersen), Supertrend, Weinstein stage analysis,
Livermore pivotal points, Dow theory, managed-futures/CTA style.

**Breakouts from a base:** CANSLIM (O'Neil), VCP/SEPA (Minervini), Darvas boxes, Kullamägi episodic
pivots and flags, Zanger, Morales–Kacher pocket pivots, high-tight flags, ascending bases, IPO bases.

**Pullbacks in a trend:** pullback to the 10/21/50-day, Fibonacci retracements, anchored VWAP, support
retests, Raschke's "Holy Grail", first pullback after a breakout.

**Momentum and rotation:** cross-sectional momentum (Jegadeesh–Titman), dual momentum (Antonacci),
volatility-scaled momentum, sector rotation, relative-strength leaders, 52-week-high momentum
(George–Hwang), industry momentum.

**Event-driven:** post-earnings-announcement drift, earnings gaps, index inclusion/exclusion,
buybacks, spin-offs and demergers, merger arbitrage, insider buying, analyst revisions, IPO lock-up
expiries, news and macro-event trades.

**Mean reversion:** RSI(2) (Connors), Bollinger reversion, short-term reversal, gap fills, failed
breakouts, oversold bounces in uptrends, pairs trading and cointegration, statistical arbitrage.

**Short side and bear markets:** stage-4 shorts, failed-breakout shorts, short squeezes, bear-market
rallies, hedging with index futures or puts.

**Intraday:** opening-range breakout, VWAP strategies, intraday momentum, market profile and
value-area trading, order-flow and tape reading, scalping (and why costs dominate it).

**Volatility and options:** covered calls and cash-secured puts, the volatility risk premium, iron
condors, calendar spreads, straddles into events, tail hedging, dispersion (concept).

**Factor and long-term:** value (Graham, Greenblatt magic formula), quality (Novy-Marx), low
volatility, size, dividend growth, buy-and-hold index, coffee-can and buy-quality-and-hold investing,
asset-allocation portfolios (60/40, all-weather, permanent portfolio).

**Seasonality and calendar:** turn-of-the-month, pre-holiday, sell-in-May, January effect, expiry-week
effects — and how many of these faded after publication.

**Discretionary schools (know them, judge the evidence):** Wyckoff, Elliott waves, Gann, ICT/smart
money concepts, harmonic patterns, Ichimoku.

For each strategy asked about, the questions should probe: the thesis (why should this work, who is on
the other side), the rules, the payoff shape, the regime it needs, the main way it fails, its costs and
capacity, and what the published evidence actually shows.
