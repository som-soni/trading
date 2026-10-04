"""Portfolio-level backtest: one capital pool, a position cap, and costs.

Why this exists
---------------
`backtest.backtest_symbol` simulates each symbol in isolation. That
implicitly assumes unlimited capital and zero costs, and it silently
answers a question nobody asked: "what if I could take every signal?"
Measured on the real signal set, the per-symbol backtest held an average
of 24 and a peak of 51 positions at once -- 51% of the account at risk
simultaneously, needing ~13x the stated capital at the position cap. Those
trades were not takeable, so their aggregate P&L was not achievable.

This module walks the calendar once, across all symbols together:

  for each trading day:
      1. mark open positions, exit any that hit stop or target
      2. fill resting buy-stops that triggered -- but only while a position
         slot and the cash for a full-size position are both available
      3. expire or cancel stale resting orders
      4. accept today's new signals as resting orders

Signals that arrive with no slot free are simply missed, exactly as they
would be in a real account. Sizing compounds off current equity rather
than a fixed notional, so gains and losses feed forward.

Costs are charged on both sides: slippage as basis points of notional
(a stand-in for spread and market impact) plus any per-order commission.
"""

import logging
from dataclasses import dataclass, field

import pandas as pd

from ..config.base import MarketConfig

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """An order the strategy wants to place, as of `date`."""
    date: pd.Timestamp
    symbol: str
    setup: str
    entry: float
    stop: float
    target: float
    decision: str
    quality: float = 0.0  # higher wins when more signals compete than slots


@dataclass
class ExitPolicy:
    """How an open position is managed.

    `bracket` is the strategy's own fixed stop+target. The others exist to
    test a specific hypothesis: a fixed measured-move target caps the right
    tail, and trend-following earns its return FROM that tail. Measured on
    the 2-year run, DY ran to +7.48R and the target closed it at +5.74R.

    Trailing modes deliberately keep the strategy's initial protective stop
    and only ever raise it, so a trade can still fail fast; what changes is
    that a winner is no longer forced out at a predetermined price.
    """
    mode: str = "bracket"        # bracket | trail_atr | ma | donchian
    use_target: bool = True      # False lets winners run indefinitely
    atr_mult: float = 3.0        # for trail_atr
    ma_col: str = "sma50"        # for ma
    donchian_bars: int = 50      # for donchian

    def label(self) -> str:
        bits = [self.mode]
        if self.mode == "trail_atr":
            bits.append(f"{self.atr_mult:g}ATR")
        elif self.mode == "ma":
            bits.append(self.ma_col)
        elif self.mode == "donchian":
            bits.append(f"{self.donchian_bars}d")
        bits.append("withTarget" if self.use_target else "noTarget")
        return "-".join(bits)


@dataclass
class PortfolioTrade:
    symbol: str
    setup: str
    decision: str
    entry_date: pd.Timestamp
    entry_price: float   # net of slippage
    stop: float
    target: float
    shares: int
    exit_date: pd.Timestamp | None = None
    exit_reason: str = "OPEN"
    exit_price: float = float("nan")
    costs: float = 0.0
    peak_close: float = float("nan")   # highest close seen since entry (trailing)
    # `stop` moves when a trailing policy ratchets it. R is by definition
    # measured against the risk accepted AT ENTRY, so the initial stop has to
    # be kept -- dividing by the live stop yields negative or NaN risk once
    # the trail passes entry, which silently scored every trailed winner as
    # a loss (0% win rate alongside a positive CAGR).
    initial_stop: float = float("nan")

    @property
    def notional(self) -> float:
        return self.entry_price * self.shares

    @property
    def pnl(self) -> float:
        if self.exit_price != self.exit_price:
            return float("nan")
        return (self.exit_price - self.entry_price) * self.shares - self.costs

    @property
    def r_multiple(self) -> float:
        base = self.initial_stop if self.initial_stop == self.initial_stop else self.stop
        risk = (self.entry_price - base) * self.shares
        return self.pnl / risk if risk > 0 else float("nan")

    @property
    def holding_days(self) -> int:
        if self.exit_date is None:
            return 0
        return (self.exit_date - self.entry_date).days


@dataclass
class PortfolioResult:
    equity: pd.Series
    positions_open: pd.Series
    cash: pd.Series
    trades: list[PortfolioTrade] = field(default_factory=list)
    costs_paid: float = 0.0
    signals_seen: int = 0
    signals_taken: int = 0
    signals_missed_no_slot: int = 0
    signals_missed_no_cash: int = 0
    partial_fills: int = 0


PENDING_EXPIRY_BDAYS = 10


