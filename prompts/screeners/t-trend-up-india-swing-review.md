# T — Trend Up (India) — Swing Trade Screener Review

Scans every stock in the Chartink "T — Trend Up (T-02, T-03, T-04)" screener
(NSE cash segment), applies quantitative trend/disqualifier/setup gates, does
a visual chart review on Chartink via Claude in Chrome, and returns a ranked
decision table of long swing-trade candidates for manual review.

- **Screener**: [T — Trend Up (T-02, T-03, T-04)](https://chartink.com/screener/t-trend-up-t-02-t-03-t-04)
  (cash segment: Close > SMA50, SMA50 > SMA200,
  SMA50 > (SMA50 20 days ago + ATR14), SMA200 > SMA200 20 days ago, ADX14 > 25,
  SMA20(Volume × Close) ≥ ₹50 crore, ATR14 > 1.5% of close,
  Market cap ≥ ₹5,000 crore — either Midcap ₹5,000–20,000 crore or
  Largecap ≥ ₹20,000 crore)
- **Chart**: https://chartink.com/stocks-new?symbol=TICKER
- **Tooling**: Claude in Chrome, against a logged-in Chartink account
- **Style**: swing long, NSE cash/delivery, days to weeks holding period

## Prompt

```
ROLE
You are my swing-trading chart analyst. I trade long positions in Indian stocks
(NSE cash segment, delivery), holding for days to weeks. Use the Claude in
Chrome tools on my Chartink account.

GOAL
Find the best long setups among ALL stocks in my screener. Every stock that
passes the quantitative gates gets a visual chart review; nothing is dropped
for ranking or sector reasons before the chart review.

LINKS

* Screener "T — Trend Up (T-02, T-03, T-04)":
https://chartink.com/screener/t-trend-up-t-02-t-03-t-04
(filters, cash segment: Close > SMA50, SMA50 > SMA200,
SMA50 > (SMA50 20 days ago + ATR14), SMA200 > SMA200 20 days ago, ADX14 > 25,
SMA20(Volume × Close) ≥ ₹50 crore, ATR14 > 1.5% of close,
Market cap ≥ ₹5,000 crore — either Midcap ₹5,000–20,000 crore or
Largecap ≥ ₹20,000 crore)
* Chart: https://chartink.com/stocks-new?symbol=TICKER
Use the NSE symbol exactly as shown in the screener's Symbol column.
URL-encode special characters (e.g. M&M → M%26M, BAJAJ-AUTO stays as is).

ACCOUNT SETTINGS (used for position sizing)

* Account size: ₹10,00,000
* Risk per trade: 1% of account (₹10,000). Halve it to ₹5,000 when India VIX > 20.
* Max position size: 25% of account (₹2,50,000). If the sizing formula gives a
larger position, reduce the shares to fit and report the smaller risk.
* If the formula gives fewer than 1 share, mark the stock "Too large for account"
and treat it as WATCH — WAIT.
* Sector limit: at most 3 TRADE / TRADE ON TRIGGER names per sector (see STEP 6).

BROWSER RULES

* Charts only draw in a VISIBLE tab. Before any screenshot, check that
document.visibilityState is "visible". Use the tab I am looking at.
* Change the symbol with the chart's symbol box (top-left of the Chartink
chart), not by reloading the page.
* Change the timeframe with the interval menu (Daily / Weekly / Monthly) next
to the chart-type button.
* Before you change anything, note which indicators my chart already shows
(e.g. EMA 50 and EMA 200). Restore exactly that set at the end.
* Do not save any template, layout or scan. Do not create alerts.
* Close the holiday/notice banner and any advert pop-ups if they cover the chart.
* When finished, navigate the tab back to the screener. If navigation is
blocked, say so and ask me to switch it.
* If a control described below does not exist on Chartink, say so once and use
the closest equivalent.

DATA PULL (pace it so the chart feed doesn't stall)

* Get daily OHLCV bars from the same data source the Chartink chart page
loads (inspect the chart page's network requests once to find it, then reuse
it for every symbol). Pull with at most 4 requests in parallel, and retry a
failed symbol at most twice.
* Build weekly bars (week ending on the last trading day of the week) and
monthly bars (calendar month) by resampling the daily bars.
* Pull all data BEFORE opening any chart, and keep the results in memory
(or save a summary) so that navigating to the chart page does not lose them.
* If raw bars cannot be obtained at all, stop and tell me before doing any
analysis from screenshots alone.

INDICATORS (the same three on every timeframe)

* Moving averages SMA 20/50/100/200 on the price pane
* Volume, drawn at the bottom of the price pane
* RSI (14, close) with its moving average, in its own pane
Remove any duplicate or hidden copy of these. Temporarily hide my existing
EMA 50/200 if they clutter the chart. If the plan's indicator limit
blocks you, say so and continue with what's available.

CHART LAYOUT
Monthly: zoom out to full history, log scale ON (full history is acceptable).
Weekly: about 5 years visible (log scale OFF).
Daily: about 12 months visible (never more than 12 months).
Move the mouse off the chart before each screenshot so the legend shows
the latest values.
Screenshots judge visual structure only; take every number from the data.
A missing ("n/a") long MA because the stock's listing history is too short
(common for recent IPOs) is acceptable; say so in the notes.

CHART READINESS (check before EVERY screenshot)

1. The symbol and interval in the header match the request.
2. Candles are drawn and the legend shows numbers (not "n/a") for the
MAs, Volume and RSI, and all lines are drawn.
3. Wait up to 30 seconds. If it's still not ready, reload once. If it still
fails, list the stock under "Not reviewed" with the reason.

DATA RULE

* At least 260 daily bars (about 2 years preferred, so the monthly and
12-month checks work), plus the resampled weekly and monthly bars, for
every stock. Flag recent listings that have less history.
* Work on completed bars. NSE trades 09:15–15:30 IST. If the run is during
market hours, drop today's bar, and use the last completed daily close as
the current weekly and monthly close.
* Chartink's free data is delayed. Record the "Delayed data as of …" time.
* Check the NSE trading-holiday calendar (and the Chartink banner) when
counting trading days.

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
swing high in the last 5 years, monthly swing high in all available history,
AND the current swing high H. A level counts as "broken" only after a
completed daily close above it.
* Tick size: round every entry UP and every stop DOWN to the NSE tick size
for that stock (₹0.05 unless the data shows a finer tick).

STEP 1 — MARKET REGIME

* NIFTY 50, NIFTY 500 and NIFTY MIDCAP 150: close vs 50 and 200 SMA; is the
50 SMA rising? Check the weekly and daily charts. (Find the index symbols
through the chart's symbol search.)
* India VIX: if above 20, use ₹5,000 risk and say so at the top.
* Breadth: % of screener names above their 20 EMA.
* If NIFTY 50 and NIFTY 500 are both below the 50 SMA, downgrade every
decision by one level.

STEP 2 — FREEZE THE UNIVERSE

* Click "Run Scan", set "Per Page" to the largest option and go through
every page. The count must match the "N stocks" total under the table.
* Record the time the list was read, the total count and the data time
shown. This frozen list is the universe for the whole run; ignore any
later intraday changes.
* If you run this before 09:15 IST or on a holiday, the list reflects the last
close.
* For each stock collect: exchange (NSE), sector / industry, market-cap band
(Mid / Large), next quarterly results / board-meeting date (from the NSE
corporate event calendar or the company's exchange announcements), any
NSE surveillance status (ASM / GSM / ESM, trade-for-trade "BE" series)
and price band, and the bars under DATA RULE. List any stock whose data
fails to load.
* If the results date cannot be found, write "Unknown". During results
season (roughly mid-Jan to mid-Feb, mid-Apr to end-May, mid-Jul to mid-Aug,
mid-Oct to mid-Nov), an "Unknown" date counts as within 15 trading days.

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

Relative strength (ranking only): 3-month and 6-month return minus
NIFTY 500's.

Disqualifiers (D):
D1 more than 2.5 ATR above EMA20
D2 quarterly results / board meeting within 10 trading days
D3 pullback on rising volume
D4 close below the prior structural swing low
D5 any overhead level (see DEFINITIONS — this INCLUDES the current swing
high H) within 3% above the close, unless the close is already above it.
Exception: a stock with an active TC-01 or TC-02 setup is NOT disqualified
when the only level within 3% is H itself; instead, H becomes the
mandatory entry level under ENTRY RULES.
D6 ATR14 above 8% of price
D7 a gap of more than 8% in the last 10 bars that has not held
D8 the stock is under ASM / GSM / ESM surveillance, trades in the
trade-for-trade (BE) series, or has a price band of 5% or less
D9 the last completed bar closed locked at its upper or lower circuit

Setup gates:
TC-01 Trend Pullback: S-01 depth 30–60% of the impulse (H − L) or 1–3 ATR;
S-02 lasting 3–10 bars; S-03 low above the prior swing low;
S-04 volume contracting
TC-02 Continuation Pattern: S-03 structure intact; S-05 10-bar range
≤ 4.5 ATR and 5-day volume below the 50-day average
TC-04 tag: within 2% of the 55-day or 52-week high

Funnel: report counts after M/W, T, D, and setup.

ENTRY RULES (apply before any sizing or decision)

* Resumption signal: a completed daily close above the prior bar's high AND
above the EMA20. For TC-02, a completed close above the 10-bar range high.
* Trigger level: start from the high of the last completed bar. Then, while
any overhead level (including H) lies within 3% above the ENTRY (trigger
+ 0.1%), move the trigger up to the highest such level and check again.
Stop when no overhead level sits within 3% above the entry.
* Entry = trigger level + 0.1% (at least one tick), rounded up to the tick.
Order type: a stop-limit (SL) buy, or a GTT trigger order for multi-day
validity, with the limit about 0.5% above the trigger. Never place an
entry below an overhead level that sits within 3% above it.
* Two plans per stock — evaluate both and report the one that earns the
better decision (state which, and give the other in the Reason column):
Plan A "pullback": the entry from the rule above. Plan B "breakout":
entry = H + 0.1%, same stop. Use it when Plan A's target is capped at H
(or another level) below 2R.
* Stop = TC-01: pullback low P − 0.1 ATR; TC-02: 10-bar range low − 0.1 ATR.
* Target = measured move (TC-01: P + (H − L); TC-02: range high + 2 × range
height), cut to the next overhead level above the entry if that is lower.
* Compute risk %, R-multiple and shares from the FINAL entry, after any
move above H. Report the nearest overhead level above the entry (₹ and %).
* Flag any plan whose risk per share is under 1.5% of price: delivery costs
(STT, exchange and stamp charges, about 0.2–0.3% round trip) take a large
share of 1R there.
* "Signal present" for TRADE — HIGH CONFIDENCE means: the resumption signal
fired on the last completed bar AND no overhead level (including H) lies
within 3% above the close. The entry is then the buy stop above the signal
bar's high. A bounce that closed within 3% below H is not a fired signal;
it is TRADE ON TRIGGER at most.

STEP 4 — VISUAL REVIEW OF EVERY SETUP

* Review EVERY stock that passes the setup gate. There is no shortlist cap and
no sector cap at this step.
* Order: best setup quality first, then relative strength, so that if the chart
feed fails partway through, the strongest names have already been reviewed.
* If more than 30 stocks pass, review the top 30 and list the rest under
"Passed gates, not chart-reviewed".
* For each stock: monthly (long-term trend, overhead supply), weekly (trend,
old highs, RSI holding above ~40 on pullbacks), daily (pattern clean?
resumption signal present? volume and RSI supporting? results date).
* Timeframe alignment:
all three up → no change; weekly up but monthly in a range → note it;
weekly fails W1 → cap at WATCH; monthly in a long-term downtrend → down one level.
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
* Interpret in context: where the pattern sits (at support, at the EMA20,
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
breakout level the stock came from, or an EMA20 / SMA50 cluster. Give the
price range.
* Supply zone: the nearest overhead level above the close (from
DEFINITIONS), plus any high-volume down bar in the last 60 bars whose
range is above the close. Give the price range and % distance.
* Verdict: "Demand in control", "Balanced" or "Supply in control", with the
two numbers that most support it (e.g. "U/D 1.6, 6 acc vs 2 dist").
* Supply in control caps the decision at WATCH — WAIT.

STEP 5 — TRADE PLAN (every reviewed stock)
Strategy › setup, entry trigger (per ENTRY RULES), order type (SL / GTT),
stop, risk %, target with R-multiple, exit style (trailing or fixed),
nearest overhead level above the entry, trading days to results, and sizing:
shares = floor(risk ₹ ÷ (entry − stop)); if shares × entry > ₹2,50,000, use
floor(2,50,000 ÷ entry) and report the actual ₹ at risk; if shares < 1, mark
it "Too large for account" (WATCH — WAIT).

STEP 6 — DECISION, THEN SECTOR FILTER
Decision values:
TRADE — HIGH CONFIDENCE : all gates pass; all timeframes aligned; signal
present as defined in ENTRY RULES; risk ≤ 7%; target ≥ 2R; no results
within 15 trading days; demand/supply not "Supply in control"
TRADE ON TRIGGER : gates pass, but the close is still below the trigger
level (including a bounce that closed under H)
WATCH — WAIT : trend fine, but extended, stop > 8%, target < 2R after
moving the entry above resistance, weekly not confirmed, supply in
control, or too large
AVOID : fails a trend gate or a disqualifier

Sector filter (applied only now):
Within each sector, rank the TRADE and TRADE ON TRIGGER names by setup
quality, then R-multiple, then RS. Keep the top 3. Mark the rest
"WATCH — SECTOR LIMIT" and name the stronger stocks in that sector that
replaced them.

OUTPUT

1. Market regime in one line (NIFTY 50 / 500 / Midcap 150 trend, breadth %,
India VIX, risk per trade).
2. Universe line: screener count, time read, data timestamp, stocks with data.
3. Funnel counts.
4. Decision table for every reviewed stock, sorted by decision and then setup
quality: Stock | Symbol | Sector | Mcap band | Price (₹) | Strategy › Setup |
Monthly | Weekly | Daily setup | Gates (M/W/T/S/D) | RS vs NIFTY 500 |
RSI (D) | Current swing high H (% above close) | Entry trigger | Order type |
Stop | Risk % | Target (R) | Nearest overhead above entry | Shares |
Position (₹) | ₹ at risk | Results in | Candles (last 5 D + last W) |
Demand / Supply | Decision | Reason
5. Full-universe appendix: one row per screener stock with Stock | Sector |
first failed gate (or "passed") | one-line reason.
6. "Not reviewed" and "Passed gates, not chart-reviewed", with reasons.
7. CSV of the TRADE and TRADE ON TRIGGER rows: Symbol, Exchange, Strategy ›
Setup, Entry, Stop, Target, Risk per share, Shares, Position (₹),
Nearest overhead level, Results date.
8. Combined risk and position value if every TRADE row is taken, and whether
it fits the ₹10,00,000 account. If all TRADE ON TRIGGER rows fired too, say
which to prioritise so the total stays within the account.
9. One line: technical analysis, not financial advice.

HOUSEKEEPING
Remove every indicator you added, restore the indicators my chart had at the
start (e.g. EMA 50 / EMA 200), set the interval to Daily, do not save any
template or layout, and return the tab to the screener.
```
