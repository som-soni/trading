"""A stock that pays out most of its price does not pass a turnover floor on its pre-payout trading.

The ranked books' liquidity floor reads a 20-day mean of daily traded value. AURUM (ex-Majesco) went ex a
98.8% special dividend on 2020-12-23 (₹717 -> ₹8.88). A plain mean of close x volume kept valuing the
shares traded before the ex-date at ₹710 for 20 sessions, so on 2020-12-31 it read ₹121 cr a day while
the stock traded ₹8 lakh, in a locked upper circuit -- and momentum_baseline "bought" 64% of the day's
value there, a trade that made 11% of the run's profit. `corporate_actions.traded_value` values every
session of the window on today's price basis, as a split already is; `baseline.load_prices` reads it,
and so does the per-stock `dollar_vol_sma20` (`indicators.enrich_daily`'s `credits`, measured on the
stock's own bars by `corporate_actions.credits_in`) that the gated strategies' liquidity gate, the
screens and the stored `prices` column read.

Synthetic bars, no database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_turnover_after_actions
"""

import sys

import pandas as pd

from swing_screener.backtesting import baseline
from swing_screener.core import indicators as ind
from swing_screener.marketdata import corporate_actions as ca

FAILS: list[str] = []
FLOOR = 500_000_000          # ₹50 cr a day, momentum_baseline's India floor
IDX = pd.bdate_range("2020-01-01", periods=320)
EX = 300                     # the ex-date's bar


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _bars(close: list[float], volume: list[float]) -> pd.DataFrame:
    c = pd.Series(close, index=IDX)
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": pd.Series(volume, index=IDX)})


def _payer() -> tuple[pd.DataFrame, pd.DataFrame]:
    """₹700, 1.5 M shares a day (₹105 cr), then ex a ₹691 special dividend: ₹9, 50,000 shares (₹4.5 lakh)."""
    close = [700.0] * EX + [9.0] * (len(IDX) - EX)
    vol = [1_500_000.0] * EX + [50_000.0] * (len(IDX) - EX)
    cr = pd.DataFrame([{"symbol": "PAYER", "date": IDX[EX], "kind": "special_dividend", "cash": 691.0,
                        "prev_close": 700.0, "open": 9.0, "pct": 691 / 700, "detail": "synthetic"}])
    return _bars(close, vol), cr


