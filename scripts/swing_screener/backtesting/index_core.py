"""The book: lots, cash, costs and taxes for index-investing backtests.

Separate from `portfolio_sim.py` because the two answer different
questions. That one simulates a *signal queue* — many candidates competing
for a capped number of slots, each with a stop. This one simulates an
*allocation*: a handful of index sleeves held at target weights, with
contributions arriving and tax falling due. Forcing either into the other's
shape would distort both.

Three things here are easy to get wrong and change conclusions:

1. **Cash earns something.** Any strategy that waits — dip-buying, a trend
   overlay, "wait for the crash" — is only fairly scored if the waiting
   money earns the T-bill/liquid-fund rate. At an implicit 0% those
   strategies pay a penalty no real investor pays.

2. **Tax is path-dependent, so it needs lots.** Whether a sale is taxed at
   20% or 12.5% depends on how long *that particular* lot was held, which
   a running average cost basis cannot tell you. Hence FIFO lots.

3. **Deferral is most of buy-and-hold's advantage.** A holder pays no tax
   for 30 years; a monthly rebalancer pays every year on the way. Comparing
   them without taxing the holder's terminal unrealised gain hands
   buy-and-hold a second, invisible subsidy — so terminal liquidation is
   modelled by default whenever tax is on.
"""

from collections import deque
from dataclasses import dataclass, field

import pandas as pd


# --- tax -----------------------------------------------------------------


@dataclass(frozen=True)
class TaxModel:
    """Realised-gains tax, paid from cash at fiscal year end.

    Rates are a stated assumption, not a fact about any individual: they
    depend on bracket, residency and account type. US numbers here are the
    common long/short retail case in a TAXABLE account — inside a 401k or
    IRA the right model is `TaxModel.none()`.
    """

    short_rate: float
    long_rate: float
    long_term_days: int
    fy_end_month: int
    fy_end_day: int
    annual_exemption: float = 0.0   # India's LTCG free allowance
    label: str = ""
    enabled: bool = True

    @staticmethod
    def none() -> "TaxModel":
        return TaxModel(0.0, 0.0, 365, 12, 31, 0.0, "no tax", enabled=False)

    @staticmethod
    def india() -> "TaxModel":
        # Post-July-2024 regime: STCG 20%, LTCG 12.5% above a Rs 1.25L
        # annual exemption, 12-month holding threshold, FY ending 31 March.
        return TaxModel(0.20, 0.125, 365, 3, 31, 125_000, "India equity (20%/12.5%)")

    @staticmethod
    def us() -> "TaxModel":
        # Taxable account, middle bracket: 15% long-term, 24% short-term.
        return TaxModel(0.24, 0.15, 366, 12, 31, 0.0, "US taxable (24%/15%)")

    def is_fy_end(self, day: pd.Timestamp, nxt: pd.Timestamp | None) -> bool:
        """True on the last trading day at or before the fiscal year end."""
        if nxt is None:
            return False
        boundary = pd.Timestamp(year=day.year, month=self.fy_end_month, day=self.fy_end_day)
        if day > boundary:
            boundary = pd.Timestamp(
                year=day.year + 1, month=self.fy_end_month, day=self.fy_end_day
            )
        return day <= boundary < nxt

    def due(self, short_gain: float, long_gain: float) -> float:
        """Tax on one fiscal year's realised gains.

        Losses offset gains within the year and then stop: carry-forward
        (8 years in India, indefinite in the US) is NOT modelled, which
        overstates the tax bill of any strategy that books losses in one
        year and gains in the next. Noted on every taxed run.
        """
        if not self.enabled:
            return 0.0
        total = short_gain + long_gain
        if total <= 0:
            return 0.0
        # Apply the exemption to the long-term slice first — the taxpayer's
        # own ordering, since it is the lower-rated bucket only in India
        # where the exemption exists at all.
        lg = max(0.0, long_gain - self.annual_exemption)
        sg = max(0.0, short_gain)
        return sg * self.short_rate + lg * self.long_rate


@dataclass
class _Lot:
    date: pd.Timestamp
    shares: float
    cost: float          # per share, including entry costs


@dataclass
class Trade:
    date: pd.Timestamp
    asset: str
    side: str
    shares: float
    price: float
    value: float
    costs: float
    reason: str = ""


