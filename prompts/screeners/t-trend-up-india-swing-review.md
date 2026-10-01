# T — Trend Up (India) — Swing Trade Screener Review

Scans every stock in the Chartink "T — Trend Up (T-02, T-03, T-04)" screener
(NSE cash segment), applies quantitative trend/disqualifier/setup gates, does
a visual chart review on TradingView via Claude in Chrome, and returns a
ranked decision table of long swing-trade candidates for manual review.
Chartink supplies the stock list and the price data; TradingView is used
only for the visual chart review.

- **Screener**: [T — Trend Up (T-02, T-03, T-04)](https://chartink.com/screener/t-trend-up-t-02-t-03-t-04)
  (cash segment: Close > SMA50, SMA50 > SMA200,
  SMA50 > (SMA50 20 days ago + ATR14), SMA200 > SMA200 20 days ago, ADX14 > 25,
  SMA20(Volume × Close) ≥ ₹50 crore, ATR14 > 1.5% of close,
  Market cap ≥ ₹5,000 crore — either Midcap ₹5,000–20,000 crore or
  Largecap ≥ ₹20,000 crore)
- **Data source**: Chartink OAPI (`https://chartink.com/oapi`) for OHLCV,
  market cap and sector
- **Chart (visual review only)**: https://www.tradingview.com/chart/1LVYn46a/?symbol=NSE%3ATICKER
- **Tooling**: Claude in Chrome, against a logged-in Chartink account and a
  logged-in TradingView account (same saved layout as the US prompt)
- **Style**: swing long, NSE cash/delivery, days to weeks holding period

## Prompt

```
ROLE
You are my swing-trading chart analyst. I trade long positions in Indian stocks
(NSE cash segment, delivery), holding for days to weeks. Use the Claude in
Chrome tools. Chartink supplies the stock list and the price data; TradingView
is used only for the visual chart review.

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
* Chart (visual review only): https://www.tradingview.com/chart/1LVYn46a/?symbol=NSE%3ATICKER
Use TradingView's NSE symbol. It usually matches the screener's Symbol
column, but TradingView writes "&" and "-" as "_" (BAJAJ-AUTO →
NSE:BAJAJ_AUTO, M&M → NSE:M_M). If a symbol does not load, find it with
TradingView's symbol search.
* Chartink is used only for the screener list and the OHLCV data. Do not
change anything on the Chartink chart page.

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
* Change the symbol with TradingView's symbol box (top-left), and the
timeframe with its interval menu next to the symbol box.
* Do not save any template, layout or scan. Do not create alerts.
* Close cookie banners, notices and advert pop-ups if they cover the chart.
* If a control described below does not exist, say so once and use the
closest equivalent.

DATA PULL (pace it so the feed doesn't stall)

* Get daily OHLCV from the endpoint the Chartink chart page uses: POST
https://chartink.com/oapi with query = "select open, high, low, close, volume
where symbol='X'", size = 5000, timeframe = Daily, limit = 1, use_live = 1,
widget_id = -1, end_time = -1, symbol = X, and the page's XSRF token in the
X-XSRF-TOKEN header. The response's groupData[0].results is a list with one
object per field (open, high, low, close, volume); join them before use. Bar
dates are in metaData[0].tradeTimes (IST midnight).
* Market-cap band and sector: the same endpoint with query = "select close,
market cap where symbol='X'" returns them in aggregatedStockList.
* Pull with at most 4 requests in parallel, and retry a failed symbol at
most twice.
* Also pull bars for the sector index (see SECTOR INDEX MAP) of every
sector represented in the universe — once per sector, not once per stock.
* Build weekly bars (week ending on the last trading day of the week) and
monthly bars (calendar month) by resampling the daily bars.
* Pull all data BEFORE opening any chart, and keep the results in memory and
in sessionStorage, so that navigating to TradingView does not lose them.
* If raw bars cannot be obtained at all, stop and tell me before doing any
analysis from screenshots alone.

INDICATORS (already saved in my TradingView layout; check them, don't add them)

* MA ribbon with SMA 20/50/100/200, Volume, and RSI 14 (close) with its
moving average.
* If any of these is missing or doubled, say so and carry on. Do not add
EMAs. My analysis uses SMAs only.

CHART LAYOUT (TradingView)
Monthly: full history, log scale ON. Press the All range button FIRST and
then pick the 1M interval, because All switches the interval to weekly. Turn
log on by right-clicking the price scale → Logarithmic.
Weekly: interval 1W, then the 5Y range button (about 5 years), log scale OFF
(right-click the price scale → Regular). If 5Y is not offered, the stock is
a recent listing; use All.
Daily: interval 1D, then the 1Y range button (about 12 months, never more).
Move the mouse onto the right-hand toolbar before each screenshot so the
legend shows the latest values. Screenshots judge visual structure only;
take every number from the data. The live (incomplete) bar may show at the
right edge; ignore it for analysis. A missing ("n/a") long MA because the
stock's listing history is too short (common for recent IPOs) is
acceptable; say so in the notes. Save every screenshot to disk for the report.

CHART READINESS (check before EVERY screenshot)

1. The symbol and interval in the header match the request.
2. Candles are drawn and the legend shows numbers (not "n/a") for the MAs,
Volume and RSI, and all lines are drawn (short-history n/a excepted).
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

SECTOR INDEX MAP (NSE sectoral indices, queried through the Chartink OAPI
like NIFTY500; each sector's context comes from its own index's trend, not
just the broad market)

* Auto — NIFTYAUTO
* Bank — NIFTYBANK
* Financial Services — NIFTYFINSERVICE
* FMCG — NIFTYFMCG
* Healthcare — NIFTYHEALTHCARE
* IT — NIFTYIT
* Media — NIFTYMEDIA
* Metal — NIFTYMETAL
* Oil & Gas — NIFTYOILGAS
* Pharma — NIFTYPHARMA
* PSU Bank — NIFTYPSUBANK
* Private Bank — NIFTYPVTBANK
* Realty — NIFTYREALTY
These symbols are the common Chartink/NSE naming convention and may not be
exact (the NIFTY500/CNX500 mismatch above is a known example of this). Test
each one before relying on it; if it returns no data, search Chartink for
the closest match and say so. If a stock's sector doesn't map cleanly onto
one of these, use the closest index and say so.

STEP 1 — MARKET REGIME (from data only; no index screenshots)

* Use these Chartink symbols: NIFTY, NIFTY500 (not CNX500, which returns no
data), NIFTYMIDCAP150 and INDIAVIX.
* For NIFTY 50, NIFTY 500 and NIFTY MIDCAP 150: daily close vs SMA50 and
SMA200; is SMA50 rising (above its value 10 bars ago)? Is the weekly close
above a rising 30-week EMA?
* India VIX: if above 20, use ₹5,000 risk and say so at the top.
* Breadth: % of screener names whose close is above their SMA20.
* If NIFTY 50 and NIFTY 500 are both below their SMA50, downgrade every
decision by one level (TRADE — HIGH CONFIDENCE → TRADE ON TRIGGER →
WATCH — WAIT → AVOID). Show each stock's decision before and after this rule.

STEP 2 — FREEZE THE UNIVERSE

* Click "Run Scan", set "Per Page" to 50 (the 500 option often won't
select) and go through every page. The count must match the "N stocks"
total under the table.
* Record the time the list was read, the total count and the data time
shown. This frozen list is the universe for the whole run; ignore any
later intraday changes.
* If you run this before 09:15 IST or on a holiday, the list reflects the last
close.
* For each stock collect: exchange (NSE), sector / industry, market-cap band
(Mid / Large), next quarterly results / board-meeting date, any NSE
surveillance status (ASM / GSM / ESM, trade-for-trade "BE" series) and price
band, and the bars under DATA RULE. List any stock whose data fails to load.
* Sources: results dates from
https://www.nseindia.com/api/event-calendar?index=equities (or the
company's exchange announcements); surveillance from
https://www.nseindia.com/api/reportASM and
https://www.nseindia.com/api/reportGSM. The NSE quote page is usually
blocked. If the price band cannot be read, treat a stock as having a band
wider than 5% when it closed more than 5% up or down in one day within the
last 120 sessions; say so.
* Sector: use Chartink's sector, but correct it when it plainly does not
match the business (e.g. a solar power producer tagged "Realty") and note
the correction.
* Sector regime: for each sector represented, compute its index's (see
SECTOR INDEX MAP) close vs SMA50/SMA200, whether SMA50 is rising, and its
3-month return minus NIFTY 500's. One summary line per sector; this is the
group header for the OUTPUT decision table and context for every stock in it.
* If the results date cannot be found, write "Unknown". During results
season (roughly mid-Jan to mid-Feb, mid-Apr to end-May, mid-Jul to mid-Aug,
mid-Oct to mid-Nov), an "Unknown" date counts as within 15 trading days. The
same applies when the 15-trading-day window reaches into results season,
even if today is just before it. Boards need only 2 working days' notice,
so recommend re-checking before entry.

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

Relative strength (ranking only): 3-month (63-bar) and 6-month (126-bar)
return minus NIFTY 500's, and separately minus the stock's own sector
index's (see SECTOR INDEX MAP).

Disqualifiers (D):
D1 more than 2.5 ATR above SMA20
D2 quarterly results / board meeting within 10 trading days
D3 pullback on rising volume (see DEFINITIONS)
D4 close below the prior structural swing low
D5 any overhead level (see DEFINITIONS — this INCLUDES the current swing
high H) within 3% above the close, unless the close is already above it.
Exception: a stock with an active TC-01 or TC-02 setup is NOT disqualified
when the only level within 3% is H itself; instead, H becomes the
mandatory entry level under ENTRY RULES.
D6 ATR14 above 8% of price
D7 a gap of more than 8% in the last 10 bars that has not held (see DEFINITIONS)
D8 the stock is under ASM / GSM / ESM surveillance, trades in the
trade-for-trade (BE) series, or has a price band of 5% or less
D9 the last completed bar closed locked at its upper or lower circuit

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
* If the live (incomplete) bar has already traded through the trigger, say
so in the Reason column, but do not change the decision until a daily
close confirms it.

STEP 4 — VISUAL REVIEW OF EVERY SETUP (TradingView)

* Review EVERY stock that passes the setup gate. There is no shortlist cap and
no sector cap at this step.
* Order: best setup quality first, then relative strength, so that if the chart
feed fails partway through, the strongest names have already been reviewed.
* If more than 30 stocks pass, review the top 30 and list the rest under
"Passed gates, not chart-reviewed".
* For each stock: monthly (long-term trend, overhead supply), weekly (trend,
old highs, RSI holding above ~40 on pullbacks), daily (pattern clean?
resumption signal present? volume and RSI supporting? results date).
* Timeframe alignment: all three up → no change; weekly up but monthly in
a range → note it.
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

1. Market regime in one line (NIFTY 50 / 500 / Midcap 150 trend, breadth %,
India VIX, risk per trade, whether the downgrade rule is active).
2. Universe line: screener count, time read, data timestamp, stocks with data.
3. Funnel counts.
4. Decision table for every reviewed stock, grouped by sector (strongest
sector index RS vs NIFTY 500 first), each group opening with a one-line
sector summary (index trend, RS vs NIFTY 500); within each sector, sorted
by decision and then setup quality: Stock | Symbol | Sector | Mcap band |
Price (₹) | Strategy › Setup | Monthly | Weekly | Daily setup |
Gates (M/W/T/S/D) | RS vs NIFTY 500 / Sector | RSI (D) | Current swing
high H (% above close) | Entry trigger | Order type | Stop | Risk % |
Target (R) | Nearest overhead above entry | Shares | Position (₹) |
₹ at risk | Results in | Candles (last 5 D + last W) | Demand / Supply |
Decision (before and after regime rule) | Reason
5. Chart review per stock: the saved monthly, weekly and daily screenshots,
with the plan numbers and the three reconciliation answers beside them.
6. Full-universe appendix: one row per screener stock, grouped by sector in
the same order as the decision table, with Stock | Sector | first failed
gate (or "passed") | one-line reason.
7. "Not reviewed" and "Passed gates, not chart-reviewed", with reasons.
8. CSV of the TRADE and TRADE ON TRIGGER rows: Symbol, Exchange, Strategy ›
Setup, Entry, Stop, Target, Risk per share, Shares, Position (₹), Nearest
overhead level, Results date.
9. Combined risk and position value if every TRADE row is taken, and whether
it fits the ₹10,00,000 account. If all TRADE ON TRIGGER rows fired too, say
which to prioritise so the total stays within the account.
10. One line: technical analysis, not financial advice.

HOUSEKEEPING
On TradingView, set the interval back to Daily and the price scale back to
Regular. Never save the layout; if a "save changes?" or "leave page?"
prompt appears, choose not to save. Then navigate the tab back to the
screener. If navigation is blocked, stop and ask me to switch the tab.
```
