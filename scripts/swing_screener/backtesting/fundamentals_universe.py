"""The companies a backtest needs filings for: every stock it could have ranked, not today's liquid set.

The `financials` job fetches company data for the Fundamentals page -- today's most liquid stocks and
today's Stage-2 leaders. A backtest that requires fundamentals and reads only those is looking ahead: a
stock that led in 2020 and is illiquid now was never fetched, so it is "missing data", never eligible,
and its fall is never booked. Measured on quality_momentum (US, 2017-2021): 72 of the 102 names the
momentum baseline held and the fundamentals-filtered control did not had no filings fetched at all.

This module is the one definition of the set that closes that gap, read by three things that must not
disagree: the `financials_backfill` job (what to fetch), `tests/test_fundamentals_universe.py` (that it
was fetched) and a backtest's coverage report (`quality_momentum.QualityFilter`, how much of its ranked
pool was never fetched, rebalance by rebalance).

It does not fix survivorship in the PRICE universe: stocks delisted before today are not stored at all,
so they are in no backtest, with or without fundamentals.
"""

from ..config import MARKETS


def turnover_floor(market: str) -> float:
    """The lowest 20-session turnover floor any backtest ranks above in `market`: the screener's floor
    (the per-symbol strategies and momentum_baseline) or a portfolio strategy's own, whichever is lower --
    so the set covers every strategy's pool, momentum_vol_scaled's Rs 10 crore one included."""
    from ..strategies import portfolio_strategies
    floors = [MARKETS[market].screener.min_dollar_volume]
    for cls in portfolio_strategies().values():
        if hasattr(cls, "min_turnover_for"):
            floors.append(cls.min_turnover_for(market))
    return min(f for f in floors if f)


def symbols(market: str) -> list[str]:
    """Every stock that reached `turnover_floor` on some month-end since the optimise stage began."""
    from ..marketdata import universe
    return universe.liquid_ever(market, turnover_floor(market))


def never_fetched(market: str, syms) -> set[str]:
    """The stocks in `syms` the filings source has never been asked about (no `quarterly_fetch` row).
    A row with status 'none' (a fund, a foreign filer: nothing filed) counts as asked."""
    from ..marketdata import financials
    return set(syms) - set(financials.load_meta(market))
