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
* Pull all data BEFORE opening any chart, and keep the results in memory
(or save a summary) so that navigating to the chart page does not lose them.

INDICATORS (the same three on every timeframe)

* MA ribbon (SMA 20/50/100/200) on the price pane
* Volume, drawn at the bottom of the price pane
* RSI (14, close) with its moving average, in its own pane
Remove any duplicate or hidden copy of these. If the plan's indicator limit
blocks you, say so and continue with what's available.

CHART LAYOUT
Monthly: "All" range button, log scale ON (full history is acceptable).
Weekly: "5Y" range button (log scale OFF).
Daily: "1Y" range button (never more than 12 months).
Move the mouse off the chart before each screenshot so the legend shows
the latest values. Close any advert pop-ups.
Screenshots judge visual structure only; take every number from the data.

CHART READINESS (check before EVERY screenshot)

1. The symbol and interval in the header match the request.
2. Candles are drawn and the legend shows numbers (not "•••" or "∅") for the
MA ribbon, Volume and RSI, and all lines are drawn.
3. Wait up to 30 seconds. If it's still not ready, reload once. If it still
fails, list the stock under "Not reviewed" with the reason.

DATA RULE

* At least 260 daily bars, plus weekly and monthly bars, for every stock.
* Work on completed bars. If the market is open, drop today's bar, and use the
last completed daily close as the current weekly and monthly close.

STEP 1 — MARKET REGIME

* SPY, QQQ, IWM: close vs 50 and 200 SMA; is the 50 SMA rising? Check the
weekly and daily charts.
* VIX: if above 25, use 50 USD risk and say so at the top.
* Breadth: % of screener names above their 20 EMA.
* If SPY and QQQ are both below the 50 SMA, downgrade every decision by one level.

STEP 2 — FREEZE THE UNIVERSE

* Read every row of the screener (scroll or use the TradingView scanner API).
The count must match the "Symbol N" header.
* Record the time the list was read and the header count. This frozen list is
the universe for the whole run; ignore any later intraday changes.
* If you run this before the market opens, the list reflects the last close.
* For each stock collect: exchange, sector, next earnings date, and the bars
under DATA RULE. List any stock whose data fails to load.

STEP 3 — QUANTITATIVE GATES (every stock)

Multi-timeframe (M / W):
M1 Monthly close above the 10-month SMA, and 12-month highs and lows above
the prior 12 months
W1 Weekly close above a rising 30-week EMA
W2 Weekly SMA20 above weekly SMA50

Trend existence (T):
T1 close > EMA20 > SMA50 > SMA200
T2 SMA50 rising over the last 10 bars, and SMA200 rising
T3 higher swing lows over the last ~50 bars
T4 12-1 month momentum positive

Relative strength (ranking only): 3-month and 6-month return minus SPY's.

Disqualifiers (D):
D1 more than 2.5 ATR above EMA20
D2 earnings within 10 trading days
D3 pullback on rising volume
D4 close below the prior structural swing low
D5 a prior daily, weekly or monthly high within about 3% above
(unless price is breaking it)
D6 ATR14 above 8% of price
D7 a gap of more than 8% in the last 10 bars that has not held

Setup gates:
TC-01 Trend Pullback: S-01 depth 30–60% of the impulse or 1–3 ATR;
S-02 lasting 3–10 bars; S-03 low above the prior swing low;
S-04 volume contracting
TC-02 Continuation Pattern: S-03 structure intact; S-05 10-bar range
≤ 4.5 ATR and 5-day volume below the 50-day average
TC-04 tag: within 2% of the 55-day or 52-week high

Funnel: report counts after M/W, T, D, and setup.

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
all three up → no change; weekly up but monthly in a range → note it;
weekly fails W1 → cap at WATCH; monthly in a long-term downtrend → down one level.

STEP 5 — TRADE PLAN (every reviewed stock)
Strategy › setup, entry trigger, stop, risk %, target with R-multiple, exit
style (trailing or fixed), days to earnings, and sizing:
shares = floor(risk USD ÷ (entry − stop)); if shares × entry > 2500, use
floor(2500 ÷ entry) and report the actual USD at risk; if shares < 1, mark
it "Too large for account" (WATCH — WAIT).

STEP 6 — DECISION, THEN SECTOR FILTER
Decision values:
TRADE — HIGH CONFIDENCE : all gates pass; all timeframes aligned; resumption
signal present on a completed bar; risk ≤ 7%;
target ≥ 2R; no earnings within 15 days
TRADE ON TRIGGER : gates pass, but the entry signal hasn't fired yet
WATCH — WAIT : trend fine, but extended, stop > 8%, resistance
just overhead, weekly not confirmed, or too large
AVOID : fails a trend gate or a disqualifier

Sector filter (applied only now):
Within each sector, rank the TRADE and TRADE ON TRIGGER names by setup
quality, then R-multiple, then RS. Keep the top 3. Mark the rest
"WATCH — SECTOR LIMIT" and name the stronger stocks in that sector that
replaced them.

OUTPUT

1. Market regime in one line (index trend, breadth %, VIX, risk per trade).
2. Universe line: screener count, time read, stocks with data.
3. Funnel counts.
4. Decision table for every reviewed stock, sorted by decision and then setup
quality: Stock | Exchange | Sector | Price | Strategy › Setup | Monthly |
Weekly | Daily setup | Gates (M/W/T/S/D) | RS vs SPY | RSI (D) | Entry trigger |
Stop | Risk % | Target (R) | Shares | Position ($) | USD at risk |
Earnings in | Decision | Reason
5. Full-universe appendix: one row per screener stock with Stock | Sector |
first failed gate (or "passed") | one-line reason.
6. "Not reviewed" and "Passed gates, not chart-reviewed", with reasons.
7. CSV of the TRADE and TRADE ON TRIGGER rows: Ticker, Exchange, Strategy ›
Setup, Entry, Stop, Target, Risk per share, Shares, Position ($),
Earnings date.
8. Combined risk and position value if every TRADE row is taken, and whether
it fits the 10000 USD account. If all TRADE ON TRIGGER rows fired too, say
which to prioritise so the total stays within the account.
9. One line: technical analysis, not financial advice.

HOUSEKEEPING
Remove any extra indicator you added, keep MA ribbon, Volume and RSI, set the
interval to D, do not click Save, and return the tab to the screener.
```
