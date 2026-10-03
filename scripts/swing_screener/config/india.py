from .base import MarketConfig, ScreenerThresholds

# NOTE on index/sector symbols below: these are the common Yahoo Finance
# tickers for NSE indices (^NSEI = Nifty 50, ^NSEBANK = Nifty Bank, etc).
# Yahoo's coverage of NSE *sectoral* and midcap indices is inconsistent and
# has changed over time — verify each one resolves with
# `yfinance.Ticker(sym).history(period="5d")` before relying on it. Where a
# sector index doesn't resolve, regime.py logs a warning and skips that
# sector's regime line rather than failing the run. The Chartink OAPI
# endpoint used in prompts/screeners/t-trend-up-india-swing-review.md is a
# viable fallback for index data specifically if yfinance coverage proves
# too thin.

INDIA_CONFIG = MarketConfig(
    name="India",
    currency_symbol="₹",
    tz="Asia/Kolkata",
    account_size=1_000_000,
    risk_pct=0.01,
    risk_pct_high_vol=0.005,
    max_position_pct=0.25,
    vol_index_symbol="^INDIAVIX",
    vol_threshold=20,
    broad_index_symbols={
        "NIFTY50": "^NSEI",
        "NIFTY500": "^CRSLDX",  # verify — Yahoo's Nifty 500 coverage is spotty
        "NIFTYMIDCAP150": "NIFTY_MIDCAP_150.NS",  # verify
    },
    benchmark_symbol="NIFTY500",
    # SECTOR INDEX MAP — NSE sectoral indices. Same caveat as above: test
    # each symbol, these are best-effort guesses at Yahoo's naming.
    sector_index_map={
        "Auto": "^CNXAUTO",
        "Bank": "^NSEBANK",
        "Financial Services": "NIFTY_FIN_SERVICE.NS",
        "FMCG": "^CNXFMCG",
        "Healthcare": "NIFTY_HEALTHCARE.NS",
        "IT": "^CNXIT",
        "Media": "^CNXMEDIA",
        "Metal": "^CNXMETAL",
        "Pharma": "^CNXPHARMA",
        "PSU Bank": "^CNXPSUBANK",
        "Private Bank": "NIFTY_PVT_BANK.NS",
        "Realty": "^CNXREALTY",
    },
    screener=ScreenerThresholds(
        min_price=0,  # India uses a market-cap floor instead of a price floor
        min_dollar_volume=500_000_000,  # SMA20(volume*close) >= INR 50 crore
        adx_min=15.0,
        atr_pct_min=1.5,
    ),
    max_open_positions=10,
    commission_per_order=0.0,
    slippage_bps=10.0,
    tick_size=0.05,
)

# Market-cap floor (INR crore), applied in addition to ScreenerThresholds
# since it doesn't fit the US-shaped dataclass cleanly.
INDIA_MIN_MARKET_CAP_CR = 5_000
