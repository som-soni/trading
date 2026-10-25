"""Indices and ETFs tracked beside the stocks — prices only, never screened.

They go into `prices` like the benchmark and sector indices do (`universe.index_symbols`
adds them, so the daily `prices` refresh keeps their tail current and `backfill --max`
fetches their history), but they are NOT in the universe file. Breadth, screens,
strategies and backtests all draw their symbols from the universe, so nothing here
can leak into a stock count or a signal.

India's ETFs need no list: NSE's securities list already includes them, and the
`classify` job keeps them out of breadth. India's mutual funds and the US mutual
funds are NAVs, not traded bars, so they live in `marketdata/funds.py` instead.

Every ticker was checked against the data source when it was added; one that stops
returning data shows up as a failed symbol in the `prices` job's run log. Tickers prefixed
`NSE:` / `BSE:` are India indices Yahoo lacks, fetched from the index provider itself
(`official_indices.py`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    ticker: str
    name: str
    kind: str        # index | etf
    category: str


def _etfs(category: str, *pairs: tuple[str, str]) -> list[Instrument]:
    return [Instrument(t, n, "etf", category) for t, n in pairs]


def _indices(category: str, *pairs: tuple[str, str]) -> list[Instrument]:
    return [Instrument(t, n, "index", category) for t, n in pairs]


_US = [
    *_indices("US indices",
              ("^GSPC", "S&P 500"), ("^DJI", "Dow Jones Industrial Average"), ("^DJT", "Dow Jones Transportation"),
              ("^DJU", "Dow Jones Utilities"), ("^IXIC", "Nasdaq Composite"), ("^NDX", "Nasdaq 100"),
              ("^RUT", "Russell 2000"), ("^RUA", "Russell 3000"), ("^NYA", "NYSE Composite"),
              ("^MID", "S&P MidCap 400"), ("^SP600", "S&P SmallCap 600"), ("^SOX", "PHLX Semiconductor"),
              ("^VIX", "CBOE Volatility Index"), ("^VXN", "CBOE Nasdaq 100 Volatility")),
    *_etfs("Broad US market",
           ("SPY", "SPDR S&P 500"), ("IVV", "iShares Core S&P 500"), ("VOO", "Vanguard S&P 500"),
           ("SPYM", "SPDR Portfolio S&P 500"), ("RSP", "Invesco S&P 500 Equal Weight"), ("VTI", "Vanguard Total Stock Market"),
           ("ITOT", "iShares Core S&P Total US Stock Market"), ("SCHB", "Schwab US Broad Market"),
           ("DIA", "SPDR Dow Jones Industrial Average"), ("QQQ", "Invesco QQQ (Nasdaq 100)"),
           ("QQQM", "Invesco Nasdaq 100"), ("IWB", "iShares Russell 1000"), ("IWV", "iShares Russell 3000")),
    *_etfs("Size",
           ("IWM", "iShares Russell 2000"), ("MDY", "SPDR S&P MidCap 400"), ("IJH", "iShares Core S&P Mid-Cap"),
           ("IJR", "iShares Core S&P Small-Cap"), ("VO", "Vanguard Mid-Cap"), ("VB", "Vanguard Small-Cap"),
           ("VXF", "Vanguard Extended Market")),
    *_etfs("Style & factor",
           ("IWF", "iShares Russell 1000 Growth"), ("IWD", "iShares Russell 1000 Value"), ("VUG", "Vanguard Growth"),
           ("VTV", "Vanguard Value"), ("MTUM", "iShares MSCI USA Momentum"), ("QUAL", "iShares MSCI USA Quality"),
           ("USMV", "iShares MSCI USA Min Vol"), ("VLUE", "iShares MSCI USA Value"), ("SCHD", "Schwab US Dividend Equity"),
           ("VIG", "Vanguard Dividend Appreciation"), ("VYM", "Vanguard High Dividend Yield"),
           ("DGRO", "iShares Core Dividend Growth"), ("NOBL", "ProShares S&P 500 Dividend Aristocrats")),
    # The 11 Select Sector SPDRs are in the market config's sector map already.
    *_etfs("Industry",
           ("SMH", "VanEck Semiconductor"), ("SOXX", "iShares Semiconductor"), ("IGV", "iShares Expanded Tech-Software"),
           ("XBI", "SPDR S&P Biotech"), ("IBB", "iShares Biotechnology"), ("KRE", "SPDR S&P Regional Banking"),
           ("KBE", "SPDR S&P Bank"), ("XHB", "SPDR S&P Homebuilders"), ("ITB", "iShares US Home Construction"),
           ("XRT", "SPDR S&P Retail"), ("XME", "SPDR S&P Metals & Mining"), ("GDX", "VanEck Gold Miners"),
           ("GDXJ", "VanEck Junior Gold Miners"), ("XOP", "SPDR S&P Oil & Gas Exploration"), ("OIH", "VanEck Oil Services"),
           ("ITA", "iShares US Aerospace & Defense"), ("XAR", "SPDR S&P Aerospace & Defense"), ("JETS", "US Global Jets"),
           ("IYT", "iShares US Transportation"), ("VNQ", "Vanguard Real Estate"), ("PAVE", "Global X US Infrastructure")),
    *_etfs("Thematic",
           ("CIBR", "First Trust Nasdaq Cybersecurity"), ("HACK", "Amplify Cybersecurity"), ("BUG", "Global X Cybersecurity"),
           ("IHAK", "iShares Cybersecurity and Tech"), ("WCBR", "WisdomTree Cybersecurity"),
           ("BOTZ", "Global X Robotics & AI"), ("ROBO", "ROBO Global Robotics & Automation"), ("AIQ", "Global X AI & Technology"),
           ("SKYY", "First Trust Cloud Computing"), ("CLOU", "Global X Cloud Computing"), ("FINX", "Global X FinTech"),
           ("BLOK", "Amplify Transformational Data Sharing"), ("QTUM", "Defiance Quantum Computing"),
           ("DRIV", "Global X Autonomous & Electric Vehicles"), ("ESPO", "VanEck Video Gaming & eSports"),
           ("UFO", "Procure Space"), ("MAGS", "Roundhill Magnificent Seven"), ("ARKK", "ARK Innovation"),
           ("ARKG", "ARK Genomic Revolution"), ("TAN", "Invesco Solar"), ("ICLN", "iShares Global Clean Energy"),
           ("LIT", "Global X Lithium & Battery Tech"), ("URA", "Global X Uranium")),
    *_etfs("Crypto", ("IBIT", "iShares Bitcoin Trust"), ("FBTC", "Fidelity Wise Origin Bitcoin"), ("ETHA", "iShares Ethereum Trust")),
    *_etfs("International",
           ("ACWI", "iShares MSCI ACWI"), ("VT", "Vanguard Total World Stock"), ("VXUS", "Vanguard Total International Stock"),
           ("EFA", "iShares MSCI EAFE"), ("VEA", "Vanguard FTSE Developed Markets"), ("IEFA", "iShares Core MSCI EAFE"),
           ("EEM", "iShares MSCI Emerging Markets"), ("VWO", "Vanguard FTSE Emerging Markets"),
           ("IEMG", "iShares Core MSCI Emerging Markets"), ("VGK", "Vanguard FTSE Europe"), ("EWJ", "iShares MSCI Japan"),
           ("FXI", "iShares China Large-Cap"), ("MCHI", "iShares MSCI China"), ("KWEB", "KraneShares CSI China Internet"),
           ("INDA", "iShares MSCI India"), ("EPI", "WisdomTree India Earnings"), ("SMIN", "iShares MSCI India Small-Cap"),
           ("EWZ", "iShares MSCI Brazil"), ("EWG", "iShares MSCI Germany"), ("EWU", "iShares MSCI United Kingdom"),
           ("EWY", "iShares MSCI South Korea"), ("EWT", "iShares MSCI Taiwan"), ("EWC", "iShares MSCI Canada"),
           ("EWA", "iShares MSCI Australia")),
    *_etfs("Bonds",
           ("AGG", "iShares Core US Aggregate Bond"), ("BND", "Vanguard Total Bond Market"),
           ("BNDX", "Vanguard Total International Bond"), ("TLT", "iShares 20+ Year Treasury"),
           ("IEF", "iShares 7-10 Year Treasury"), ("SHY", "iShares 1-3 Year Treasury"), ("SGOV", "iShares 0-3 Month Treasury"),
           ("BIL", "SPDR 1-3 Month T-Bill"), ("GOVT", "iShares US Treasury Bond"), ("LQD", "iShares Investment Grade Corporate"),
           ("VCIT", "Vanguard Intermediate-Term Corporate"), ("HYG", "iShares High Yield Corporate"),
           ("JNK", "SPDR Bloomberg High Yield"), ("TIP", "iShares TIPS Bond"), ("MUB", "iShares National Muni Bond"),
           ("EMB", "iShares JP Morgan USD Emerging Markets Bond")),
    *_etfs("Commodities & currency",
           ("GLD", "SPDR Gold Shares"), ("IAU", "iShares Gold Trust"), ("SLV", "iShares Silver Trust"),
           ("USO", "United States Oil"), ("UNG", "United States Natural Gas"), ("DBC", "Invesco DB Commodity Index"),
           ("PDBC", "Invesco Optimum Yield Diversified Commodity"), ("CPER", "United States Copper"),
           ("DBA", "Invesco DB Agriculture"), ("UUP", "Invesco DB US Dollar Bullish")),
]

_INDIA = [
    # Yahoo tickers where Yahoo has real history. Checked Oct 2026: it has no series at all for Nifty
    # Midcap 150, BSE MidCap / SmallCap, Nifty Total Market, Smallcap 100, Microcap 250, Oil & Gas,
    # Consumer Durables and India Defence, and only the last bar or two for Nifty Private Bank, Healthcare,
    # Media, Services Sector and Commodities. Those come from the index providers themselves (NSE Indices,
    # BSE) under `NSE:` / `BSE:` tickers — official_indices.py fetches them and must list each one.
    *_indices("Broad market",
              ("^NSEI", "Nifty 50"), ("^BSESN", "BSE Sensex"), ("^NSMIDCP", "Nifty Next 50"), ("^CNX100", "Nifty 100"),
              ("^CNX200", "Nifty 200"), ("^CRSLDX", "Nifty 500"), ("^NSEMDCP50", "Nifty Midcap 50"),
              ("NIFTYSMLCAP250.NS", "Nifty Smallcap 250"), ("^INDIAVIX", "India VIX"),
              ("NSE:NIFTY_MIDCAP_150", "Nifty Midcap 150"), ("NSE:NIFTY_SMALLCAP_100", "Nifty Smallcap 100"),
              ("NSE:NIFTY_MICROCAP_250", "Nifty Microcap 250"), ("NSE:NIFTY_TOTAL_MARKET", "Nifty Total Market"),
              ("BSE:MIDCAP", "BSE MidCap"), ("BSE:SMALLCAP", "BSE SmallCap")),
    *_indices("Sector",
              ("^NSEBANK", "Nifty Bank"), ("^CNXPSUBANK", "Nifty PSU Bank"), ("NIFTY_FIN_SERVICE.NS", "Nifty Financial Services"),
              ("^CNXIT", "Nifty IT"), ("^CNXPHARMA", "Nifty Pharma"), ("^CNXAUTO", "Nifty Auto"), ("^CNXFMCG", "Nifty FMCG"),
              ("^CNXMETAL", "Nifty Metal"), ("^CNXREALTY", "Nifty Realty"), ("^CNXENERGY", "Nifty Energy"),
              ("^CNXINFRA", "Nifty Infrastructure"), ("NSE:NIFTY_PRIVATE_BANK", "Nifty Private Bank"),
              ("NSE:NIFTY_HEALTHCARE", "Nifty Healthcare"), ("NSE:NIFTY_MEDIA", "Nifty Media"),
              ("NSE:NIFTY_OIL_GAS", "Nifty Oil & Gas"), ("NSE:NIFTY_CONSUMER_DURABLES", "Nifty Consumer Durables")),
    *_indices("Thematic",
              ("^CNXPSE", "Nifty PSE"), ("^CNXMNC", "Nifty MNC"), ("^CNXCONSUM", "Nifty India Consumption"),
              ("NSE:NIFTY_SERVICES_SECTOR", "Nifty Services Sector"), ("NSE:NIFTY_COMMODITIES", "Nifty Commodities"),
              ("NSE:NIFTY_INDIA_DEFENCE", "Nifty India Defence")),
]

TRACKED: dict[str, list[Instrument]] = {"us": _US, "india": _INDIA}


def for_market(market: str) -> list[Instrument]:
    return TRACKED.get(market, [])


def symbols(market: str) -> list[str]:
    return [i.ticker for i in for_market(market)]