@dataclass
class Result:
    equity: pd.Series
    cash: pd.Series
    exposure: pd.Series          # risk-asset value / equity
    weights: pd.DataFrame
    trades: pd.DataFrame
    cashflows: list[tuple[pd.Timestamp, float]] = field(default_factory=list)
    contributed: float = 0.0
    costs_paid: float = 0.0
    tax_paid: float = 0.0
    terminal_tax: float = 0.0
    caveats: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class Book:
    """Cash plus FIFO lots per asset, with costs and realised-gain tracking.

    Fractional units throughout. For index funds and ETFs this is how the
    instrument actually works (an SIP buys 3.47 units), and the integer
    rounding that matters for a Rs 900 stock is irrelevant here — the
    momentum baseline already showed integer floors silently dropping
    positions, which would be a far worse distortion in a contribution
    backtest where each instalment is small.
    """

    def __init__(self, cash: float, cost_bps: float, tax: TaxModel):
        self.cash = float(cash)
        self.cost_bps = cost_bps
        self.tax = tax
        self.lots: dict[str, deque[_Lot]] = {}
        self.trades: list[Trade] = []
        self.costs_paid = 0.0
        self.tax_paid = 0.0
        self.fy_short = 0.0
        self.fy_long = 0.0

    # --- valuation ---
    def shares(self, asset: str) -> float:
        return sum(l.shares for l in self.lots.get(asset, ()))

    def holdings_value(self, prices: dict[str, float]) -> float:
        return sum(
            self.shares(a) * prices[a]
            for a in self.lots
            if a in prices and prices[a] == prices[a]
        )

    def equity(self, prices: dict[str, float]) -> float:
        return self.cash + self.holdings_value(prices)

    def accrue(self, annual_rate: float, days: int = 1) -> None:
        """Interest on idle cash for `days` CALENDAR days.

        Calendar days, not trading days: cash earns over weekends and
        holidays. Accruing per bar at rate/252 silently pays only ~69% of
        the real interest, which penalises precisely the strategies this
        suite exists to test — dip-buying and trend overlays spend years in
        cash. It also makes the result depend on how many bars the vendor
        happened to print, which is not a fact about the strategy.
        """
        if annual_rate and annual_rate == annual_rate and self.cash > 0 and days > 0:
            self.cash *= (1.0 + annual_rate / 365.0) ** days

    # --- trading ---
    def buy(self, date, asset: str, cash_amount: float, price: float, reason: str = "") -> float:
        if cash_amount <= 0 or price <= 0 or price != price:
            return 0.0
        cash_amount = min(cash_amount, self.cash)
        if cash_amount <= 0:
            return 0.0
        cost = cash_amount * self.cost_bps / 10_000
        net = cash_amount - cost
        shares = net / price
        if shares <= 0:
            return 0.0
        self.cash -= cash_amount
        self.costs_paid += cost
        # Entry cost rides in the basis, which is both the tax treatment and
        # the only way R-free P&L stays honest.
        self.lots.setdefault(asset, deque()).append(
            _Lot(date, shares, cash_amount / shares)
        )
        self.trades.append(
            Trade(date, asset, "BUY", shares, price, cash_amount, cost, reason)
        )
        return shares

    def sell(self, date, asset: str, shares: float, price: float, reason: str = "") -> float:
        """Sell `shares` FIFO. Returns net proceeds added to cash."""
        have = self.shares(asset)
        shares = min(shares, have)
        if shares <= 1e-12 or price <= 0 or price != price:
            return 0.0
        gross = shares * price
        cost = gross * self.cost_bps / 10_000
        net = gross - cost
        self.cash += net
        self.costs_paid += cost

        # FIFO match, splitting gains into short/long by each lot's own age
        remaining = shares
        lots = self.lots[asset]
        exit_px = net / shares   # cost-of-exit inside the realised gain
        while remaining > 1e-12 and lots:
            lot = lots[0]
            take = min(lot.shares, remaining)
            gain = (exit_px - lot.cost) * take
            held = (date - lot.date).days
            if held >= self.tax.long_term_days:
                self.fy_long += gain
            else:
                self.fy_short += gain
            lot.shares -= take
            remaining -= take
            if lot.shares <= 1e-12:
                lots.popleft()
        if not lots:
            del self.lots[asset]
        self.trades.append(
            Trade(date, asset, "SELL", shares, price, gross, cost, reason)
        )
        return net

    def sell_value(self, date, asset: str, value: float, price: float, reason: str = "") -> float:
        if price <= 0 or price != price:
            return 0.0
        return self.sell(date, asset, value / price, price, reason)

    # --- tax ---
    def settle_fiscal_year(self, date, prices: dict[str, float]) -> float:
        """Pay the year's tax out of cash, liquidating pro-rata if short."""
        bill = self.tax.due(self.fy_short, self.fy_long)
        self.fy_short = self.fy_long = 0.0
        if bill <= 0:
            return 0.0
        if self.cash < bill:
            # Raising cash to pay tax itself realises gains. Those land in
            # the NEXT fiscal year here rather than compounding the current
            # bill — a simplification, and a small one: it only bites for a
            # fully-invested book, which by definition realises little.
            need = bill - self.cash
            held = self.holdings_value(prices)
            if held > 0:
                for asset in list(self.lots):
                    if asset not in prices:
                        continue
                    share = self.shares(asset) * prices[asset] / held
                    self.sell_value(date, asset, min(need * share * 1.02, self.shares(asset) * prices[asset]),
                                    prices[asset], "TAX_RAISE")
        paid = min(bill, max(self.cash, 0.0))
        self.cash -= paid
        self.tax_paid += paid
        return paid

    def terminal_tax(self, date, prices: dict[str, float]) -> float:
        """Tax on unrealised gains if everything were sold on the last day.

        Without this, a 30-year holder is compared against a rebalancer on
        a post-tax basis while never paying any tax — which is not a
        comparison, it is a head start.
        """
        if not self.tax.enabled:
            return 0.0
        short = long = 0.0
        for asset, lots in self.lots.items():
            px = prices.get(asset)
            if px is None or px != px:
                continue
            for lot in lots:
                gain = (px - lot.cost) * lot.shares
                if (date - lot.date).days >= self.tax.long_term_days:
                    long += gain
                else:
                    short += gain
        return self.tax.due(self.fy_short + short, self.fy_long + long)


