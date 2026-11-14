"""Boucher's timing models: release lags, the rules' thresholds, the Nasdaq reversal and the book.

No database: every check runs on small hand-made series, so it says what the code does, not what the
market did.

    PYTHONPATH=. .venv/bin/python -m tests.test_boucher
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.backtesting import boucher_bonds_gold as bg
from swing_screener.backtesting import boucher_book as bb
from swing_screener.backtesting import boucher_stocks as bs

FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("  ok    " if ok else "  FAIL  ") + name)
    if not ok:
        FAILS.append(name)


def release_lag() -> None:
    print("an economic number is read only after its release")
    # April 2020's unemployment, stamped 2020-04-01 by FRED, came out on 2020-05-08
    obs = pd.Series([4.4, 14.7], index=pd.to_datetime(["2020-03-01", "2020-04-01"]))
    at = pd.to_datetime(["2020-04-30", "2020-05-29"])
    got = bs.as_of(bs.lagged(obs, bs.UNEMP_LAG_DAYS), at)
    check("at the end of April only March's rate is known", got.iloc[0] == 4.4)
    check("at the end of May April's rate is known", got.iloc[1] == 14.7)
    check("nothing is known before the first release",
          np.isnan(bs.as_of(bs.lagged(obs, bs.UNEMP_LAG_DAYS), pd.to_datetime(["2020-03-31"])).iloc[0]))
    check("every lag is at least a month after FRED's date (monthly) or a quarter (GDP)",
          min(bs.CPI_LAG_DAYS, bs.INDPRO_LAG_DAYS, bs.CAPACITY_LAG_DAYS, bs.UNEMP_LAG_DAYS,
              bs.SENTIMENT_LAG_DAYS, bs.BAA_LAG_DAYS) > 31 and bs.GDP_LAG_DAYS > 92 + 21)


def calendar() -> None:
    print("weekly and monthly readings fall on the right sessions")
    idx = pd.bdate_range("2021-03-29", "2021-04-09").drop(pd.Timestamp("2021-04-02"))   # Good Friday
    wk = bs.week_ends(idx)
    check("a week whose Friday is a holiday is read on its Thursday", pd.Timestamp("2021-04-01") in wk)
    check("a normal week is read on its Friday", pd.Timestamp("2021-04-09") in wk)
    me = bs.month_ends(idx)
    check("a month is read on its last session", pd.Timestamp("2021-03-31") in me)


def hysteresis() -> None:
    print("in-out rules with a neutral zone keep their state")
    e = pd.Series([False, True, False, False, False])
    lv = pd.Series([False, False, False, True, False])
    check("off before the first entry, on until the exit, off after it",
          list(bs.hysteresis(e, lv)) == [False, True, True, False, False])


def switches() -> None:
    print("each switch at his published threshold")
    r = pd.DataFrame({
        "tbill_roc": [5.9, 6.0], "bond_roc": [-1.4, -1.5], "long_roc": [9.0, 9.1], "curve": [1.16, 1.15],
        "capacity": [81.5, 81.6], "indpro_roc": [5.6, 5.7], "unemp_change": [0.1, -0.1],
        "cpi_fast": [2.0, 3.0], "cpi_slow": [2.5, 3.0], "cpi_yoy": [3.1, 3.3], "gdp_growth": [3.9, 4.1],
        "sentiment": [99.5, 99.6]}, index=pd.to_datetime(["2020-01-31", "2020-02-28"]))
    s = bs.switch_states(r)
    for k in ("tbill_roc", "bond_roc", "long_roc", "curve", "capacity", "indpro", "unemployment", "cpi_trend",
              "cpi_gdp", "sentiment", "monetary"):
        check(f"{k}: bullish on the first row, not on the second", bool(s[k].iloc[0]) and not bool(s[k].iloc[1]))
    hot = pd.DataFrame({"tbill_roc": [10.0], "bond_roc": [-3.0], "long_roc": [12.0], "curve": [1.0],
                        "capacity": [89.0], "indpro_roc": [3.0], "unemp_change": [0.0], "cpi_fast": [4.0],
                        "cpi_slow": [3.0], "cpi_yoy": [4.0], "gdp_growth": [5.0], "sentiment": [100.0]},
                       index=pd.to_datetime(["2020-01-31"]))
    check("the brake engages when overheated, inflation rising and the rate models bearish",
          not bool(bs.switch_states(hot)["brake"].iloc[0]))
    calm = hot.assign(capacity=[80.0], indpro_roc=[2.0])
    check("the brake stays off when the economy is not overheated",
          bool(bs.switch_states(calm)["brake"].iloc[0]))
    miss = r.iloc[:1].assign(capacity=[np.nan])
    check("a missing reading is not bullish", not bool(bs.switch_states(miss)["capacity"].iloc[0]))


def base_rule() -> None:
    print("the 40-week rule")
    idx = pd.bdate_range("2018-01-01", periods=5 * 60)
    up = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    falling = pd.Series(np.linspace(5, 2, len(idx)), index=idx)
    rising = pd.Series(np.linspace(2, 5, len(idx)), index=idx)
    st, _ = bs.base_rule(up, falling, rising)
    check("no reading before 40 weeks of history", not bool(st.iloc[10]))
    check("S&P up and the T-bill falling: in", bool(st.iloc[-1]))
    st2, _ = bs.base_rule(up, rising, rising)
    check("both yields rising: out", not bool(st2.iloc[-1]))
    st3, _ = bs.base_rule(up[::-1].set_axis(idx), falling, falling)
    check("S&P below its average: out, whatever the yields", not bool(st3.iloc[-1]))


def otc_reversal() -> None:
    print("the Nasdaq 7.9% reversal")
    px = [100, 110, 101.4, 101.3, 95, 102.4, 102.6]
    c = pd.Series(px, index=pd.bdate_range("2020-01-01", periods=len(px)))
    p = bs.otc_target(c)
    check("still long 7.8% below the peak", p.iloc[2] == 1)
    check("short at 7.9% below the peak", p.iloc[3] == -1)
    check("still short 7.8% above the trough", p.iloc[5] == -1)
    check("long again at 7.9% above the trough", p.iloc[6] == 1)
    check("the long/cash variant is out instead of short", list(bs.otc_target(c, short=False).iloc[3:6]) == [0, 0, 0])


def book() -> None:
    print("the book: fills a session later, cash, shorts, costs")
    idx = pd.bdate_range("2020-01-06", periods=6)
    px = pd.Series([100, 100, 100, 110, 121, 121], index=idx, dtype=float)
    want = pd.Series([0, 1, 1, 1, 0, 0], index=idx)
    rate = pd.Series(0.0, index=idx)
    t, eq, held, _c, costs, pos = bs.simulate(px, want, rate, "2020-01-06", 0.0, 1000.0, "X")
    check("a signal on day 2's close is filled at day 3's close", list(pos) == [0, 0, 1, 1, 1, 0])
    check("the holding earns days 4 and 5 (+10%, +10%), not day 2's signal close",
          abs(eq.iloc[-1] - 1210.0) < 1e-6)
    check("one round trip", len(t) == 1 and abs(t["r_multiple"].iloc[0] - 0.21) < 1e-9)
    _t, eq_s, *_ = bs.simulate(px, -want, pd.Series(0.0, index=idx), "2020-01-06", 0.0, 1000.0, "X")
    check("a short loses what the long makes, day by day", abs(eq_s.iloc[-1] - 1000 * 0.9 * 0.9) < 1e-6)
    _t, eq_c, *_ = bs.simulate(px, want * 0, pd.Series(0.0365, index=idx), "2020-01-06", 0.0, 1000.0, "X")
    days = (idx[-1] - idx[0]).days
    check("cash earns the T-bill rate per calendar day", abs(eq_c.iloc[-1] - 1000 * (1.0001) ** days) < 1e-6)
    _t, eq_k, _h, _c, costs, _p = bs.simulate(px * 0 + 100, want, rate, "2020-01-06", 10.0, 1000.0, "X")
    check("costs are charged on the way in and on the way out", abs(costs - (1.0 + 0.999)) < 1e-6)


def bonds() -> None:
    print("bond arithmetic")
    check("a bond priced at its own coupon is at par", abs(float(bs.bond_price(5.0, 5.0, 20)) - 100) < 1e-9)
    y = pd.Series([5.0, 6.0], index=pd.to_datetime(["2020-01-01", "2020-02-01"]))
    idx = bs.bond_index(y, 20)
    check("a price index falls when the yield rises", idx.iloc[1] < idx.iloc[0])
    tr = bs.bond_index(y, 20, carry=True)
    check("the total-return index adds the coupon earned", tr.iloc[1] > idx.iloc[1])


def bond_gold_rules() -> None:
    print("bond and gold rules read averages only once they exist")
    s = pd.Series(np.arange(1.0, 31.0))
    a = bg.above(s, 10)
    check("no reading before the average has its weeks", a.iloc[:9].isna().all() and a.iloc[9] is not np.nan)
    check("a rising series is above its average", bool(a.iloc[-1]))
    check("and a falling one below it", bool(bg.below(s[::-1].reset_index(drop=True), 10).iloc[-1]))


def zero_bound() -> None:
    print("the zero-bound floor: off by default (1.2), silences the bill below it with --zero-bound")
    idx = pd.bdate_range("2018-01-01", periods=5 * 60)
    up = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    low_falling = pd.Series(np.linspace(0.45, 0.05, len(idx)), index=idx)      # under the floor, falling
    rising = pd.Series(np.linspace(2, 5, len(idx)), index=idx)
    falling = pd.Series(np.linspace(5, 2, len(idx)), index=idx)
    st0, _ = bs.base_rule(up, low_falling, rising)
    check("by default (1.0's rule) a falling bill under 0.5% still keeps the S&P in", bool(st0.iloc[-1]))
    st, r = bs.base_rule(up, low_falling, rising, zero_bound=True)
    check("a falling bill under the floor does not keep the S&P in when the long yield rises", not bool(st.iloc[-1]))
    check("the readings say the bill was silent", not bool(r["tbill_live"].iloc[-1]))
    st2, _ = bs.base_rule(up, low_falling, falling, zero_bound=True)
    check("under the floor the long yield decides alone: falling long yield, in", bool(st2.iloc[-1]))
    above_floor = pd.Series(np.linspace(3.0, bs.TBILL_FLOOR_PCT + 0.01, len(idx)), index=idx)
    st3, _ = bs.base_rule(up, above_floor, rising, zero_bound=True)
    check("a falling bill at or above the floor still counts", bool(st3.iloc[-1]))


def trade_log() -> None:
    print("the trade log: both fees in costs, the fund's own prices")
    idx = pd.bdate_range("2020-01-06", periods=6)
    level = pd.Series([1000, 1000, 1000, 1100, 1210, 1210], index=idx, dtype=float)
    quote = pd.Series([50, 50, 50, 55, 60.5, 60.5], index=idx, dtype=float)
    want = pd.Series([0, 1, 1, 1, 0, 0], index=idx)
    t, _eq, _h, _c, costs, _p = bs.simulate(level, want, pd.Series(0.0, index=idx), "2020-01-06", 10.0, 1000.0,
                                             "X", quote=quote)
    row = t.iloc[0]
    check("costs on the row are the entry fee plus the exit fee", abs(row["costs"] - costs) < 0.01)
    check("entry and exit prices are the quote", row["entry_price"] == 50 and row["exit_price"] == 60.5)
    check("the total-return levels are logged beside them", row["entry_tr_level"] == 1000 and row["exit_tr_level"] == 1210)
    t2, *_ = bs.simulate(level, want, pd.Series(0.0, index=idx), "2020-01-06", 0.0, 1000.0, "X",
                         quote=quote.iloc[:3])
    check("a date with no quote leaves the price blank", t2["exit_price"].isna().iloc[0])


def mixing() -> None:
    print("the combined book: fixed weights, monthly rebalance, costs on what moves")
    idx = pd.bdate_range("2020-01-01", "2020-03-31")
    a = pd.Series(np.linspace(1.0, 2.0, len(idx)), index=idx)      # doubles over the quarter
    c = pd.Series(1.0, index=idx)                                  # flat
    eq, vals, paid = bb.mix({"a": a, "c": c}, {"a": 50, "c": 50}, 0.0)
    jan = bs.month_ends(idx)[0]
    check("weights are restored at a month-end", abs(vals.at[jan, "a"] - vals.at[jan, "c"]) < 1e-12)
    check("between month-ends the weights drift", vals["a"].iloc[3] > vals["c"].iloc[3])
    check("no cost at zero bps", paid == 0.0)
    _e, _v, paid10 = bb.mix({"a": a, "c": c}, {"a": 50, "c": 50}, 10.0)
    check("rebalancing pays on the value moved", paid10 > 0)
    held, _v2, _p2 = bb.mix({"a": a, "c": c}, {"a": 100, "c": 0}, 0.0)
    check("a 100% weight is the sleeve itself", abs(held.iloc[-1] - 2.0) < 1e-9)
    rate = pd.Series(0.0, index=idx)
    st = bb.book_stats(a, rate)
    check("book stats: a rising line has no drawdown", st["max_dd_pct"] == 0.0)


def main() -> int:
    release_lag()
    calendar()
    hysteresis()
    switches()
    base_rule()
    otc_reversal()
    book()
    bonds()
    bond_gold_rules()
    zero_bound()
    trade_log()
    mixing()
    print(f"\n{'FAIL' if FAILS else 'OK'} — {len(FAILS)} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