def main() -> int:
    payer, cr = _payer()
    plain = (payer["close"] * payer["volume"]).rolling(20, min_periods=20).mean()
    tv = ca.traded_value(payer["close"], payer["volume"], cr)
    day = IDX[EX + 5]

    print("traded value after a 98.7% special dividend")
    check("the plain 20-day mean is stale: it still clears ₹50 cr five sessions after the ex-date",
          plain[day] >= FLOOR, f"{plain[day]:,.0f}")
    check("traded_value does not clear ₹50 cr then", tv[day] < FLOOR, f"{tv[day]:,.0f}")
    # 14 pre-ex sessions at 1.5 M shares x ₹9 and 6 post-ex (the ex-date and five after) at 50,000 x ₹9, on today's ₹9 basis
    want = (14 * 1_500_000 * 9.0 + 6 * 50_000 * 9.0) / 20
    check("...it values the pre-ex shares at today's price, as a split would be",
          abs(tv[day] - want) < 1e-3 * want, f"{tv[day]:,.0f} vs {want:,.0f}")
    check("before the ex-date it equals the plain mean exactly (no action after t leaks in)",
          tv.iloc[:EX].equals(plain.iloc[:EX]))
    check("once the window has left the ex-date behind it equals the plain mean exactly",
          tv.iloc[EX + 19:].equals(plain.iloc[EX + 19:]))

    print("a lagged median (parabolic_short's size tier, stage4_shorts' turnover)")
    med = ca.traded_value(payer["close"], payer["volume"], cr, 50, stat="median", lag=11)
    plain_med = (payer["close"] * payer["volume"]).shift(11).rolling(50, min_periods=50).median()
    adj_tv = pd.Series([9.0] * len(IDX), index=IDX) * payer["volume"]          # every session on today's ₹9 basis
    want_med = adj_tv.shift(11).rolling(50, min_periods=50).median()
    check("before the ex-date it is the plain lagged median, bit for bit", med.iloc[:EX].equals(plain_med.iloc[:EX]))
    check("from the ex-date on, every session in its window is on today's price basis",
          ((med.iloc[EX:] - want_med.iloc[EX:]).abs() <= 1e-6 * want_med.iloc[EX:]).all())
    med5 = ca.traded_value(payer["close"], payer["volume"], cr, 5, stat="median", lag=2)
    plain5 = (payer["close"] * payer["volume"]).shift(2).rolling(5, min_periods=5).median()
    check("once the lagged window has left the ex-date behind it is the plain median again",
          med5.iloc[EX + 6:].equals(plain5.iloc[EX + 6:]))

    print("a stock with no credited action")
    calm = _bars([100.0 + i * 0.1 for i in range(len(IDX))], [2e6 + i for i in range(len(IDX))])
    check("traded_value is bit-identical to the plain mean",
          ca.traded_value(calm["close"], calm["volume"], None).equals(
              (calm["close"] * calm["volume"]).rolling(20, min_periods=20).mean()))

    print("the ranked books' loader and floor (baseline.load_prices -> eligible_scores)")
    bars = {"PAYER": payer, "CALM": calm.assign(volume=calm["volume"] * 30)}   # CALM: ~₹60-100 cr a day
    saved = (baseline.universe.load_universe, baseline.universe.non_stock_symbols,
             baseline.cache.load_cached, baseline.corporate_actions.credits)
    try:
        baseline.universe.load_universe = lambda market: list(bars)
        baseline.universe.non_stock_symbols = lambda market: set()
        baseline.cache.load_cached = lambda market, sym: bars.get(sym)
        baseline.corporate_actions.credits = lambda market, symbols=None: cr
        px, dv, sma200, tr = baseline.load_prices("india", min_bars=250)
    finally:
        (baseline.universe.load_universe, baseline.universe.non_stock_symbols,
         baseline.cache.load_cached, baseline.corporate_actions.credits) = saved
    check("load_prices' turnover frame is traded_value", dv.loc[day, "PAYER"] == tv[day],
          f"{dv.loc[day, 'PAYER']:,.0f}")
    score = pd.Series({"PAYER": 0.9, "CALM": 0.3})
    elig = baseline.eligible_scores(px.columns, px.loc[day], dv.loc[day], sma200.loc[day], score,
                                    floor_price=1.0, liq_floor=FLOOR, trend_filter=True,
                                    liquidity_rank_top=None, trend_row=tr.loc[day])
    check("the payer is not eligible five sessions after its ex-date", "PAYER" not in elig, str(elig))
    check("a liquid stock in an uptrend still is", "CALM" in elig, str(elig))
    elig_before = baseline.eligible_scores(px.columns, px.loc[IDX[EX - 1]], dv.loc[IDX[EX - 1]],
                                           sma200.loc[IDX[EX - 1]], score, floor_price=1.0, liq_floor=FLOOR,
                                           trend_filter=False, liquidity_rank_top=None)
    check("the payer was eligible before its ex-date, when it traded ₹105 cr a day", "PAYER" in elig_before,
          str(elig_before))

    print("the per-stock indicator (enrich_daily's credits, measured by credits_in)")
    acts = pd.DataFrame([
        {"symbol": "PAYER", "ex_date": IDX[EX], "kind": "dividend", "value": 691.0, "source": "yahoo", "detail": "synthetic"},
        {"symbol": "PAYER", "ex_date": IDX[100], "kind": "dividend", "value": 7.0, "source": "yahoo", "detail": "ordinary"},
        {"symbol": "PAYER", "ex_date": IDX[EX], "kind": "dividend", "value": 691.0, "source": "yahoo", "detail": "twice"}])
    got = ca.credits_in(payer, acts)
    check("credits_in finds the special dividend once, measured on the frame (an ordinary 1% one is not credited)",
          got is not None and len(got) == 1 and got["date"].iloc[0] == IDX[EX] and got["cash"].iloc[0] == 691.0,
          str(got))
    check("...and none in a frame cut before the ex-date (point in time)", ca.credits_in(payer.iloc[:EX], acts) is None)
    e = ind.enrich_daily(payer, got)
    check("enrich_daily's dollar_vol_sma20 is traded_value", e["dollar_vol_sma20"].equals(tv))
    check("without credits it is the plain mean, bit for bit", ind.enrich_daily(payer)["dollar_vol_sma20"].equals(plain))
    cut = payer.loc[:day]
    check("enriching a frame cut at t gives t's full-history value (sliceable, no look-ahead)",
          ind.enrich_daily(cut, ca.credits_in(cut, acts))["dollar_vol_sma20"].equals(e["dollar_vol_sma20"].loc[:day]))
    check("every other column is untouched by credits",
          ind.enrich_daily(payer).drop(columns="dollar_vol_sma20").equals(e.drop(columns="dollar_vol_sma20")))
    from types import SimpleNamespace
    from swing_screener.strategies.base import tradable_point_in_time
    cfg = SimpleNamespace(screener=SimpleNamespace(min_dollar_volume=FLOOR))
    check("the gated strategies' liquidity gate fails the payer five sessions after its ex-date",
          not tradable_point_in_time(cfg, e.loc[day])[0])
    check("...and passed it before the ex-date", tradable_point_in_time(cfg, e.loc[IDX[EX - 1]])[0])

    print("the 50-day traded-value ranks (spec.top_dollar_volume / traded_value_ranks)")
    from swing_screener.backtesting import spec
    longs = pd.concat([b.assign(symbol=sym).rename_axis("date").reset_index()
                       for sym, b in (("PAYER", payer), ("CALM", calm.iloc[5:]))])   # CALM lists later: a gap
    saved_p = ca.payouts
    try:
        ca.payouts = lambda market: {"PAYER": acts}
        v50 = spec._traded_value_50("india", longs)
    finally:
        ca.payouts = saved_p
    plain50 = (payer["close"] * payer["volume"]).rolling(50, min_periods=40).mean()
    tv50 = ca.traded_value(payer["close"], payer["volume"], got, 50, 40)
    check("the payer's 50-day value is traded_value's", v50["PAYER"].equals(tv50))
    check("...which no longer reads its pre-payout trading 15 sessions on",
          v50.loc[IDX[EX + 15], "PAYER"] < 0.5 * plain50[IDX[EX + 15]])
    calm50 = (calm["close"] * calm["volume"]).iloc[5:].reindex(IDX).rolling(50, min_periods=40).mean()
    check("a stock with no payout keeps the plain 50-day mean, bit for bit", v50["CALM"].equals(calm50))

    print(f"\n{'OK — a payout does not leave the turnover floor reading pre-payout trading.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
