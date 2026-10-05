"""Chart links for report rows.

A screener row that names a symbol but makes you retype it into a charting
site is doing half the job: every candidate here has to be looked at before
it is traded, and the look-up is the friction.

Everything provider-specific lives in this file. Point `CHART_URL` and
`EXCHANGE` somewhere else and every report follows — the pipeline CSV, the
markdown report and `find_pattern` all call `chart_url()` and nothing else.

Symbol mapping
--------------
The provider's symbol is not always the data provider's. yfinance suffixes
Indian tickers with the exchange (`RELIANCE.NS`), TradingView prefixes it
(`NSE:RELIANCE`). US tickers are passed bare: the universe CSV carries no
exchange, so there is nothing to prefix with, and TradingView resolves a bare
ticker on its own. That resolution is a guess on its part — a US ticker that
also exists on a foreign exchange may open the wrong listing. Add the
exchange to the universe file if that ever matters.
"""

from urllib.parse import quote

# {symbol} is filled with the provider's own symbol, already URL-encoded.
CHART_URL = "https://www.tradingview.com/chart/?symbol={symbol}"

# yfinance suffix -> the charting provider's exchange prefix
EXCHANGE = {
    ".NS": "NSE",
    ".BO": "BSE",
}


def provider_symbol(symbol: str) -> str:
    """`RELIANCE.NS` -> `NSE:RELIANCE`; `AAPL` -> `AAPL`."""
    if not symbol:
        return ""
    for suffix, exchange in EXCHANGE.items():
        if symbol.endswith(suffix):
            return f"{exchange}:{symbol[: -len(suffix)]}"
    return symbol


def chart_url(symbol: str) -> str:
    """A link straight to this symbol's chart, or "" if there is no symbol."""
    if not symbol:
        return ""
    return CHART_URL.format(symbol=quote(provider_symbol(symbol), safe=""))


def md_link(symbol: str) -> str:
    """The symbol as a markdown link, for the report. Falls back to plain
    text rather than rendering an empty link."""
    url = chart_url(symbol)
    return f"[{symbol}]({url})" if url else (symbol or "")
