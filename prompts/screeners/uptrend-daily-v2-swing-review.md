# Uptrend Daily v2 — Swing Trade Screener Review

Scans every stock in the TradingView "Uptrend Daily v2" screener (US market),
applies quantitative trend/disqualifier/setup gates and watch-flag timing
checks computed entirely from price data, and returns a ranked decision
table of long swing-trade candidates for manual review, grouped by sector.
Data-only workflow — no chart screenshots or visual review; every number in
the output comes from the pulled OHLCV data.

- **Screener**: [Uptrend Daily v2](https://www.tradingview.com/screener/cnWiFFnI/)
  (deliberately loose: Price > 10, SMA200 < SMA50, ADX14 > 15,
  Price × Avg Vol 30D > 10M USD, ATR14 > 1.5%. Trend-quality checks
  (close > SMA50, SMA50/SMA200 rising, ADX > 25) moved into STEP 3 as hard
  gates or watch flags.)
- **Data source**: the TradingView chart's own history endpoint, called
  directly per symbol — no chart is rendered or screenshotted
- **Tooling**: Claude in Chrome, against a logged-in TradingView account
- **Style**: swing long, days to weeks holding period

> **Note:** this assumes the saved TradingView screener (cnWiFFnI) has
> itself been reconfigured to the looser filters below. I can't edit a
> saved TradingView screener from here — if it still filters at the old,
> tighter settings, loosen it to match before relying on this prompt.

## Prompt

```
ROLE
You are my swing-trading analyst. I trade long positions in US stocks,
holding for days to weeks. Use the Claude in Chrome tools on my TradingView
account. This is a data-only workflow — there is no chart screenshot or
visual review step; every number in the output comes from the pulled OHLCV
data.

GOAL
Find the best long setups among ALL stocks in my screener. Every stock that
passes the quantitative gates gets a full data-driven review; nothing is
dropped for ranking or sector reasons before that review.

LINKS

* Screener "Uptrend Daily v2": https://www.tradingview.com/screener/cnWiFFnI/
(filters: Price > 10, SMA200 < SMA50, ADX14 > 15,
Price × Avg Vol 30D > 10M USD, ATR14 > 1.5%)
The screener is deliberately loose: it only confirms that the long-term
structure is up. It no longer checks close > SMA50, SMA50 rising,
SMA200 rising or ADX > 25. Those checks are made in STEP 3 instead — as
hard gates (T) where the uptrend is broken, and as watch flags (X) where
only the timing is off. Expect a longer list than before.

ACCOUNT SETTINGS (used for position sizing)

* Account size: 10000 USD
* Risk per trade: 1% of account (100 USD). Halve it to 50 USD when VIX > 25.
* Max position size: 25% of account (2500 USD). If the sizing formula gives a
larger position, reduce the shares to fit and report the smaller risk.
* If the formula gives fewer than 1 share, mark the stock "Too large for account"
and treat it as WATCH — WAIT.
* Sector limit: at most 3 TRADE / TRADE ON TRIGGER names per sector (see STEP 6).

BROWSER RULES

* Use the TradingView tab I am looking at.
* Do not save any changes to the screener or to any chart you open while
discovering the data endpoint. Do not create alerts.
* Close cookie banners, notices and advert pop-ups if they block the
screener table.
* If a control described below does not exist, say so once and use the
closest equivalent.

DATA PULL (pace it so the feed doesn't stall)

* Get daily OHLCV bars from the data source the TradingView chart loads
(inspect the network requests on any TradingView chart page once to find
the endpoint, then call it directly for every symbol — no need to render
or screenshot a chart).
* Also pull bars for the sector index (see SECTOR INDEX MAP) of every
sector represented in the universe — once per sector, not once per stock.
* Pull with at most 4 requests in parallel, and retry a failed symbol at
most twice.
* Build weekly bars (week ending on the last trading day of the week) and
monthly bars (calendar month) by resampling the daily bars.
* Keep all pulled data in memory (or sessionStorage) for the rest of the run.
* If raw bars cannot be obtained for a stock, list it under "Not reviewed"
with the reason; if the endpoint fails entirely, stop and tell me.

DATA RULE

* At least 260 daily bars, plus weekly and monthly bars, for every stock.
* Work on completed bars. If the market is open, drop today's bar, and use the
last completed daily close as the current weekly and monthly close.

DEFINITIONS (use these exactly, so every run is reproducible)

* Swing low / swing high (daily): a bar whose low (high) is the lowest
(highest) of the 3 bars on each side. Weekly: 3 bars each side.
Monthly: 2 bars each side.
* Current swing high (H): the highest high of the last 20 daily bars.
* Impulse low (L): the lowest low in the 40 bars before H.
* Pullback low (P): the lowest low after H.
* Prior structural swing low: the last daily swing low before H.
* "Rising": SMA50 above its value 10 bars ago; SMA200 above its value
20 bars ago; weekly 30 EMA above last week's value.
* "Falling": SMA50 more than 1% below its value 10 bars ago; SMA200 more
than 0.5% below its value 20 bars ago.
* "Flat": neither rising nor falling.
* Percent distance from an SMA: (close ÷ SMA − 1) × 100. ATR% = ATR14 ÷
close × 100. "N ATR from an SMA" = (close − SMA) ÷ ATR14.
* 52-week high: the highest high of the last 252 daily bars.
* ADX: ADX 14 with Wilder smoothing. "ADX falling" = ADX below its value
5 bars ago.
* Base vs drift (used when the SMA50 is flat or ADX is 15–20):
Base = the 10-bar range is ≤ 4.5 ATR AND the close is within 10% of the
52-week high. Drift = anything else.
* Overhead levels: every daily swing high in the last 252 bars, weekly
swing high in the last 5 years, monthly swing high in all history, AND
the current swing high H. A level counts as "broken" only after a
completed daily close above it.
* Higher swing lows (T3): the last two confirmed daily swing lows within
the last 50 bars are rising. If there are fewer than two, the lowest low of
the last 25 bars must be above the lowest low of the 25 bars before that.
* Pullback on rising volume (D3): the average volume of the bars after H is
higher than the average volume of the impulse bars from L to H.
* Gap that has not held (D7): a gap up of more than 8% where a later close
fell below the close before the gap, or a gap down of more than 8% where
the current close is still below the close before the gap.
* RSI moving average: a 14-period SMA of RSI 14. ATR and RSI use Wilder
smoothing.

SECTOR INDEX MAP (SPDR Select Sector ETFs; each sector's context comes from
its own ETF's trend, not just the broad market)

* Communication Services — XLC
* Consumer Discretionary — XLY
* Consumer Staples — XLP
* Energy — XLE
* Financials — XLF
* Health Care — XLV
* Industrials — XLI
* Materials — XLB
* Real Estate — XLRE
* Technology — XLK
* Utilities — XLU
If a stock's sector doesn't map cleanly onto one of these, use the closest
ETF and say so.

STEP 1 — MARKET REGIME

* SPY, QQQ, IWM: daily close vs SMA50 and SMA200; is SMA50 rising (above
its value 10 bars ago)? Is the weekly close above a rising 30-week EMA?
* VIX: if above 25, use 50 USD risk and say so at the top.
* Breadth: % of screener names whose close is above their SMA20, and
separately % above their SMA50. (The screener no longer requires close >
SMA50, so the second number is now meaningful.)
* If SPY and QQQ are both below their SMA50, downgrade every decision by
one level (TRADE — HIGH CONFIDENCE → TRADE ON TRIGGER → WATCH — WAIT →
AVOID). Show each stock's decision before and after this rule.

STEP 2 — FREEZE THE UNIVERSE

* Read every row of the screener (scroll or use the TradingView scanner API).
The count must match the "Symbol N" header.
* Record the time the list was read and the header count. This frozen list is
the universe for the whole run; ignore any later intraday changes.
* If the screener table shows columns for ADX, RSI, % vs SMA20, % vs SMA50,
% from 52-week high, or 1-month/3-month performance, record them too, as a
cross-check only. Every gate and flag uses values computed from the
completed-bar data. If a screener value and your computed value disagree
noticeably (e.g. ADX by more than 3 points), note it.
* If you run this before the market opens, the list reflects the last close.
* For each stock collect: exchange, sector, next earnings date, and the bars
under DATA RULE. List any stock whose data fails to load.
* Sector: use the screener's sector tag, but correct it when it plainly
does not match the business, and note the correction.
* Sector regime: for each sector represented, compute its index's (see
SECTOR INDEX MAP) close vs SMA50/SMA200, whether SMA50 is rising, and its
3-month return minus SPY's. One summary line per sector; this is the group
header for the OUTPUT decision table and context for every stock in it.

STEP 3 — QUANTITATIVE GATES (every stock)

There are two kinds of check. HARD GATES (M, W, T, D) mean the uptrend is
broken or the stock is untradeable; a stock that fails one is AVOID and
leaves the funnel. WATCH FLAGS (X) mean the trend is intact but the timing
or quality is off; they never make a stock AVOID on their own, but they
cap the decision or change its ranking as stated.

Multi-timeframe (M / W) — hard gates:
M1 Monthly close above the 10-month SMA, and 12-month highs and lows above
the prior 12 months (n/a with under 24 months of history: pass, flag it)
W1 Weekly close above a rising 30-week EMA
W2 Weekly SMA20 above weekly SMA50

Trend (T) — hard gates:
T1 Structure: SMA50 > SMA200 (the screener guarantees this; re-check it on
completed bars), AND the close has not broken down through the SMA50.
Fail if the close is more than 2 ATR below the SMA50, or if the last 5
completed closes are all below the SMA50. (A close slightly below the
SMA50 is NOT a fail; see X2.)
T2 Slope: fail if the SMA50 is falling or the SMA200 is falling (see
DEFINITIONS). Flat passes but is flagged X4.
T3 Higher swing lows over the last ~50 bars (see DEFINITIONS)
T4 12-1 month momentum positive (close 21 bars ago vs close 252 bars ago)
T5 Leadership: the close is no more than 25% below the 52-week high.
T6 Trend not fading: fail if the 3-month (63-bar) return is negative AND
the SMA50 is flat or falling.

Note on the old T1 stack (close > SMA20 > SMA50 > SMA200): it is no longer a
gate. A close below the SMA20 is normal during a TC-01 pullback, and the
resumption signal in ENTRY RULES already requires a close back above the
SMA20 before any entry.

Relative strength (ranking only): 3-month and 6-month return minus SPY's,
and separately minus the stock's own sector index's (see SECTOR INDEX MAP).

Disqualifiers (D) — hard gates:
D1 (retired — extension is now watch flag X1, so an extended stock in a
good trend goes to WATCH — WAIT instead of AVOID)
D2 earnings within 10 trading days
D3 pullback on rising volume (see DEFINITIONS)
D4 close below the prior structural swing low
D5 any overhead level (see DEFINITIONS — this INCLUDES the current swing
high H) within 3% above the close, unless the close is already above it.
Exception: a stock with an active TC-01 or TC-02 setup is NOT disqualified
when the only level within 3% is H itself; instead, H becomes the
mandatory entry level under ENTRY RULES.
D6 ATR14 above 8% of price
D7 a gap of more than 8% in the last 10 bars that has not held (see DEFINITIONS)

Watch flags (X) — never AVOID on their own:
X1 Extended: close more than 2.5 ATR above the SMA20, or daily RSI above
75. Cap: WATCH — WAIT. Say what pullback would make it actionable (e.g.
"back toward the SMA20 at $___").
X2 Below the SMA50 (but within the T1 limits): the stock is testing its
SMA50. Cap: TRADE ON TRIGGER, and the trigger must also be above the
SMA50.
X3 At a rising SMA50: the close is within 1 ATR of the SMA50 (either side)
and the SMA50 is rising. Positive flag — often the best risk/reward. Rank
it up one step in setup quality. It still needs the resumption signal.
X4 Flat SMA50: read it as base or drift (see DEFINITIONS). Base: no cap; it
supports a TC-02 continuation. Drift: cap at TRADE ON TRIGGER and rank it
down one step in setup quality.
X5 Low ADX (15–20): read it as base or drift. Base: no effect. Drift: rank
it down one step in setup quality. Never a reason to reject — low ADX
inside a tight base is often the best setup.
X6 ADX falling: if the close is within 5% of H, it is a healthy pause (no
effect). If the close has fallen toward the SMA50 over the last 5 bars,
momentum is fading: rank it down one step.
X7 Late move: ADX above 40 together with X1. Prefer Plan A (pullback) over
Plan B (breakout), and say so.
X8 Weak momentum: daily RSI below 40 while the close is above the SMA50.
Cap: TRADE ON TRIGGER; check that the next pullback holds.
If several caps apply, use the lowest.

Setup gates:
TC-01 Trend Pullback: S-01 depth 30–60% of the impulse (H − L) or 1–3 ATR;
S-02 lasting 3–10 bars; S-03 low above the prior swing low;
S-04 volume contracting (pullback average volume below impulse average volume)
TC-02 Continuation Pattern: S-03 structure intact (10-bar range low above
the prior swing low); S-05 10-bar range ≤ 4.5 ATR and 5-day volume below
the 50-day average
TC-04 tag: within 2% of the 55-day or 52-week high
If both TC-01 and TC-02 are valid, TC-01 sets the stop and target.

Funnel: report counts after M/W, T, D, and setup, and how many of the
survivors carry each watch flag (X1–X8).

ENTRY RULES (apply before any sizing or decision)

* Resumption signal: a completed daily close above the prior bar's high AND
above the SMA20. For TC-02, a completed close above the high of the 10
bars before the signal bar.
* Trigger level: start from the high of the last completed bar (TC-02: the
higher of that and the prior 10-bar high). If X2 applies, the trigger is
also at least the SMA50 + 0.1%. Then, while any overhead level
(including H) lies within 3% above the ENTRY (trigger + 0.1%), move the
trigger up to the highest such level and check again. Stop when no
overhead level sits within 3% above the entry.
* Entry = buy stop at trigger level + 0.1% (at least 0.01 USD). Never place
an entry below an overhead level that sits within 3% above it.
* Two plans per stock — evaluate both and report the one that earns the
better decision (state which, and give the other in the Reason column):
Plan A "pullback": the entry from the rule above. Plan B "breakout":
entry = H + 0.1%, same stop. Use it when Plan A's target is capped at H
(or another level) below 2R. With X7, prefer Plan A.
* Stop = TC-01: pullback low P − 0.1 ATR; TC-02: 10-bar range low − 0.1 ATR.
* Target = measured move (TC-01: P + (H − L); TC-02: range high + 2 × range
height), cut to the next overhead level above the entry if that is lower.
* Compute risk %, R-multiple and shares from the FINAL entry, after any
move above H. Report the nearest overhead level above the entry ($ and %).
* "Signal present" for TRADE — HIGH CONFIDENCE means: the resumption signal
fired on the last completed bar AND no overhead level (including H) lies
within 3% above the close. The entry is then the buy stop above the signal
bar's high. A bounce that closed within 3% below H is not a fired signal;
it is TRADE ON TRIGGER at most.
* If the live (incomplete) bar has already traded through the trigger, say
so in the Reason column, but do not change the decision until a daily
close confirms it.

STEP 4 — DETAILED REVIEW (every setup-gate passer; data only)

* Review EVERY stock that passes the setup gate. There is no shortlist cap
and no sector cap at this step — a data-only review is cheap enough to
cover every qualifying stock in full.
* Timeframe alignment:
all three up → no change; weekly up but monthly in a range → note it.

CANDLESTICK COMMENTARY (last 5 completed daily bars, plus the last weekly bar)
Five daily bars = one trading week: long enough to show how the pullback or
flag is ending, short enough to stay about the entry decision.

* Compute from the data for each of the 5 bars: body as % of range, close
location in the range (top / middle / bottom third), upper and lower wick
size vs body, any gap, and volume vs the 50-day average.
* Name a pattern only when its definition is met: doji (body ≤ 10% of
range), hammer / shooting star (wick ≥ 2× body, close in the top / bottom
third), bullish / bearish engulfing, inside bar, outside bar, NR7
(narrowest range of the last 7), 3-bar reversal, gap up / gap down.
* Interpret in context: where the pattern sits (at support, at the SMA20,
at the SMA50, under H, at a breakout level) and whether volume confirms it.
* Note the last completed weekly candle in one phrase (e.g. "weekly: inside
bar near high", "weekly: long upper wick at resistance").
* Keep it to 25 words or fewer in the table; read it off the data.

DEMAND / SUPPLY COMMENTARY
Compute from the daily data:

* Up/down volume ratio, 50 bars: total volume on up-close days ÷ total
volume on down-close days.
* Accumulation and distribution days, last 25 bars: accumulation = close up
≥ 0.2% on volume higher than the prior day; distribution = close down
≥ 0.2% on volume higher than the prior day.
* Pullback volume vs impulse volume (average per bar), and 5-day vs 50-day
average volume.
* Demand zone: the nearest support below the close — the pullback low, the
breakout level the stock came from, or an SMA20 / SMA50 cluster. Give the
price range.
* Supply zone: the nearest overhead level above the close (from
DEFINITIONS), plus any high-volume down bar in the last 60 bars whose
range is above the close. Give the price range and % distance.
* Verdict: score +1 each for U/D ≥ 1.2, acc > dist + 1, and pullback/impulse
volume < 0.8; score −1 each for U/D < 0.8, dist > acc + 1, and
pullback/impulse volume > 1.1. +2 or more = "Demand in control", −2 or less
= "Supply in control", otherwise "Balanced". Quote the two numbers that
most support it (e.g. "U/D 1.6, 6 acc vs 2 dist").
* Supply in control caps the decision at WATCH — WAIT.

STEP 5 — TRADE PLAN (every reviewed stock)
Strategy › setup, entry trigger (per ENTRY RULES), stop, risk %, target with
R-multiple, exit style (trailing or fixed), nearest overhead level above the
entry, days to earnings, and sizing:
shares = floor(risk USD ÷ (entry − stop)); if shares × entry > 2500, use
floor(2500 ÷ entry) and report the actual USD at risk; if shares < 1, mark
it "Too large for account" (WATCH — WAIT).

STEP 6 — DECISION, THEN SECTOR FILTER
Decision values:
TRADE — HIGH CONFIDENCE : all hard gates pass; no watch-flag cap applies
(X1, X2, X4-drift, X8); all timeframes aligned; signal present as defined
in ENTRY RULES; risk ≤ 7%; target ≥ 2R; no earnings within 15 trading days;
demand/supply not "Supply in control"
TRADE ON TRIGGER : hard gates pass, but the close is still below the
trigger level (including a bounce that closed under H), or a watch flag
caps it here (X2, X4-drift, X8); risk ≤ 8%; target ≥ 2R
WATCH — WAIT : trend fine, but extended (X1), stop > 8%, target < 2R after
moving the entry above resistance, supply in control, or too large
AVOID : fails a hard gate (M, W, T or D2–D7)
Apply the watch-flag caps first, then the market-regime downgrade from
STEP 1, if active.

Sector filter (applied only now):
Within each sector, rank the TRADE and TRADE ON TRIGGER names by setup
quality (after the X3–X6 adjustments), then R-multiple, then RS. Keep the
top 3. Mark the rest "WATCH — SECTOR LIMIT" and name the stronger stocks in
that sector that replaced them.

OUTPUT (publish as one report page)

1. Market regime in one line (index trend, breadth % above SMA20 and above
SMA50, VIX, risk per trade, whether the downgrade rule is active).
2. Universe line: screener count, time read, stocks with data.
3. Funnel counts, including how many survivors carry each watch flag.
4. Decision table for every reviewed stock, grouped by sector (strongest
sector index RS vs SPY first), each group opening with a one-line sector
summary (index trend, RS vs SPY); within each sector, sorted by decision
and then setup quality: Stock | Exchange | Sector | Price | Strategy ›
Setup | Monthly | Weekly | Daily setup | Gates (M/W/T/S/D) |
Watch flags (X) | RS vs SPY / Sector | RSI (D) | ADX (D) |
% vs SMA20 / SMA50 | % below 52-week high | Current swing high H (% above
close) | Entry trigger | Stop | Risk % | Target (R) | Nearest overhead
above entry | Shares | Position ($) | USD at risk | Earnings in |
Candles (last 5 D + last W) | Demand / Supply |
Decision (before and after regime rule) | Reason
5. Full-universe appendix: one row per screener stock, grouped by sector in
the same order as the decision table, with Stock | Sector | first failed
gate (or "passed") | watch flags | one-line reason.
6. "Not reviewed", with reasons.
7. CSV of the TRADE and TRADE ON TRIGGER rows: Ticker, Exchange, Strategy ›
Setup, Entry, Stop, Target, Risk per share, Shares, Position ($), Nearest
overhead level, Earnings date.
8. Combined risk and position value if every TRADE row is taken, and whether
it fits the 10000 USD account. If all TRADE ON TRIGGER rows fired too, say
which to prioritise so the total stays within the account.
9. A watchlist of WATCH — WAIT names whose only problem is a watch flag
(X1, X2, X4, X8), each with the specific trigger to wait for (e.g.
"pullback to SMA20 at $___", "close back above SMA50 at $___").
10. One line: technical analysis, not financial advice.

HOUSEKEEPING
Do not save any changes to the screener or to any chart you opened while
discovering the data endpoint. Leave the screener tab as the active tab
when you finish.
```
