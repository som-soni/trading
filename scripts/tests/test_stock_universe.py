"""Stock strategies screen and trade operating companies only (marketdata/universe.py `non_stock_symbols`,
`stock_universe`).

Prompted by the daily Darvas screen listing LIQUID1.NS and LIQUIDADD.NS (money-market ETFs) as "TRADE - HIGH
CONFIDENCE": a liquid fund's price climbs in a near-straight line, so price-pattern rules read it as a perfect
breakout. The fund rule existed but only the portfolio backtests applied it; the daily screens and the stock
backtests read the raw universe file.

Reads the stored names and classifications (Postgres), so it checks the rule against the real universe.

    PYTHONPATH=. .venv/bin/python -m tests.test_stock_universe
"""

import re
import sys
from pathlib import Path

from swing_screener.marketdata import universe

FAILS: list[str] = []
ROOT = Path(__file__).resolve().parent.parent / "swing_screener"

# instruments that must never reach a stock strategy, when they are in the universe file
NOT_STOCKS = {
    "india": ["LIQUID1.NS", "LIQUIDADD.NS", "LIQUIDCASE.NS", "LIQUIDIETF.NS", "LIQUIDBEES.NS", "LIQUIDSBI.NS",
              "ABSLLIQUID.NS", "ICICIB22.NS", "NIFTYBEES.NS", "GOLDBEES.NS"],
    "us": ["BAR", "ENO", "EAI", "VXX", "SGOV", "BIL", "SHV", "USFR", "TFLO", "JPST", "MINT"],
}
# operating companies whose names or symbols look like funds and must stay
STOCKS = {
    "india": ["RELIANCE.NS", "CHEMBOND.NS", "BONDADA.NS", "PNBGILTS.NS", "JETFREIGHT.NS"],
    "us": ["AAPL", "NTRS", "AAT", "LQDT", "LQDA"],
}


def check(what: str, ok: bool) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}")
    if not ok:
        FAILS.append(what)


def main() -> int:
    for market in ("india", "us"):
        listed = set(universe.load_universe(market))
        su = set(universe.stock_universe(market))
        bad = [s for s in NOT_STOCKS[market] if s in su]
        check(f"{market}: no fund, ETF or listed debt in the stock universe ({len(listed):,} -> {len(su):,})"
              + (f" -- found {bad}" if bad else ""), not bad)
        lost = [s for s in STOCKS[market] if s in listed and s not in su]
        check(f"{market}: real companies with fund-like names stay" + (f" -- lost {lost}" if lost else ""), not lost)
        check(f"{market}: no index symbols", not any(s.startswith("^") for s in su))

    # every stock universe reads the one rule, not the raw file
    for rel, fn in (("screening/pipeline.py", "_run"), ("backtesting/backtest.py", "_point_in_time_candidates")):
        src = (ROOT / rel).read_text()
        body = re.search(rf"def {fn}\(.*?(?=\ndef )", src, re.S)
        ok = bool(body) and "universe.stock_universe(" in body.group(0) and "universe.load_universe(" not in body.group(0)
        check(f"{rel} {fn}() reads universe.stock_universe", ok)
    br = (ROOT / "analytics" / "breadth.py").read_text()
    check("Screens/breadth `eligible` is the same rule", "return universe.stock_universe(market)" in br)

    print("FAIL" if FAILS else "OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
