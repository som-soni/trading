# App notes moved out of learn-macro-calendar

## Intro — "Where this shows in the app" (verbatim)

**Where this shows in the app.** The app tracks each stock's own earnings date:

- the **Chart** marks past results with an "E";
- its **News & events** panel lists what is coming;
- the setups table on **Strategies** has an *Earnings in (d)* column (days until results);
- **Markets → Post-market** lists earnings in the next 10
  days among watched and screened stocks.

Market-wide volatility is part of the app's market-regime check
(`scripts/swing_screener/core/regime.py`). When the VIX is above
25 (US) or India VIX is above 20, live position sizing halves the risk per
trade, from 1% to 0.5% of the account. Macro release dates themselves are not in
the app. Use the official calendars listed in Further reading.


## §6 The trader's rules — rule 5 (verbatim)

5. **Respect the market regime.** When the VIX is above 25 or India VIX above 20,
   the app already halves risk per trade. Take that as the cue to be
   pickier, too.

## §6 subsection (verbatim)

### What this app's strategies do with earnings

The strategies check how many days remain until a stock's next results. (Search
`scripts/swing_screener/strategies/` for `earnings_days_away` to see the code.) The rule comes
in two strengths: a hard gate rejects the setup, while a watch flag only marks it.

| Strategy | Earnings rule (live screening) |
|---|---|
| `trend_pullback` | Hard gate D2: no setup if earnings are 10 or fewer business days away; earnings within 15 days also block the HIGH CONFIDENCE label |
| `breakout` | Hard gate B7: no setup within 10 days; within 15 days blocks HIGH CONFIDENCE |
| `chart_pattern` | Hard gate P5: no setup within 10 trading days |
| `chart_pattern_spec` | Hard gate S3: no setup within `EARNINGS_DAYS` (10) trading days |
| `minervini` | Watch flag V5: earnings due within 10 days — flagged, not rejected |
| `minervini_spec` | Watch flag B4: earnings within `EARNINGS_WARN_DAYS` (10) days |
| `donchian` | No earnings rule |

Two caveats. First, if the earnings date is **unknown, the stock passes**. Second, the **backtests never
apply these rules**. The backtester (`backtesting/backtest.py`) has no record of which earnings dates
were known at each past date, so it passes none. Tested results therefore include trades held through
earnings. And none of the strategies looks at *macro* dates. Watching FOMC,
CPI, RBI and Budget days is your job.

## §8 A weekly prep routine — steps 2–3 (verbatim)

2. **List earnings dates for your positions and watchlist.** Use Post-market's
   *Earnings in the next 10 days*, or each chart's News & events panel.
3. **Decide in advance** what you will do around each: hold, trim, or make no new entries
   until after. Write it in the **Notes** journal.

## §9 What the evidence says (verbatim)

- **For this app:** the earnings gates apply only to live screening. The backtests cannot
  measure whether they help.

## §10 Checklist

- Is the VIX above 25 or India VIX above 20 — is sizing already halved?
