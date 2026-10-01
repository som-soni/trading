# Uptrend Daily v2 — Swing Trade Screener Review

Scans every stock in the TradingView "Uptrend Daily v2" screener (US market),
applies quantitative trend/disqualifier/setup gates, does a visual chart
review on TradingView via Claude in Chrome, and returns a ranked decision
table of long swing-trade candidates for manual review.

- **Screener**: [Uptrend Daily v2](https://www.tradingview.com/screener/cnWiFFnI/)
  (Price > 10, SMA50 < Price, SMA200 < SMA50, ADX14 > 25,
  Price × Avg Vol 30D > 10M USD, ATR14 > 1.5%)
- **Chart layout**: https://www.tradingview.com/chart/1LVYn46a/?symbol=EXCHANGE%3ATICKER
- **Tooling**: Claude in Chrome, against a logged-in TradingView account
- **Style**: swing long, days to weeks holding period

## Prompt

```
ROLE
You are my swing-trading chart analyst. I trade long positions in US stocks,
holding for days to weeks. Use the Claude in Chrome tools on my TradingView account.

GOAL
Find the best long setups among ALL stocks in my screener. Every stock that
passes the quantitative gates gets a visual chart review; nothing is dropped
for ranking or sector reasons before the chart review.

LINKS

* Screener "Uptrend Daily v2": https://www.tradingview.com/screener/cnWiFFnI/
(filters: Price > 10, SMA50 < Price, SMA200 < SMA50, ADX14 > 25,
Price × Avg Vol 30D > 10M USD, ATR14 > 1.5%)
* My chart layout: https://www.tradingview.com/chart/1LVYn46a/?symbol=EXCHANGE%3ATICKER
Always take the exchange from the screener row.

ACCOUNT SETTINGS (used for position sizing)

* Account size: 10000 USD
* Risk per trade: 1% of account (100 USD). Halve it to 50 USD when VIX > 25.
* Max position size: 25% of account (2500 USD). If the sizing formula gives a
larger position, reduce the shares to fit and report the smaller risk.
* If the formula gives fewer than 1 share, mark the stock "Too large for account"
and treat it as WATCH — WAIT.
* Sector limit: at most 3 TRADE / TRADE ON TRIGGER names per sector (see STEP 6).

BROWSER RULES

* Charts only draw in a VISIBLE tab. Before any screenshot, check that
document.visibilityState is "visible". Use the tab I am looking at.
* Change the symbol with the chart's symbol box, not by reloading the page.
Reloading can be blocked by a "Leave site?" prompt when the layout has
unsaved changes.
* Leave the layout on Daily (D) when you finish. Do not click Save.
* When finished, navigate the tab back to the screener. If navigation is
blocked, say so and ask me to switch it.

DATA PULL (pace it so the chart feed doesn't stall)

* Pull bars with at most 4 requests in parallel, and retry a failed
symbol at most twice.
* Also pull bars for the sector index (see SECTOR INDEX MAP) of every
sector represented in the universe — once per sector, not once per stock.
* Pull all data BEFORE opening any chart, and keep the results in memory and
in sessionStorage, so that navigating to the chart page does not lose them.

INDICATORS (the same three on every timeframe)

* MA ribbon (SMA 20/50/100/200) on the price pane
* Volume, drawn at the bottom of the price pane
* RSI (14, close) with its moving average, in its own pane
Remove any duplicate or hidden copy of these. Do not add EMAs; the ribbon
uses SMAs only. If the plan's indicator limit blocks you, say so and
continue with what's available.

CHART LAYOUT
Monthly: full history, log scale ON. Press the All range button FIRST and
then pick the 1M interval, because All switches the interval to weekly. Turn
log on by right-clicking the price scale → Logarithmic.
Weekly: interval 1W, then the 5Y range button (about 5 years), log scale OFF
(right-click the price scale → Regular). If 5Y is not offered, the stock is
a recent listing; use All.
Daily: interval 1D, then the 1Y range button (about 12 months, never more).
Move the mouse onto the right-hand toolbar before each screenshot so the
legend shows the latest values. Close any advert pop-ups.
Screenshots judge visual structure only; take every number from the data.
The live (incomplete) bar may show at the right edge; ignore it for
analysis. A "∅" on a long MA because the stock's history is too short is
acceptable; say so in the notes. Save every screenshot to disk for the report.

CHART READINESS (check before EVERY screenshot)

1. The symbol and interval in the header match the request.
2. Candles are drawn and the legend shows numbers (not "•••" or "∅") for the
MA ribbon, Volume and RSI, and all lines are drawn (short-history ∅ excepted).
3. Wait up to 30 seconds. If it's still not ready, reload once. If it still
fails, list the stock under "Not reviewed" with the reason.

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

STEP 1 — MARKET REGIME (from data only; no index screenshots)

* SPY, QQQ, IWM: daily close vs SMA50 and SMA200; is SMA50 rising (above
its value 10 bars ago)? Is the weekly close above a rising 30-week EMA?
* VIX: if above 25, use 50 USD risk and say so at the top.
* Breadth: % of screener names whose close is above their SMA20.
* If SPY and QQQ are both below their SMA50, downgrade every decision by
one level (TRADE — HIGH CONFIDENCE → TRADE ON TRIGGER → WATCH — WAIT →
AVOID). Show each stock's decision before and after this rule.

STEP 2 — FREEZE THE UNIVERSE

* Read every row of the screener (scroll or use the TradingView scanner API).
The count must match the "Symbol N" header.
* Record the time the list was read and the header count. This frozen list is
the universe for the whole run; ignore any later intraday changes.
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

Multi-timeframe (M / W) — hard gates; a stock that fails one leaves the funnel:
M1 Monthly close above the 10-month SMA, and 12-month highs and lows above
the prior 12 months (n/a with under 24 months of history: pass, flag it)
W1 Weekly close above a rising 30-week EMA
W2 Weekly SMA20 above weekly SMA50

Trend existence (T):
T1 close > SMA20 > SMA50 > SMA200
T2 SMA50 rising over the last 10 bars, and SMA200 rising
T3 higher swing lows over the last ~50 bars (see DEFINITIONS)
T4 12-1 month momentum positive (close 21 bars ago vs close 252 bars ago)

Relative strength (ranking only): 3-month and 6-month return minus SPY's,
and separately minus the stock's own sector index's (see SECTOR INDEX MAP).

Disqualifiers (D):
D1 more than 2.5 ATR above SMA20
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

Setup gates:
TC-01 Trend Pullback: S-01 depth 30–60% of the impulse (H − L) or 1–3 ATR;
S-02 lasting 3–10 bars; S-03 low above the prior swing low;
S-04 volume contracting (pullback average volume below impulse average volume)
TC-02 Continuation Pattern: S-03 structure intact (10-bar range low above
the prior swing low); S-05 10-bar range ≤ 4.5 ATR and 5-day volume below
the 50-day average
TC-04 tag: within 2% of the 55-day or 52-week high
If both TC-01 and TC-02 are valid, TC-01 sets the stop and target.

Funnel: report counts after M/W, T, D, and setup.

ENTRY RULES (apply before any sizing or decision)

* Resumption signal: a completed daily close above the prior bar's high AND
above the SMA20. For TC-02, a completed close above the high of the 10
bars before the signal bar.
* Trigger level: start from the high of the last completed bar (TC-02: the
higher of that and the prior 10-bar high). Then, while any overhead level
(including H) lies within 3% above the ENTRY (trigger + 0.1%), move the
trigger up to the highest such level and check again. Stop when no
overhead level sits within 3% above the entry.
* Entry = buy stop at trigger level + 0.1% (at least 0.01 USD). Never place
an entry below an overhead level that sits within 3% above it.
* Two plans per stock — evaluate both and report the one that earns the
better decision (state which, and give the other in the Reason column):
Plan A "pullback": the entry from the rule above. Plan B "breakout":
entry = H + 0.1%, same stop. Use it when Plan A's target is capped at H
(or another level) below 2R.
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

STEP 4 — VISUAL REVIEW OF EVERY SETUP

* Review EVERY stock that passes the setup gate. There is no shortlist cap and
no sector cap at this step.
* Order: best setup quality first, then relative strength, so that if the chart
feed fails partway through, the strongest names have already been reviewed.
* If more than 30 stocks pass, review the top 30 and list the rest under
"Passed gates, not chart-reviewed".
* For each stock: monthly (long-term trend, overhead supply), weekly (trend,
old highs, RSI holding above ~40 on pullbacks), daily (pattern clean?
resumption signal present? volume and RSI supporting? earnings marker).
* Timeframe alignment:
all three up → no change; weekly up but monthly in a range → note it.
* Reconciliation check (daily chart), answer each explicitly:
1. Is the entry below any visible high within 3%? If yes, the plan is wrong —
move the trigger above it and recompute. If a high seen on the chart is
missing from the data's overhead levels, add it, re-test D5 and recompute.
A stock that fails D5 at this stage is AVOID.
2. Does the chart agree with the data-derived entry, stop and target (e.g.
is the stop really below the pullback low; is the target below obvious
supply)? If not, fix the plan or explain the difference.
3. Do the candlestick and demand/supply readings below agree with what the
chart shows?

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
under H, at a breakout level) and whether volume confirms it.
* Note the last completed weekly candle in one phrase (e.g. "weekly: inside
bar near high", "weekly: long upper wick at resistance").
* Keep it to 25 words or fewer in the table; read it off the data and
confirm it on the screenshot.

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
TRADE — HIGH CONFIDENCE : all gates pass; all timeframes aligned; signal
present as defined in ENTRY RULES; risk ≤ 7%; target ≥ 2R; no earnings
within 15 trading days; demand/supply not "Supply in control"
TRADE ON TRIGGER : gates pass, but the close is still below the trigger
level (including a bounce that closed under H); risk ≤ 8%; target ≥ 2R
WATCH — WAIT : trend fine, but extended, stop > 8%, target < 2R after
moving the entry above resistance, supply in control, or too large
AVOID : fails a trend gate or a disqualifier
Then apply the market-regime downgrade from STEP 1, if active.

Sector filter (applied only now):
Within each sector, rank the TRADE and TRADE ON TRIGGER names by setup
quality, then R-multiple, then RS. Keep the top 3. Mark the rest
"WATCH — SECTOR LIMIT" and name the stronger stocks in that sector that
replaced them.

OUTPUT (publish as one report page)

1. Market regime in one line (index trend, breadth %, VIX, risk per trade,
whether the downgrade rule is active).
2. Universe line: screener count, time read, stocks with data.
3. Funnel counts.
4. Decision table for every reviewed stock, grouped by sector (strongest
sector index RS vs SPY first), each group opening with a one-line sector
summary (index trend, RS vs SPY); within each sector, sorted by decision
and then setup quality: Stock | Exchange | Sector | Price | Strategy ›
Setup | Monthly | Weekly | Daily setup | Gates (M/W/T/S/D) | RS vs SPY /
Sector | RSI (D) | Current swing high H (% above close) | Entry trigger |
Stop | Risk % | Target (R) | Nearest overhead above entry | Shares |
Position ($) | USD at risk | Earnings in | Candles (last 5 D + last W) |
Demand / Supply | Decision (before and after regime rule) | Reason
5. Chart review per stock: the saved monthly, weekly and daily screenshots,
with the plan numbers and the three reconciliation answers beside them.
6. Full-universe appendix: one row per screener stock, grouped by sector in
the same order as the decision table, with Stock | Sector | first failed
gate (or "passed") | one-line reason.
7. "Not reviewed" and "Passed gates, not chart-reviewed", with reasons.
8. CSV of the TRADE and TRADE ON TRIGGER rows: Ticker, Exchange, Strategy ›
Setup, Entry, Stop, Target, Risk per share, Shares, Position ($), Nearest
overhead level, Earnings date.
9. Combined risk and position value if every TRADE row is taken, and whether
it fits the 10000 USD account. If all TRADE ON TRIGGER rows fired too, say
which to prioritise so the total stays within the account.
10. One line: technical analysis, not financial advice.

HOUSEKEEPING
Remove any extra indicator you added, keep MA ribbon, Volume and RSI, set the
interval to D and the price scale back to Regular. Do not click Save; if a
"save changes?" or "leave page?" prompt appears, choose not to save. Then
navigate the tab back to the screener. If navigation is blocked, say so and
ask me to switch it.
```
