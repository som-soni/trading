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
    exchange="NSE", badge="NSE", flag="🇮🇳", symbol_suffix=".NS", fx_to_usd="USDINR",
    tz="Asia/Kolkata",
    account_size=2_000_000,
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
    # Sector proxies, each verified to return usable history — not assumed.
    #
    # Yahoo carries only three live Nifty sector INDICES (^NSEBANK, ^CNXIT,
    # ^CNXPHARMA, ~4,000 bars each); ^CNXAUTO, ^CNXFMCG, ^CNXMEDIA,
    # ^CNXMETAL, ^CNXPSUBANK, ^CNXREALTY and the NIFTY_*.NS forms all return
    # 0-1 bars however they are fetched. NSE-listed sector ETFs are ordinary
    # equities and do resolve, so they fill the gaps.
    #
    # Indices are preferred where they work (far longer history); ETFs are
    # the fallback. ETF proxies carry tracking error and start much later —
    # the oldest is 2019 — so sector history before then is unavailable for
    # those sectors, which matters for backtesting but not for a daily regime
    # read. Thinly traded ETFs were rejected in favour of liquid ones
    # (INFRABEES has 3,950 bars but only ~Rs 0.8cr/day, too noisy to use).
    sector_index_map={
        "Bank": "^NSEBANK",            # index, 4,013 bars
        "IT": "^CNXIT",                # index, 4,013 bars
        "Pharma": "^CNXPHARMA",        # index, 3,859 bars
        "PSU Bank": "PSUBNKBEES.NS",   # ETF, 4,380 bars, ~Rs 18cr/day
        "Private Bank": "PVTBANIETF.NS",  # ETF, 1,761 bars, ~Rs 8.9cr/day
        "Auto": "AUTOBEES.NS",         # ETF, 1,161 bars, ~Rs 6.6cr/day
        "FMCG": "FMCGIETF.NS",         # ETF, 1,269 bars, ~Rs 7.5cr/day
        "Metal": "METALIETF.NS",       # ETF,   532 bars, ~Rs 10cr/day
        "Infra": "INFRAIETF.NS",       # ETF,   562 bars, ~Rs 4cr/day
        "Energy": "OILIETF.NS",        # ETF,   519 bars, ~Rs 2.1cr/day
        "Consumption": "CONSUMBEES.NS",  # ETF, 2,919 bars, ~Rs 1.2cr/day
    },
    # yfinance reports its own sector taxonomy for NSE stocks ("Technology",
    # "Financial Services", "Healthcare"), which does not match the Nifty
    # names above. Without this the pipeline logged 68 "no sector index
    # mapped" warnings per run and produced no sector regime at all.
    # Real Estate, Communication Services and Utilities remain unmapped —
    # no proxy with usable history was found, and a wrong proxy is worse
    # than an honest gap.
    sector_alias_map={
        "Technology": "IT",
        "Financial Services": "Bank",
        "Healthcare": "Pharma",
        "Consumer Cyclical": "Auto",
        "Consumer Defensive": "FMCG",
        "Basic Materials": "Metal",
        "Industrials": "Infra",
        "Energy": "Energy",
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
