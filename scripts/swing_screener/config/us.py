from .base import MarketConfig, ScreenerThresholds

US_CONFIG = MarketConfig(
    name="US",
    currency_symbol="$",
    tz="America/New_York",
    account_size=10_000,
    risk_pct=0.01,
    risk_pct_high_vol=0.005,
    max_position_pct=0.25,
    vol_index_symbol="^VIX",
    vol_threshold=25,
    broad_index_symbols={"SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM"},
    benchmark_symbol="SPY",
    # SECTOR INDEX MAP — SPDR Select Sector ETFs (see
    # prompts/screeners/uptrend-daily-v2-swing-review.md)
    sector_index_map={
        "Communication Services": "XLC",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Financials": "XLF",
        "Health Care": "XLV",
        "Industrials": "XLI",
        "Materials": "XLB",
        "Real Estate": "XLRE",
        "Technology": "XLK",
        "Utilities": "XLU",
    },
    screener=ScreenerThresholds(
        min_price=10,
        min_dollar_volume=10_000_000,
        adx_min=15.0,
        atr_pct_min=1.5,
    ),
    max_open_positions=10,
    commission_per_order=0.0,
    slippage_bps=5.0,
    tick_size=0.01,
    # yfinance's .info['sector'] uses its own taxonomy, not GICS/SPDR names
    sector_alias_map={
        "Financial Services": "Financials",
        "Healthcare": "Health Care",
        "Consumer Cyclical": "Consumer Discretionary",
        "Consumer Defensive": "Consumer Staples",
        "Basic Materials": "Materials",
    },
)
