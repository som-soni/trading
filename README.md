# Trading

Version control for trading-related tooling and prompts.

## Structure

- `prompts/` — LLM prompts used for trading workflows (chart analysis, screener reviews, etc.)
  - `screeners/` — prompts that scan a screener and produce a reviewed trade list
    - [`uptrend-daily-v2-swing-review.md`](prompts/screeners/uptrend-daily-v2-swing-review.md) — US market (TradingView, NASDAQ/NYSE)
    - [`t-trend-up-india-swing-review.md`](prompts/screeners/t-trend-up-india-swing-review.md) — India market (Chartink, NSE)
