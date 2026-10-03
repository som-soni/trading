from dataclasses import dataclass, field


@dataclass
class ScreenerThresholds:
    """The loosened, structure-only screener filters (see STEP 3 'Note on the old
    T1 stack' in the prompts — timing/quality checks moved into the gate engine)."""

    min_price: float
    min_dollar_volume: float  # price * 30D avg volume, in account currency
    adx_min: float = 15.0
    atr_pct_min: float = 1.5  # ATR14 / close * 100


@dataclass
class MarketConfig:
    name: str
    currency_symbol: str
    tz: str

    # ACCOUNT SETTINGS
    account_size: float
    risk_pct: float
    risk_pct_high_vol: float
    max_position_pct: float
    vol_index_symbol: str
    vol_threshold: float

    # indices used for STEP 1 market regime; RS and breadth are measured
    # against benchmark_symbol
    broad_index_symbols: dict
    benchmark_symbol: str

    # SECTOR INDEX MAP: sector name -> ticker usable by the data provider
    sector_index_map: dict

    screener: ScreenerThresholds

    tick_size: float = 0.01
    min_history_days: int = 260
    sector_limit_per_sector: int = 3

    # universe source: "csv" expects data/universe_<market>.csv with
    # columns ticker,sector; override per market if a live source exists
    universe_source: str = "csv"

    # maps the data provider's own sector taxonomy (e.g. yfinance's
    # "Financial Services", "Healthcare") onto the keys used in
    # sector_index_map (GICS/SPDR-style names) — without this, sectors
    # silently fail to match their index and get skipped from regime/RS
    sector_alias_map: dict = field(default_factory=dict)

    @property
    def benchmark_ticker(self) -> str:
        """`benchmark_symbol` may be a LABEL (India uses 'NIFTY500') rather
        than something the data provider understands. Resolve it through
        `broad_index_symbols` so callers that just want to load prices get a
        real ticker. US happens to work either way because 'SPY' is both,
        which is why the India benchmark comparison was silently absent."""
        return self.broad_index_symbols.get(self.benchmark_symbol, self.benchmark_symbol)

    # ---- PORTFOLIO / EXECUTION (used by the portfolio backtest) ----
    # A per-symbol backtest implicitly assumes unlimited capital and no
    # costs. Both assumptions flatter results badly, so the portfolio
    # simulator needs them stated explicitly.
    max_open_positions: int = 10
    commission_per_order: float = 0.0   # per side, in account currency
    slippage_bps: float = 5.0           # per side, basis points of notional
