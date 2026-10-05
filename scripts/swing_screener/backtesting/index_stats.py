"""Scoring index-investing runs — and the significance tests they need.

Two scoring regimes, because the two families ask different questions:

* An **allocation** run starts with a lump and is judged on CAGR, drawdown
  and risk-adjusted return — the existing conventions in `metrics.py`.

* An **accumulation** run has money flowing in every month, which makes
  CAGR on its equity curve meaningless: contribute more in later years and
  the "CAGR" falls even though nothing about the strategy changed. The
  right measure is money-weighted (XIRR), plus terminal wealth per unit
  contributed so two schedules of identical total size can be compared.

The third thing here matters most. Pick the best of 28 day-of-month
variants and you have run 28 experiments and reported the maximum, which is
roughly a 2-sigma draw even from pure noise. `placebo_band` generates the
null directly — randomise the contribution day, resample, and report where
the winner sits in that distribution. Without it, "the 7th is the best day"
is a number, not a finding.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import metrics

TRADING_DAYS = 252


# --- money-weighted return ----------------------------------------------


def xirr(cashflows: list[tuple[pd.Timestamp, float]], guess: float = 0.1) -> float:
    """Annualised internal rate of return for dated, irregular cashflows.

    Sign convention: contributions NEGATIVE (money leaving the investor),
    terminal value POSITIVE. Solved by bisection rather than Newton —
    slower and completely robust, which is the right trade for a few
    hundred flows.
    """
    if len(cashflows) < 2:
        return float("nan")
    t0 = cashflows[0][0]
    years = np.array([(d - t0).days / 365.25 for d, _ in cashflows])
    amts = np.array([a for _, a in cashflows], dtype=float)
    if not (amts > 0).any() or not (amts < 0).any():
        return float("nan")

    def npv(rate: float) -> float:
        if rate <= -0.9999:
            return float("inf")
        return float(np.sum(amts / (1.0 + rate) ** years))

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def rolling_worst(equity: pd.Series, years: int) -> tuple[float, float]:
    """(worst, median) annualised return over every `years`-long window.

    A single max-drawdown number says how bad one moment was. This says
    what a given holding period actually delivered at its worst — the
    figure that decides whether someone can hold the thing.
    """
    n = int(years * TRADING_DAYS)
    if len(equity) <= n:
        return float("nan"), float("nan")
    ratio = (equity.values[n:] / equity.values[:-n]) ** (1 / years) - 1
    return float(np.nanmin(ratio) * 100), float(np.nanmedian(ratio) * 100)


# --- summaries -----------------------------------------------------------


@dataclass
class AllocationStats:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp
    years: float
    cagr_pct: float
    total_return_pct: float
    max_dd_pct: float
    max_dd_days: int
    vol_pct: float
    sharpe: float
    sortino: float
    calmar: float
    exposure_pct: float
    turnover_annual: float
    trades: int
    costs_paid: float
    tax_paid: float
    terminal_tax: float
    after_tax_cagr_pct: float
    worst_1y_pct: float
    worst_3y_pct: float
    worst_10y_pct: float
    pct_months_up: float
    ending_equity: float
    starting_equity: float
    notes: list[str] = field(default_factory=list)

    def row(self) -> dict:
        return {
            "strategy": self.name, "years": round(self.years, 1),
            "cagr_pct": round(self.cagr_pct, 2),
            # after-tax figures are NOT filled in here: a taxed run's equity
            # curve is already net of tax paid along the way, so its "cagr"
            # is not a pre-tax number. index_investing runs each strategy
            # twice and merges the two columns.
            "max_dd_pct": round(self.max_dd_pct, 1),
            "dd_days": self.max_dd_days,
            "vol_pct": round(self.vol_pct, 1),
            "sharpe": round(self.sharpe, 2),
            "sortino": round(self.sortino, 2),
            "calmar": round(self.calmar, 2),
            "exposure_pct": round(self.exposure_pct, 1),
            "worst_1y_pct": round(self.worst_1y_pct, 1),
            "worst_3y_pct": round(self.worst_3y_pct, 1),
            "worst_10y_pct": round(self.worst_10y_pct, 1),
            "turnover_annual": round(self.turnover_annual, 2),
            "trades": self.trades,
            "costs_paid": round(self.costs_paid, 0),
            "ending_equity": round(self.ending_equity, 0),
        }


def summarize_allocation(name: str, res, notes: list[str] | None = None) -> AllocationStats:
    eq = res.equity.dropna()
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    total = (eq.iloc[-1] / eq.iloc[0] - 1) * 100
    cagr = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) * 100
    dd, dd_days = metrics.max_drawdown(eq)
    vol, sharpe, sortino = metrics.risk_stats(eq.pct_change())
    calmar = (cagr / abs(dd)) if dd else float("nan")

    # After tax, the terminal unrealised gain is settled too, so a holder and
    # a trader are compared on the same basis (see index_core.terminal_tax).
    after_tax_end = eq.iloc[-1] - res.terminal_tax
    after_tax_cagr = ((after_tax_end / eq.iloc[0]) ** (1 / years) - 1) * 100

    monthly = eq.resample("ME").last().pct_change().dropna()
    pct_up = float((monthly > 0).mean() * 100) if len(monthly) else float("nan")

    turnover = 0.0
    if not res.trades.empty and years > 0:
        turnover = float(res.trades["value"].sum()) / float(eq.mean()) / years

    w1, _ = rolling_worst(eq, 1)
    w3, _ = rolling_worst(eq, 3)
    w10, _ = rolling_worst(eq, 10)

    return AllocationStats(
        name=name, start=eq.index[0], end=eq.index[-1], years=years,
        cagr_pct=cagr, total_return_pct=total, max_dd_pct=dd, max_dd_days=dd_days,
        vol_pct=vol, sharpe=sharpe, sortino=sortino, calmar=calmar,
        exposure_pct=float(res.exposure.mean() * 100),
        turnover_annual=turnover, trades=int(len(res.trades)),
        costs_paid=res.costs_paid, tax_paid=res.tax_paid,
        terminal_tax=res.terminal_tax, after_tax_cagr_pct=after_tax_cagr,
        worst_1y_pct=w1, worst_3y_pct=w3, worst_10y_pct=w10,
        pct_months_up=pct_up, ending_equity=float(eq.iloc[-1]),
        starting_equity=float(eq.iloc[0]),
        notes=list(res.caveats) + list(notes or []),
    )


@dataclass
class AccumulationStats:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp
    years: float
    contributed: float
    terminal: float
    multiple: float               # terminal / contributed
    xirr_pct: float
    after_tax_terminal: float
    after_tax_xirr_pct: float
    max_dd_pct: float
    avg_cash_pct: float           # time-weighted share held in cash
    costs_paid: float
    tax_paid: float
    terminal_tax: float
    trades: int
    notes: list[str] = field(default_factory=list)

    def row(self) -> dict:
        return {
            "strategy": self.name, "years": round(self.years, 1),
            "contributed": round(self.contributed, 0),
            "terminal": round(self.terminal, 0),
            "multiple": round(self.multiple, 4),
            "xirr_pct": round(self.xirr_pct, 3),
            "max_dd_pct": round(self.max_dd_pct, 1),
            "avg_cash_pct": round(self.avg_cash_pct, 1),
            "costs_paid": round(self.costs_paid, 0),
            "trades": self.trades,
        }


def summarize_accumulation(name: str, res, notes: list[str] | None = None) -> AccumulationStats:
    eq = res.equity.dropna()
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    terminal = float(eq.iloc[-1])
    contributed = float(res.contributed)

    flows = [(d, -a) for d, a in res.cashflows]
    irr = xirr(flows + [(eq.index[-1], terminal)]) * 100
    after_tax_terminal = terminal - res.terminal_tax
    irr_at = xirr(flows + [(eq.index[-1], after_tax_terminal)]) * 100

    dd, _ = metrics.max_drawdown(eq)
    avg_cash = float((res.cash / res.equity.replace(0, np.nan)).mean() * 100)

    return AccumulationStats(
        name=name, start=eq.index[0], end=eq.index[-1], years=years,
        contributed=contributed, terminal=terminal,
        multiple=terminal / contributed if contributed else float("nan"),
        xirr_pct=irr, after_tax_terminal=after_tax_terminal,
        after_tax_xirr_pct=irr_at, max_dd_pct=dd, avg_cash_pct=avg_cash,
        costs_paid=res.costs_paid, tax_paid=res.tax_paid,
        terminal_tax=res.terminal_tax, trades=int(len(res.trades)),
        notes=list(res.caveats) + list(notes or []),
    )


# --- significance --------------------------------------------------------


@dataclass
class PlaceboBand:
    """The null distribution for a calendar-choice experiment."""

    n: int
    mean: float
    sd: float
    p05: float
    p50: float
    p95: float
    best_observed: float
    best_label: str
    z_of_best: float
    spread_observed: float
    spread_p95_null: float

    def details(self) -> list[str]:
        """Supporting numbers, as markdown bullets.

        `verdict()` + `details()` is the shared shape every object in a
        report's `extra` block implements, so the renderer never has to know
        which kind it is holding."""
        return [
            f"random-day null: median **{self.p50:.4f}**, 5-95th pct "
            f"**{self.p05:.4f} - {self.p95:.4f}**, sd {self.sd:.4f}",
            f"best fixed day: **{self.best_label}** at {self.best_observed:.4f} "
            f"({self.z_of_best:+.1f} sd)",
            f"observed best-worst spread **{self.spread_observed:.4f}** vs null "
            f"95th pct **{self.spread_p95_null:.4f}**",
        ]

    def verdict(self) -> str:
        """Plain reading of whether the winner cleared the noise.

        The spread test is the honest one: with 28 variants the MAXIMUM is
        selected on, so the question is not "is the best good?" but "is the
        best-to-worst gap wider than randomising the choice produces?".
        """
        if self.spread_observed <= self.spread_p95_null:
            return (
                f"NOISE — the best-to-worst spread ({self.spread_observed:.3f}) sits "
                f"inside the 95th percentile of the randomised null "
                f"({self.spread_p95_null:.3f}). No day beats any other."
            )
        if self.z_of_best < 2.0:
            return (
                f"WEAK — spread exceeds the null, but '{self.best_label}' is only "
                f"{self.z_of_best:.1f} sd above the random-day mean, and it was "
                f"selected as the max of {self.n} tries."
            )
        return (
            f"SIGNAL — '{self.best_label}' is {self.z_of_best:.1f} sd above the "
            f"random-day mean and the spread exceeds the randomised null. Still a "
            f"selected maximum: treat as a hypothesis, not a rule."
        )


def placebo_band(
    observed: dict[str, float], random_draws: list[float], n_variants: int,
) -> PlaceboBand:
    """Compare measured variants against a randomised-choice null.

    `random_draws` are outcomes from runs that picked the calendar slot at
    random each period. `observed` maps variant label -> outcome.
    """
    draws = np.array([d for d in random_draws if d == d], dtype=float)
    vals = np.array(list(observed.values()), dtype=float)
    best_label = max(observed, key=observed.get)
    best = float(observed[best_label])
    mean, sd = float(draws.mean()), float(draws.std(ddof=1))

    # Null for the SPREAD: resample n_variants random-day outcomes and take
    # max-min, repeatedly. This is what max-min looks like with no effect.
    rng = np.random.default_rng(7)
    spreads = [
        float(s.max() - s.min())
        for s in (rng.choice(draws, size=n_variants, replace=True) for _ in range(2000))
    ]

    return PlaceboBand(
        n=n_variants, mean=mean, sd=sd,
        p05=float(np.percentile(draws, 5)), p50=float(np.percentile(draws, 50)),
        p95=float(np.percentile(draws, 95)),
        best_observed=best, best_label=best_label,
        z_of_best=(best - mean) / sd if sd else float("nan"),
        spread_observed=float(vals.max() - vals.min()),
        spread_p95_null=float(np.percentile(spreads, 95)),
    )


def subwindow_table(
    runner, index: pd.DatetimeIndex, years: int = 10, step_years: int = 5,
) -> pd.DataFrame:
    """Re-run `runner(start, end)` over rolling sub-windows.

    A ranking that holds in 1993-2003, 2003-13 and 2013-26 is a finding; one
    that only holds on the full window is a fit to one path.
    """
    rows = []
    first, last = index[0], index[-1]
    cursor = first
    while cursor + pd.DateOffset(years=years) <= last:
        end = cursor + pd.DateOffset(years=years)
        try:
            rows.append({"window": f"{cursor.date()}..{end.date()}", **runner(cursor, end)})
        except Exception as e:  # noqa: BLE001 — a short window must not kill the sweep
            rows.append({"window": f"{cursor.date()}..{end.date()}", "error": str(e)[:60]})
        cursor = cursor + pd.DateOffset(years=step_years)
    return pd.DataFrame(rows)