# --- weight-driven driver ------------------------------------------------


def rebalance_to(
    book: Book, date, targets: dict[str, float], prices: dict[str, float],
    equity: float, band: float = 0.0, reason: str = "REBALANCE",
) -> None:
    """Trade the book toward `targets` (asset -> weight of equity).

    `band` implements threshold rebalancing: a sleeve is left alone while it
    is within `band` of its target in absolute weight. Sells run before
    buys so the cash exists.
    """
    tradable = {a: p for a, p in prices.items() if p and p == p}
    targets = {a: w for a, w in targets.items() if a in tradable}

    current = {a: book.shares(a) * tradable[a] for a in tradable}
    held_assets = set(a for a, v in current.items() if v > 1e-9)

    for asset in sorted(held_assets | set(targets)):
        if asset not in tradable:
            continue
        want = equity * targets.get(asset, 0.0)
        have = current.get(asset, 0.0)
        if have - want <= 1e-9:
            continue
        drift = abs(have - want) / equity if equity > 0 else 0.0
        if targets.get(asset, 0.0) > 0 and drift < band:
            continue
        book.sell_value(date, asset, have - want, tradable[asset], reason)

    for asset in sorted(targets):
        want = equity * targets[asset]
        have = book.shares(asset) * tradable[asset]
        if want - have <= 1e-9:
            continue
        drift = abs(want - have) / equity if equity > 0 else 0.0
        if have > 1e-9 and drift < band:
            continue
        book.buy(date, asset, min(want - have, book.cash), tradable[asset], reason)


def trades_frame(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(
            columns=["date", "asset", "side", "shares", "price", "value", "costs", "reason"]
        )
    return pd.DataFrame([t.__dict__ for t in trades])


def align(series: dict[str, pd.Series], start: str | None = None,
          end: str | None = None) -> tuple[pd.DatetimeIndex, dict[str, pd.Series]]:
    """Common calendar for a set of series: the INTERSECTION of their dates.

    Union-plus-ffill would invent prices on days a market was shut and let a
    strategy trade on them. The intersection costs a few days where the US
    and India calendars disagree and keeps every traded price real.
    """
    if not series:
        raise ValueError("no series to align")
    idx = None
    for s in series.values():
        idx = s.index if idx is None else idx.intersection(s.index)
    idx = pd.DatetimeIndex(sorted(idx))
    if start:
        idx = idx[idx >= pd.Timestamp(start)]
    if end:
        idx = idx[idx <= pd.Timestamp(end)]
    if len(idx) < 60:
        raise ValueError(
            f"only {len(idx)} overlapping trading days — check the series' start dates"
        )
    return idx, {k: v.reindex(idx) for k, v in series.items()}


# --- loading ------------------------------------------------------------


@dataclass
class Context:
    """Everything a run needs: a calendar, holdable series, a cash rate.

    `prices` are TOTAL-RETURN levels with expense ratios already deducted,
    so a strategy never has to remember to add dividends — getting that
    wrong once would silently bias every timing result in the suite.
    """

    market: str
    currency: str
    index: pd.DatetimeIndex
    prices: dict[str, pd.Series]
    cash_rate: pd.Series
    caveats: list[str] = field(default_factory=list)

    def px(self, date) -> dict[str, float]:
        return {a: float(s.loc[date]) for a, s in self.prices.items()
                if date in s.index and s.loc[date] == s.loc[date]}

    def slice(self, start=None, end=None) -> "Context":
        idx, prices = align(self.prices, start, end)
        return Context(self.market, self.currency, idx, prices,
                       self.cash_rate.reindex(idx).ffill(), list(self.caveats))


def load_context(
    market: str, assets: list[str], start: str | None = None,
    end: str | None = None, cash_rate: float | None = None,
) -> Context:
    from ..config import MARKETS
    from ..marketdata import index_data

    caveats: list[str] = []
    series: dict[str, pd.Series] = {}
    for key in assets:
        s, c = index_data.total_return_index(market, key)
        series[key] = s
        caveats.extend(c)

    idx, series = align(series, start, end)
    rate, rc = index_data.cash_rate_series(market, idx, override=cash_rate)
    caveats.extend(rc)
    return Context(
        market=market, currency=MARKETS[market].currency_symbol,
        index=idx, prices=series, cash_rate=rate, caveats=caveats,
    )
