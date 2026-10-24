"""Chart-pattern trades a review found wrong, pinned on stored prices.

Each row is a signal bar a past chart_pattern version traded, and what the current rules say about
it. The synthetic mutations in test_pattern_spec prove each rule is wired; these prove the rules
catch the real charts that motivated them, and that the good trades in the same review survive.
Skipped (not failed) for a symbol with no stored prices.

Run: `PYTHONPATH=. .venv/bin/python -m tests.test_pattern_regressions`
"""

import sys

from swing_screener.core import indicators as ind
from swing_screener.marketdata import cache
from swing_screener.strategies import chart_pattern_spec as m

# (market, symbol, setup, signal date, tradeable now?, why)
CASES = [
    ("india", "JINDALSTEL.NS", "IHS", "2022-10-25", False,
     "v1.11 HS-09: the 'left shoulder' low was followed by a new high"),
    ("india", "ICICIBANK.NS", "FWDG", "2015-08-03", False,
     "v1.12: a falling wedge refitted over the first one's failed breakout"),
    ("india", "ICICIBANK.NS", "IHS", "2016-04-27", False,
     "v1.12 EARLY_BREAKOUT: the neckline broke on 2016-04-21, before the right shoulder confirmed"),
    ("india", "ICICIBANK.NS", "ATRI", "2017-05-04", False,
     "v1.12 TL-04: closed above the upper line in November 2016, then touched it again"),
    ("india", "ICICIBANK.NS", "ATRI", "2025-03-21", False,
     "v1.12 TL-04: closed above the upper line in September 2024, then touched it again"),
    ("india", "PFC.NS", "DBOT", "2020-02-12", False,
     "v1.13 OW-03: the 'first low' 85.76 came after a 72.36 low below the base high"),
    # the same review's sound patterns must survive
    ("india", "ICICIBANK.NS", "DBOT", "2013-04-25", True, "a clean O'Neil W"),
    ("india", "ICICIBANK.NS", "FWDG", "2015-05-29", True, "a converging wedge, 61% to the apex"),
    ("india", "ICICIBANK.NS", "FWDG", "2026-06-10", True,
     "a wedge whose earlier close above the line came after its last touch"),
]


def main() -> None:
    failures, ran = [], 0
    frames: dict = {}
    for market, sym, code, date, want, why in CASES:
        if (market, sym) not in frames:
            raw = cache.load_cached(market, sym)
            frames[(market, sym)] = None if raw is None or raw.empty else ind.enrich_daily(raw)
        d = frames[(market, sym)]
        if d is None:
            print(f"skip  {sym} {code} {date} — no stored prices")
            continue
        ran += 1
        r = m.BULLISH[code][1](d.loc[:date])
        got = m._tradeable(r)
        detail = (f"state={r.get('state')} fail={r.get('fail')} "
                  f"age={r.get('metrics', {}).get('bars_since_breakout')}")
        ok = got == want
        print(f"{'ok  ' if ok else 'FAIL'}  {sym} {code} {date} {'trades' if want else 'rejected'} — {why}"
              + ("" if ok else f"  [{detail}]"))
        if not ok:
            failures.append(f"{sym} {code} {date}")
    if failures:
        print(f"\n{len(failures)} regression(s): {', '.join(failures)}")
        sys.exit(1)
    print(f"\nall {ran} pinned pattern reads hold")


if __name__ == "__main__":
    main()