def _slip(price: float, bps: float, side: str) -> float:
    """Buys fill a touch higher, sells a touch lower."""
    adj = bps / 10_000.0
    return price * (1 + adj) if side == "buy" else price * (1 - adj)


def simulate(
    signals: list[Signal],
    prices: dict[str, pd.DataFrame],
    cfg: MarketConfig,
    start: pd.Timestamp,
    end: pd.Timestamp | None = None,
    max_positions: int | None = None,
    exit_policy: ExitPolicy | None = None,
) -> PortfolioResult:
    """Walk every trading day once, with one shared pool of capital."""
    cap = max_positions if max_positions is not None else cfg.max_open_positions
    policy = exit_policy or ExitPolicy()

    # the calendar is the union of the dates of every symbol we might trade
    all_dates = sorted({d for df in prices.values() for d in df.index if d >= start})
    if end is not None:
        all_dates = [d for d in all_dates if d <= end]
    if not all_dates:
        raise ValueError("no trading dates in range")

    by_date: dict[pd.Timestamp, list[Signal]] = {}
    for s in signals:
        by_date.setdefault(s.date, []).append(s)

    cash = float(cfg.account_size)
    positions: dict[str, PortfolioTrade] = {}
    pending: dict[str, dict] = {}
    closed: list[PortfolioTrade] = []
    costs_total = 0.0
    taken = missed_slot = missed_cash = partial_fills = 0

    eq_rows, pos_rows, cash_rows = [], [], []

    for today in all_dates:
        # ---- 1. exits ----------------------------------------------------
        for sym, pos in list(positions.items()):
            df = prices.get(sym)
            if df is None or today not in df.index:
                continue
            bar = df.loc[today]

            hit_stop = bar["low"] <= pos.stop
            hit_target = policy.use_target and bar["high"] >= pos.target
            trend_break = False
            if not hit_stop and not hit_target and policy.mode in ("ma", "donchian"):
                # trend-failure exits act on the CLOSE, so they are evaluated
                # only once the bar is complete -- no intrabar clairvoyance
                if policy.mode == "ma":
                    ma = bar.get(policy.ma_col, float("nan"))
                    trend_break = ma == ma and float(bar["close"]) < float(ma)
                else:
                    hist = df.loc[:today, "low"]
                    if len(hist) > policy.donchian_bars:
                        floor_ = float(hist.iloc[-(policy.donchian_bars + 1) : -1].min())
                        trend_break = float(bar["close"]) < floor_

            if not (hit_stop or hit_target or trend_break):
                # nothing exited: ratchet the trailing stop upward for tomorrow
                c = float(bar["close"])
                pos.peak_close = c if pos.peak_close != pos.peak_close else max(pos.peak_close, c)
                if policy.mode == "trail_atr":
                    atr = bar.get("atr14", float("nan"))
                    if atr == atr and atr:
                        pos.stop = max(pos.stop, pos.peak_close - policy.atr_mult * float(atr))
                continue

            if hit_stop:  # conservative: the stop wins a same-bar tie
                raw = min(pos.stop, float(bar["open"]))  # gap-through fills at the open
                reason = "STOP"
            elif hit_target:
                raw = max(pos.target, float(bar["open"]))
                reason = "TARGET"
            else:
                raw = float(bar["close"])  # trend-failure exit, at the close
                reason = "TREND_EXIT"
            fill = _slip(raw, cfg.slippage_bps, "sell")
            # slippage is embedded in the fill price, so it has to be counted
            # explicitly or the reported cost total understates what was paid
            exit_cost = cfg.commission_per_order + (raw - fill) * pos.shares
            pos.exit_date, pos.exit_reason, pos.exit_price = today, reason, fill
            pos.costs += exit_cost
            costs_total += exit_cost
            cash += fill * pos.shares - exit_cost
            closed.append(pos)
            del positions[sym]

        # ---- 2. resting buy-stops ----------------------------------------
        # Rank the ones that triggered today, because slots are scarce.
        triggered = []
        for sym, order in list(pending.items()):
            df = prices.get(sym)
            if df is None or today not in df.index:
                continue
            bar = df.loc[today]
            if today > order["expires"]:
                del pending[sym]
                continue
            if bar["high"] >= order["entry"]:
                triggered.append((sym, order, bar))
            elif bar["low"] <= order["stop"]:
                del pending[sym]  # fell away before ever filling

        triggered.sort(key=lambda t: t[1]["quality"], reverse=True)
        for sym, order, bar in triggered:
            if sym in positions:
                del pending[sym]
                continue
            if len(positions) >= cap:
                missed_slot += 1
                continue  # keep it resting; a slot may free up before it expires

            raw_entry = max(order["entry"], float(bar["open"]))  # gap fills worse
            if raw_entry >= order["target"]:
                del pending[sym]  # gapped past the whole reward
                continue
            entry = _slip(raw_entry, cfg.slippage_bps, "buy")
            risk_per_share = entry - order["stop"]
            if risk_per_share <= 0:
                del pending[sym]
                continue

            equity_now = cash + sum(
                _mark(p, prices, today) for p in positions.values()
            )
            risk_budget = equity_now * cfg.risk_pct
            shares = int(risk_budget // risk_per_share)
            max_notional = equity_now * cfg.max_position_pct
            if shares * entry > max_notional:
                shares = int(max_notional // entry)
            # Scale down to what cash allows rather than declining outright.
            # A trader who can afford 70% of target size buys 70%; they do not
            # skip the breakout. Under-filling puts LESS than risk_pct at risk
            # on that position, never more, so this cannot inflate leverage --
            # it only stops a fully-invested book from being deaf for months.
            affordable = int((cash - cfg.commission_per_order) // entry)
            if affordable < shares:
                shares = affordable
                partial_fills += 1
            # computed after the final share count, not before
            cost = cfg.commission_per_order + (entry - raw_entry) * shares
            if shares < 1:
                missed_cash += 1
                del pending[sym]
                continue

            cash -= shares * entry + cfg.commission_per_order
            costs_total += cost
            positions[sym] = PortfolioTrade(
                symbol=sym, setup=order["setup"], decision=order["decision"],
                entry_date=today, entry_price=entry, stop=order["stop"],
                initial_stop=order["stop"],
                target=order["target"], shares=shares, costs=cost,
            )
            taken += 1
            del pending[sym]

        # ---- 3. today's new signals become resting orders ----------------
        for s in by_date.get(today, []):
            if s.symbol in positions or s.symbol in pending:
                continue
            pending[s.symbol] = {
                "entry": s.entry, "stop": s.stop, "target": s.target,
                "setup": s.setup, "decision": s.decision, "quality": s.quality,
                "expires": today + pd.tseries.offsets.BDay(PENDING_EXPIRY_BDAYS),
            }

        # ---- 4. mark to market -------------------------------------------
        held = sum(_mark(p, prices, today) for p in positions.values())
        eq_rows.append(cash + held)
        pos_rows.append(len(positions))
        cash_rows.append(cash)

    # anything still open is marked at the final close
    last = all_dates[-1]
    for sym, pos in positions.items():
        df = prices.get(sym)
        if df is not None and len(df.loc[:last]):
            pos.exit_date = last
            pos.exit_reason = "OPEN"
            pos.exit_price = float(df.loc[:last, "close"].iloc[-1])
        closed.append(pos)

    idx = pd.DatetimeIndex(all_dates)
    return PortfolioResult(
        equity=pd.Series(eq_rows, index=idx),
        positions_open=pd.Series(pos_rows, index=idx),
        cash=pd.Series(cash_rows, index=idx),
        trades=closed, costs_paid=costs_total,
        signals_seen=len(signals), signals_taken=taken,
        signals_missed_no_slot=missed_slot, signals_missed_no_cash=missed_cash,
        partial_fills=partial_fills,
    )


def _mark(pos: PortfolioTrade, prices: dict[str, pd.DataFrame], today: pd.Timestamp) -> float:
    df = prices.get(pos.symbol)
    if df is None:
        return pos.entry_price * pos.shares
    upto = df.loc[:today, "close"]
    price = float(upto.iloc[-1]) if len(upto) else pos.entry_price
    return price * pos.shares


def trades_to_df(trades: list[PortfolioTrade]) -> pd.DataFrame:
    rows = [
        {
            "symbol": t.symbol, "setup": t.setup, "decision": t.decision,
            "entry_date": t.entry_date.date(), "entry_price": round(t.entry_price, 4),
            "stop": round(t.stop, 4),
            "initial_stop": round(t.initial_stop, 4) if t.initial_stop == t.initial_stop else None,
            "target": round(t.target, 4), "shares": t.shares,
            "exit_date": t.exit_date.date() if t.exit_date is not None else None,
            "exit_reason": t.exit_reason, "exit_price": round(t.exit_price, 4),
            "notional": round(t.notional, 2), "costs": round(t.costs, 2),
            "pnl": round(t.pnl, 2), "r_multiple": round(t.r_multiple, 3),
            "holding_days": t.holding_days,
        }
        for t in trades
    ]
    cols = [
        "symbol", "setup", "decision", "entry_date", "entry_price", "stop",
        "initial_stop", "target",
        "shares", "exit_date", "exit_reason", "exit_price", "notional", "costs",
        "pnl", "r_multiple", "holding_days",
    ]
    return pd.DataFrame(rows, columns=cols)
