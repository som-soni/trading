"""Checks for the index-investing suite — synthetic data, no database.

The headline check is **lookahead safety**. Every timing result in Family B
depends on a signal on date *t* using only prices up to *t-1*, and that
property is invisible in a backtest's output: a leaking signal just looks
like a brilliant strategy. So it is tested the way `test_chart_patterns.py`
tests pivot leakage — move the last bar and assert nothing earlier changes,
then move a bar and assert the signal on that same bar does not change.

Also checked: the vendor-artefact repair (on fabricated artefacts whose
right answer is known), FIFO tax lot classification, cash accrual, XIRR
against closed-form answers, and the accumulation invariant that every
deployment rule contributes the same money on the same dates — without
which the Family A table compares savings rates, not timing.

Run: `PYTHONPATH=. python3 -m tests.test_index_investing`
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.backtesting import index_accumulate as acc
from swing_screener.backtesting import index_allocate as alloc
from swing_screener.backtesting import index_signals as sig
from swing_screener.backtesting import index_stats as stats
from swing_screener.backtesting.index_core import Book, Context, TaxModel, align
from swing_screener.marketdata import index_data

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


def bdays(n: int, start: str = "2000-01-03") -> pd.DatetimeIndex:
    return pd.bdate_range(start, periods=n)


def ramp(n: int, a: float = 100.0, growth: float = 0.0003) -> pd.Series:
    return pd.Series(a * (1 + growth) ** np.arange(n), index=bdays(n))


def ctx_of(px: pd.Series, rate: float = 0.0, market: str = "us") -> Context:
    idx, prices = align({"EQ": px})
    return Context(market, "$", idx, prices,
                   pd.Series(rate, index=idx), [])


# --- 1. vendor-artefact repair ------------------------------------------


def test_repair() -> None:
    n = 300
    s = ramp(n)

    # (a) spike reversal: a 1:10 split applied for two days only, exactly the
    # NIFTYBEES/GOLDBEES/MON100 bug.
    bad = s.copy()
    bad.iloc[150:152] = bad.iloc[150:152] / 10
    out, log = index_data.repair(pd.DataFrame({"close": bad}), "t")
    err = float((out["close"] / s - 1).abs().max())
    check(err < 0.01, f"spike reversal not repaired: max residual {err:.3%}")
    check(len(log) == 1 and "interpolated" in log[0],
          f"spike reversal should log one interpolation, got {log}")

    # (b) persistent unapplied split: level halves and stays halved. The
    # repaired series must be continuous in RETURN space, which is all a
    # backtest reads.
    bad = s.copy()
    bad.iloc[200:] = bad.iloc[200:] / 10
    out, log = index_data.repair(pd.DataFrame({"close": bad}), "t")
    r = out["close"].pct_change().abs().max()
    check(r < 0.05, f"persistent split left a {r:.1%} jump behind")
    check(len(log) == 1 and "back-adjusted" in log[0],
          f"persistent split should log a back-adjustment, got {log}")

    # (c) opening artefact: a junk second bar, as Nifty Midcap 50 has.
    bad = s.copy()
    bad.iloc[1] = bad.iloc[1] * 3
    out, log = index_data.repair(pd.DataFrame({"close": bad}), "t")
    check(out["close"].pct_change().abs().max() < 0.05,
          "opening artefact survived the repair")
    check(len(out) < len(s), "opening artefact should truncate the series")

    # (d) THE IMPORTANT ONE: a real crash must be left completely alone.
    # 1987-10-19 was -20.5% and 1929-10-28 -12.3%; a repair that eats those
    # silently rewrites market history.
    real = s.copy()
    real.iloc[100] = real.iloc[99] * 0.795      # -20.5%
    real.iloc[101:] = real.iloc[101:] * 0.795
    out, log = index_data.repair(pd.DataFrame({"close": real}), "t")
    check(not log, f"a -20.5% crash was 'repaired': {log}")
    check(np.allclose(out["close"].values, real.values),
          "a -20.5% crash was altered")


# --- 2. lookahead safety ------------------------------------------------


SIGNALS = {
    "sma_overlay": lambda p: sig.sma_overlay(p, 10),
    "dma_cross": lambda p: sig.dma_cross(p, 50),
    "golden_cross": lambda p: sig.golden_cross(p, 10, 50),
    "abs_momentum": lambda p: sig.abs_momentum(p, 60),
    "vol_target": lambda p: sig.vol_target_weight(p, 0.15, 30),
    "drawdown_from_peak": lambda p: sig.drawdown_from_peak(p),
}


def test_no_lookahead() -> None:
    rng = np.random.default_rng(5)
    n = 600
    px = pd.Series(
        100 * np.exp(np.cumsum(rng.normal(0.0004, 0.011, n))), index=bdays(n)
    )

    for name, fn in SIGNALS.items():
        base = fn(px)

        # (a) spiking the LAST bar must not change any earlier signal value
        spiked = px.copy()
        spiked.iloc[-1] *= 1.25
        after = fn(spiked)
        diff = (base.iloc[:-1].astype(float) - after.iloc[:-1].astype(float)).abs()
        check(float(diff.max()) < 1e-12,
              f"{name}: spiking the last bar changed {int((diff > 1e-12).sum())} "
              f"earlier signal value(s) — the signal reads the future")

        # (b) the signal ON a bar must not react to that bar's own price,
        # which is the one that gets traded at
        for k in (200, 400, 550):
            moved = px.copy()
            moved.iloc[k] *= 1.30
            m = fn(moved)
            check(abs(float(base.iloc[k]) - float(m.iloc[k])) < 1e-12,
                  f"{name}: changing bar {k}'s price changed the signal AT bar {k} "
                  f"— it would trade on a price it has already seen")


def test_seasonal_is_calendar_only() -> None:
    idx = bdays(800)
    on = sig.seasonal(idx, (11, 12, 1, 2, 3, 4))
    months = {d.month for d, v in on.items() if v}
    check(months == {11, 12, 1, 2, 3, 4}, f"seasonal fired in {sorted(months)}")


# --- 3. the book: lots, costs, cash, tax --------------------------------


def test_fifo_tax_split() -> None:
    tax = TaxModel.india()
    book = Book(100_000.0, 0.0, tax)
    t0 = pd.Timestamp("2020-01-01")
    book.buy(t0, "EQ", 50_000, 100.0)                       # 500 sh @ 100
    book.buy(t0 + pd.Timedelta(days=400), "EQ", 50_000, 200.0)  # 250 sh @ 200

    # Sell 600 shares two months after the second buy: FIFO means the first
    # 500 are long-term (>365d) and the next 100 short-term.
    sell_date = t0 + pd.Timedelta(days=460)
    book.sell(sell_date, "EQ", 600, 250.0)
    check(abs(book.fy_long - 500 * (250 - 100)) < 1.0,
          f"long-term gain should be 75,000, got {book.fy_long:,.0f}")
    check(abs(book.fy_short - 100 * (250 - 200)) < 1.0,
          f"short-term gain should be 5,000, got {book.fy_short:,.0f}")

    # the India exemption applies to the long-term slice
    due = tax.due(book.fy_short, book.fy_long)
    expected = 5_000 * 0.20 + max(0, 75_000 - 125_000) * 0.125
    check(abs(due - expected) < 1.0, f"tax due {due:,.0f}, expected {expected:,.0f}")


def test_costs_and_accrual() -> None:
    book = Book(100_000.0, 10.0, TaxModel.none())   # 10bps
    t0 = pd.Timestamp("2020-01-01")
    book.buy(t0, "EQ", 100_000, 100.0)
    check(abs(book.costs_paid - 100.0) < 1e-6,
          f"10bps on 100k should cost 100, got {book.costs_paid}")
    check(abs(book.shares("EQ") - 999.0) < 1e-6,
          f"expected 999 shares after cost, got {book.shares('EQ')}")

    # cash accrual is CALENDAR-day: 365 single days at 5% must compound to
    # ~5%, and one 365-day step must give the same answer as 365 one-day
    # steps (otherwise a holiday gap would change the interest earned)
    b2 = Book(1_000.0, 0.0, TaxModel.none())
    for _ in range(365):
        b2.accrue(0.05)
    check(abs(b2.cash / 1_000 - 1 - 0.0513) < 1e-3,
          f"365 days at 5% gave {b2.cash / 1_000 - 1:.4%}, expected ~5.13%")
    b3 = Book(1_000.0, 0.0, TaxModel.none())
    b3.accrue(0.05, days=365)
    check(abs(b3.cash - b2.cash) < 1e-6,
          f"one 365-day accrual ({b3.cash}) != 365 one-day accruals ({b2.cash})")


def test_cash_only_earns_the_rate() -> None:
    """A strategy holding nothing must return exactly the cash rate."""
    px = ramp(252 * 4)
    c = ctx_of(px, rate=0.06)
    targets = pd.DataFrame(0.0, index=c.index, columns=["EQ"])
    res = alloc.simulate(c, targets, 100_000, 5.0, TaxModel.none(), "never")
    years = (c.index[-1] - c.index[0]).days / 365.25
    cagr = (float(res.equity.iloc[-1]) / 100_000) ** (1 / years) - 1
    check(abs(cagr - 0.06) < 0.002,
          f"all-cash book returned {cagr:.4%}, expected ~6%")
    check(res.trades.empty, "an all-cash book should place no trades")


def test_buy_hold_tracks_the_index() -> None:
    px = ramp(252 * 5, growth=0.0004)
    c = ctx_of(px)
    targets, cadence = alloc.buy_hold(c, "EQ")
    res = alloc.simulate(c, targets, 100_000, 0.0, TaxModel.none(), cadence)
    want = float(px.iloc[-1] / px.iloc[0])
    got = float(res.equity.iloc[-1]) / 100_000
    check(abs(got / want - 1) < 1e-6,
          f"buy & hold returned {got:.6f}x vs index {want:.6f}x")
    check(len(res.trades) == 1, f"buy & hold should trade once, did {len(res.trades)}")


def test_band_suppresses_trades() -> None:
    """Threshold rebalancing must actually suppress small-drift trades."""
    rng = np.random.default_rng(3)
    n = 252 * 6
    idx = bdays(n)
    a = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n))), index=idx)
    b = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.004, n))), index=idx)
    i, prices = align({"A": a, "B": b})
    c = Context("us", "$", i, prices, pd.Series(0.0, index=i), [])
    mix = {"A": 0.6, "B": 0.4}
    targets, _ = alloc.static_mix(c, mix, "ME")
    tight = alloc.simulate(c, targets, 100_000, 5.0, TaxModel.none(), "ME", band=0.0)
    wide = alloc.simulate(c, targets, 100_000, 5.0, TaxModel.none(), "ME", band=0.10)
    check(len(wide.trades) < len(tight.trades),
          f"a 10% band traded {len(wide.trades)} vs {len(tight.trades)} unbanded")
    check(wide.costs_paid < tight.costs_paid,
          "a 10% band should pay less in costs")


# --- 4. XIRR ------------------------------------------------------------


def test_xirr() -> None:
    # single flow, exactly 10% over one year
    f = [(pd.Timestamp("2020-01-01"), -100.0), (pd.Timestamp("2020-12-31"), 110.0)]
    r = stats.xirr(f)
    check(abs(r - 0.10) < 0.002, f"xirr single-period {r:.4%}, expected 10%")

    # zero return
    f = [(pd.Timestamp("2010-01-01"), -1000.0), (pd.Timestamp("2020-01-01"), 1000.0)]
    check(abs(stats.xirr(f)) < 1e-4, "xirr on a flat outcome should be ~0")

    # a monthly SIP into an asset compounding at exactly 12% must return 12%
    idx = pd.bdate_range("2005-01-03", periods=252 * 12)
    # compound on CALENDAR time: a business-day index has ~261 bars a year,
    # so 1.12**(bar/252) is a 12.45%/yr asset, not a 12% one
    px = pd.Series(
        100 * 1.12 ** ((idx - idx[0]).days / 365.25), index=idx
    )
    c = ctx_of(px)
    sched, _ = acc.schedule(c.index, "dom", 12_000, day=1)
    res = acc.simulate(c, "EQ", sched, 0.0, TaxModel.none(), "immediate")
    s = stats.summarize_accumulation("sip", res)
    check(abs(s.xirr_pct - 12.0) < 0.15,
          f"SIP into a 12% asset gave XIRR {s.xirr_pct:.2f}%, expected ~12%")


# --- 5. accumulation invariants -----------------------------------------


def test_same_money_every_variant() -> None:
    """Every deployment rule must contribute the same total on the same dates.

    If this fails, the Family A table is comparing savings rates and the
    'best' rule is just the one that put in more money.
    """
    px = ramp(252 * 10, growth=0.0003)
    c = ctx_of(px, rate=0.05)
    sched, _ = acc.schedule(c.index, "dom", 12_000, day=1)
    totals = {}
    for rule, kw in (
        ("immediate", {}),
        ("dip", dict(dip_threshold=0.10)),
        ("trend_on", dict(ma_window=200)),
        ("trend_double", dict(ma_window=200)),
        ("value_avg", dict(growth=0.10)),
        ("hindsight", {}),
    ):
        res = acc.simulate(c, "EQ", sched, 2.0, TaxModel.none(), rule, **kw)
        totals[rule] = (round(res.contributed, 2), len(res.cashflows))
    distinct = set(totals.values())
    check(len(distinct) == 1,
          f"deployment rules contributed different money: {totals}")


def test_day_of_month_schedule() -> None:
    idx = bdays(252 * 3)
    for day in (1, 15, 28):
        dates = acc.monthly_dates(idx, day)
        check(len(dates) == len(set((d.year, d.month) for d in dates)),
              f"day {day}: more than one contribution in some month")
        check(all(d.day >= day or d == max(x for x in idx if x.month == d.month
                                           and x.year == d.year)
                  for d in dates),
              f"day {day}: a contribution landed before the chosen day")
    first = acc.monthly_dates(idx, "first")
    last = acc.monthly_dates(idx, "last")
    check(all(f <= l for f, l in zip(first, last)),
          "'first' trading day landed after 'last'")
    check(len(first) == len(last), "first/last produced different month counts")


def test_hindsight_beats_every_real_rule() -> None:
    """The lookahead benchmark must dominate. If a real rule beats it, the
    real rule is itself leaking."""
    rng = np.random.default_rng(17)
    n = 252 * 12
    px = pd.Series(
        100 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, n))), index=bdays(n)
    )
    c = ctx_of(px, rate=0.04)
    sched, _ = acc.schedule(c.index, "dom", 12_000, day=1)
    best = acc.simulate(c, "EQ", sched, 0.0, TaxModel.none(), "hindsight")
    ceiling = float(best.equity.iloc[-1])
    for day in (1, 7, 15, 22, "last"):
        s2, _ = acc.schedule(c.index, "dom", 12_000, day=day)
        r = acc.simulate(c, "EQ", s2, 0.0, TaxModel.none(), "immediate")
        check(float(r.equity.iloc[-1]) <= ceiling * 1.0001,
              f"day {day} beat the perfect-hindsight ceiling — it is leaking")


# --- 6. placebo band ----------------------------------------------------


def test_placebo_band_calls_noise_noise() -> None:
    """Fed pure noise, the band must say NOISE rather than find a winner."""
    rng = np.random.default_rng(23)
    draws = list(rng.normal(10.0, 0.5, 400))
    observed = {str(i): float(rng.normal(10.0, 0.5)) for i in range(1, 29)}
    band = stats.placebo_band(observed, draws, n_variants=28)
    check("NOISE" in band.verdict(),
          f"placebo band found signal in pure noise: {band.verdict()}")

    # and given a genuinely separated winner it must NOT say NOISE
    observed["7"] = 10.0 + 6 * 0.5
    band2 = stats.placebo_band(observed, draws, n_variants=28)
    check("NOISE" not in band2.verdict(),
          f"placebo band missed a 6-sigma winner: {band2.verdict()}")


def main() -> None:
    tests = [
        test_repair,
        test_no_lookahead,
        test_seasonal_is_calendar_only,
        test_fifo_tax_split,
        test_costs_and_accrual,
        test_cash_only_earns_the_rate,
        test_buy_hold_tracks_the_index,
        test_band_suppresses_trades,
        test_xirr,
        test_same_money_every_variant,
        test_day_of_month_schedule,
        test_hindsight_beats_every_real_rule,
        test_placebo_band_calls_noise_noise,
    ]
    for t in tests:
        before = len(failures)
        try:
            t()
        except Exception as e:  # noqa: BLE001 — report, don't abort the suite
            failures.append(f"{t.__name__} raised {type(e).__name__}: {e}")
        mark = "ok  " if len(failures) == before else "FAIL"
        print(f"  {mark} {t.__name__}")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print(f"All {len(tests)} index-investing checks passed — no signal reads a "
          f"price it would trade at, repairs leave real crashes alone, and every "
          f"deployment rule contributes identical money.")


if __name__ == "__main__":
    main()
