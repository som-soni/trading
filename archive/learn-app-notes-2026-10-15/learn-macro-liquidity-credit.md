# App notes moved out of learn-macro-liquidity-credit

## Intro — "Where this shows in the app" (verbatim)

**Where this shows in the app.** The US macro strip (the row of market tiles) on Markets → Breadth
(`scripts/swing_screener/marketdata/macro.py`) ends with **HY credit (HYG)**, a high-yield bond fund.
The tile shows the 1-day and 1-month change, a 3-month sparkline, and the hover line *"Credit risk
appetite: HYG falling while stocks rise is an early warning."* The VIX is not
on the strip. Instead, the same page's **"Options: expected vs actual?"** card compares the VIX
(India VIX for India) with how much the index has actually been moving. The
screener uses it too. When the VIX is above 25 (US) or India VIX is above 20,
the app's market-regime check flags the market as high-volatility, and position sizing halves risk per trade from 1%
to 0.5% (`core/regime.py`, `core/sizing.py`, each market's config).

## §2.2 heading
- "### 2.2 The US record (approximate; not stored in the app)"

## §3 The 2020 flood
- "That is the kind of divergence Markets → Breadth shows."

## §4.3 heading and first sentence
- "### 4.3 HYG — the series the app stores instead"
- "The app stores **HYG** (the iShares high-yield bond ETF) as a raw daily close since 2007."

## §5 The VIX — trader's read
- "A VIX holding above the threshold (25 for the US) is when the app halves risk."
- "India VIX ... Its highest stored value is 83.6, on 24 March 2020." (now "highest close")

## §6 Bank stress
- "The regional-bank ETF (KRE, not stored) fell much harder than XLF."

## §8 Practical habits
- "1. **Read the HYG tile weekly.** Compare its 1-month change with the index's. ..."
- "2. **For India** the app stores no credit gauge. Instead, watch the RBI's daily liquidity position, ..."

## §10 Checklist
- "[ ] HYG tile: 1-month change — falling while the S&P rises?"
