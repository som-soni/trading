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
(a stand-in for spread and market impact) plus any per-order commission,
plus (optionally) `cost_bps` of notional for statutory charges and brokerage.
Each cost is charged once: slippage lives inside the fill prices, so a trade's
pnl and the cash it returns both exclude it a second time (until 2026-10 the
exit path deducted exit slippage from cash twice, understating every result by
a few basis points per trade).

Spec mode (research/minervini-backtest-spec.md)
-----------------------------------------------
A signal may carry `meta`, which changes how ITS order behaves; a signal
without meta behaves exactly as before:

  order="open"        fill at the next session's open (EN-01), one day only;
                      skipped if that open is above `max_fill` or at or below
                      `min_open` (the tight low)
  max_fill            skip a fill above this price (buy range, 1.05 × pivot)
  cancel_close_below  cancel a resting buy-stop on a close below this
  max_risk_pct        skip a fill whose risk (fill − stop) / fill exceeds this (SL-03)
  base_id             one entry per base (EN-04): a base that was entered once is not entered again
  adv                 50-day average traded value, for the `max_adv_pct` cap (SL-06)
  slippage_bps        this order's slippage (and its exits'), overriding the market's
  min_breakout_vol    sell at the next open if the fill day's volume is under this × its 50-day average
  pivot, rs, tightness  carried on the trade for exits and reports

and the "minervini" exit mode runs the strategy's EX-01 … EX-07 (see ExitPolicy).
Exits that act on a close (EX-02, EX-05, EX-06, EX-07, a light-volume fill) are
queued and fill at the next session's open; the stop (EX-01) fills during the
day, at the open if the stock gapped through it. A partial sale (EX-04, and a
climax when `climax_partial`) is folded into the trade's single row:
`exit_price` is the blended price of every share sold.
"""

import logging
import math
from dataclasses import dataclass, field

import pandas as pd

from ..config.base import MarketConfig
from ..strategies import minervini_spec as _ms

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
    meta: dict = field(default_factory=dict)   # spec-mode order details (module docstring)


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
    mode: str = "bracket"        # bracket | trail_atr | ma | donchian | minervini
    use_target: bool = True      # False lets winners run indefinitely
    atr_mult: float = 3.0        # for trail_atr
    ma_col: str = "sma50"        # for ma, and minervini's EX-06
    donchian_bars: int = 50      # for donchian
    # ---- minervini: the strategy's exit ladder. Defaults are minervini_spec's constants, so a
    # --spec run trades the strategy's documented numbers (1.8: the SEPA Learn guide's).
    fail_days: int = _ms.FAIL_DAYS              # EX-02: a close below the pivot within this many sessions of entry (0 = off)
    breakeven_r: float = _ms.BREAKEVEN_R        # EX-03: stop to entry + round-trip costs once the high reaches entry + this × R (0 = off)
    partial_r: float = 0.0                      # EX-04 (1.7): sell `partial_frac` at entry + this × R (0 = off)
    partial_frac: float = _ms.STRENGTH_FRAC
    strength_ext: float = _ms.STRENGTH_EXT_PCT / 100   # EX-04: sell `partial_frac` at the next open once the close is
                                                #   this far above `ma_col` (0 = off)
    climax: bool = True          # EX-05
    climax_partial: bool = bool(_ms.CLIMAX_IS_PARTIAL)  # a climax sells `partial_frac` (if not yet sold), not everything
    climax_gain: float = 0.25    #   only once the position is up this much
    climax_up_days: int = 8      #   … at least this many up closes in the last 10
    climax_ext_200: float = 0.70 #   … close this far above SMA200
    climax_gap: float = 0.03     #   … a gap up this large after a rise of `climax_gap_after`
    climax_gap_after: float = 0.50
    trend_volume: bool = bool(_ms.TREND_EXIT_NEEDS_VOLUME)  # EX-06 needs volume ≥ its 50-day average
    time_stop_days: int = _ms.TIME_STOP_DAYS    # EX-07: sold if the high has not reached +1R within this many sessions (0 = off)
    # ---- trade management for the other modes (bracket, trail_atr, ma, donchian). All off by default,
    # so a run without them trades exactly as before. `minervini` has its own ladder above and ignores these.
    be_r: float = 0.0            # stop to entry + round-trip costs once the HIGH reaches entry + this × R;
                                 #   effective from the next session (0 = off)
    time_stop_bars: int = 0      # sold at the close of the Nth session after the entry session (0 = off)
    time_stop_mult: float = 0.0  # … N = this × the setup's duration in bars, when the signal carries
                                 #   meta["setup_start"]; otherwise time_stop_bars (0 = off)
    partial_at_target: float = 0.0   # sell this fraction at the target; the rest drops the target and
                                     #   trails atr_mult × ATR14 under its highest close (0 = off)

    @property
    def managed(self) -> bool:
        """Whether any of the opt-in trade-management rules is on (non-minervini modes)."""
        return self.mode != "minervini" and bool(
            self.be_r or self.time_stop_bars or self.time_stop_mult or self.partial_at_target)

    def label(self) -> str:
        bits = [self.mode]
        if self.mode == "minervini":
            bits.append(self.ma_col)
            if self.partial_r:
                bits.append(f"partial{self.partial_r:g}R")
            if self.strength_ext != _ms.STRENGTH_EXT_PCT / 100:
                bits.append(f"strength{self.strength_ext * 100:g}" if self.strength_ext else "noStrength")
            if self.fail_days != _ms.FAIL_DAYS:
                bits.append(f"fail{self.fail_days}" if self.fail_days else "noFail")
            if self.time_stop_days != _ms.TIME_STOP_DAYS:
                bits.append(f"time{self.time_stop_days}" if self.time_stop_days else "noTime")
            return "-".join(bits)
        if self.mode == "trail_atr":
            bits.append(f"{self.atr_mult:g}ATR")
        elif self.mode == "ma":
            bits.append(self.ma_col)
        elif self.mode == "donchian":
            bits.append(f"{self.donchian_bars}d")
        bits.append("withTarget" if self.use_target else "noTarget")
        if self.be_r:
            bits.append(f"be{self.be_r:g}R")
        if self.time_stop_mult:
            bits.append(f"time{self.time_stop_mult:g}x" + (f"or{self.time_stop_bars}" if self.time_stop_bars else ""))
        elif self.time_stop_bars:
            bits.append(f"time{self.time_stop_bars}")
        if self.partial_at_target:
            bits.append(f"partial{self.partial_at_target:g}atT")
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
    # spec mode
    meta: dict = field(default_factory=dict)
    open_shares: int = -1          # shares still held (-1 = all of them)
    sold_value: float = 0.0        # proceeds of shares already sold (partial exit), before costs
    partial_shares: int = 0
    bars_held: int = 0
    queued_exit: str = ""          # a close-based exit to fill at the next open
    # Slippage is already inside entry_price / exit_price. `costs` reports it (with commission and
    # charges) as what the trade paid, so pnl subtracts `costs - slippage`: every cost counted once.
    slippage: float = 0.0
    # Pyramiding. `entry_price` becomes the share-weighted average cost as tranches
    # are added, which keeps both pnl and r_multiple correct without special-casing:
    # sum((entry_i - stop) * shares_i) == (avg_entry - stop) * total_shares.
    target_shares: int = 0         # full intended size; 0 when not pyramiding
    add_price: float = float("nan")  # resting buy-stop for the remaining tranche
    adds: int = 0

    @property
    def held(self) -> int:
        return self.shares if self.open_shares < 0 else self.open_shares

    @property
    def notional(self) -> float:
        return self.entry_price * self.shares

    @property
    def pnl(self) -> float:
        if self.exit_price != self.exit_price:
            return float("nan")
        return (self.exit_price - self.entry_price) * self.shares - (self.costs - self.slippage)

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
    skipped: dict = field(default_factory=dict)   # spec-mode skips by reason (gap, risk, base, adv, open_risk)


PENDING_EXPIRY_BDAYS = 10


def _slip(price: float, bps: float, side: str) -> float:
    """Buys fill a touch higher, sells a touch lower."""
    adj = bps / 10_000.0
    return price * (1 + adj) if side == "buy" else price * (1 - adj)


@dataclass
class Exposure:
    """PE-01…PE-04: size the next entry from how the last few trades went.

    Minervini does not risk the same fraction every time. He opens at a pilot size,
    and only pays full size once the account is making money — so a losing streak
    costs progressively less and a winning one is pressed. The point is drawdown,
    not return: the same trades taken in the same order should end in a similar
    place having fallen less far along the way.

    The state is deliberately read ONCE at the top of each session, before that day's
    exits, so a trade closing this morning cannot resize a fill this afternoon. Every
    input is therefore a trade that closed on an earlier session.

    `press` (PE-04) is off unless press_net_r is set.
    """

    enabled: bool = False
    window: int = 10             # PE-01: closed trades in the rolling window
    warmup: int = 5              # PE-02: pilot size until this many trades have closed
    pilot_frac: float = 0.5      # PE-02: fraction of risk_pct while the window is not paying
    press_net_r: float | None = None   # PE-04: net R over the window that unlocks the press
    press_frac: float = 1.25     # PE-04: fraction of risk_pct when pressing
    press_slots: int = 2         # PE-04: extra concurrent positions when pressing

    def state(self, closed: list) -> tuple[float, int, str]:
        """(risk multiplier, extra slots, why) from the trades closed before today."""
        if not self.enabled:
            return 1.0, 0, "flat"
        window = [t for t in closed[-self.window:] if t.r_multiple is not None]
        net_r = sum(t.r_multiple for t in window)
        last_two = [t for t in closed[-2:] if t.r_multiple is not None]
        two_losses = len(last_two) == 2 and all(t.r_multiple < 0 for t in last_two)
        if len(closed) < self.warmup:
            return self.pilot_frac, 0, "pilot: warming up"
        if two_losses:
            return self.pilot_frac, 0, "pilot: two losses in a row"
        if net_r <= 0:
            return self.pilot_frac, 0, f"pilot: net {net_r:+.1f}R over the last {len(window)}"
        if self.press_net_r is not None and net_r >= self.press_net_r:
            return self.press_frac, self.press_slots, f"press: net {net_r:+.1f}R"
        return 1.0, 0, f"full: net {net_r:+.1f}R"


_FLAT = Exposure()   # disabled: every entry risks the full risk_pct


def simulate(
    signals: list[Signal],
    prices: dict[str, pd.DataFrame],
    cfg: MarketConfig,
    start: pd.Timestamp,
    end: pd.Timestamp | None = None,
    max_positions: int | None = None,
    exit_policy: ExitPolicy | None = None,
    cost_bps: float = 0.0,
    slippage_bps: float | None = None,
    max_open_risk_pct: float | None = None,
    exposure: "Exposure | None" = None,
    regime_ok: "pd.Series | None" = None,
    max_adv_pct: float | None = None,
    pyramid_frac: float | None = None,
    pyramid_add_pct: float = 2.0,
) -> PortfolioResult:
    """Walk every trading day once, with one shared pool of capital.

    `cost_bps` is charged on every fill's notional (statutory charges and brokerage, C-01);
    `slippage_bps` overrides the market's; `max_open_risk_pct` caps the open risk across positions
    — (price − stop) × shares, summed — as a share of equity (PF-04); `max_adv_pct` skips an order
    worth more than this share of the stock's 50-day average traded value (SL-06, needs meta["adv"]).

    `pyramid_frac` builds the position in two tranches instead of one: take this
    fraction of full size at entry and rest a buy-stop `pyramid_add_pct` above it
    for the remainder. Minervini adds into strength and never into weakness, and
    the binding constraint is average cost -- the stop comes from the base, not
    from what he paid, so an add that lifts the average far above the pivot widens
    the loss if he is wrong. The add is therefore refused above meta["max_fill"],
    the same buy-range ceiling the initial entry respects, and refused once any
    partial profit has been taken. None or 1.0 keeps the old single-tranche fill."""
    cap = max_positions if max_positions is not None else cfg.max_open_positions
    policy = exit_policy or ExitPolicy()
    base_slip = cfg.slippage_bps if slippage_bps is None else slippage_bps
    fee_rate = cost_bps / 10_000.0

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
    skipped: dict[str, int] = {}
    bases_entered: set = set()

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    def sell(pos: PortfolioTrade, raw: float, n: int, today) -> float:
        """Sell n shares at raw (before slippage). Cash receives the slipped fill less commission and
        charges — the slippage is inside the fill, so it is not deducted again (it is still reported in
        `costs`)."""
        nonlocal cash, costs_total
        fill = _slip(raw, pos.meta.get("slippage_bps", base_slip), "sell")
        cost = cfg.commission_per_order + (raw - fill) * n + fill * n * fee_rate
        pos.costs += cost
        pos.slippage += (raw - fill) * n
        costs_total += cost
        cash += fill * n - cfg.commission_per_order - fill * n * fee_rate
        pos.sold_value += fill * n
        pos.open_shares = pos.held - n
        return fill

    def close_out(sym: str, pos: PortfolioTrade, raw: float, reason: str, today) -> None:
        fill = sell(pos, raw, pos.held, today)
        pos.exit_date, pos.exit_reason = today, reason
        # blended over any partial sale; exactly the fill when there was none
        pos.exit_price = pos.sold_value / pos.shares if pos.partial_shares else fill
        closed.append(pos)
        del positions[sym]

    eq_rows, pos_rows, cash_rows = [], [], []

    for today in all_dates:
        # ---- progressive exposure: fixed for the whole session, computed from trades
        # that closed on EARLIER sessions. Reading it here rather than at the fill is
        # the whole point — today's stop-out must not resize today's entry.
        risk_mult, extra_slots, exposure_why = (exposure or _FLAT).state(closed)
        risk_pct_today = cfg.risk_pct * risk_mult
        slots_today = cap + extra_slots

        # ---- 0. pyramid adds, before exits so a position that is added to and
        # then stopped on the same bar pays for both, which is what would happen
        # ----------------------------------------------------------------------
        for sym, pos in list(positions.items()):
            if not pos.target_shares or pos.shares >= pos.target_shares or pos.partial_shares:
                continue
            df = prices.get(sym)
            if df is None or today not in df.index or today == pos.entry_date:
                continue
            bar = df.loc[today]
            if not (float(bar["high"]) >= pos.add_price):
                continue
            fill = max(pos.add_price, float(bar["open"]))        # a gap fills worse
            ceiling = pos.meta.get("max_fill")
            if ceiling is not None and fill > float(ceiling):
                skip("add would lift the average cost past the buy range")
                pos.target_shares = 0
                continue
            want = pos.target_shares - pos.shares
            fill_slipped = _slip(fill, pos.meta.get("slippage_bps", base_slip), "buy")
            affordable = int((cash - cfg.commission_per_order) // (fill_slipped * (1 + fee_rate)))
            add_n = min(want, max(0, affordable))
            if add_n < 1:
                skip("not enough cash to add")
                pos.target_shares = 0
                continue
            fee = fill_slipped * add_n * fee_rate
            extra = cfg.commission_per_order + (fill_slipped - fill) * add_n + fee
            cash -= add_n * fill_slipped + cfg.commission_per_order + fee
            costs_total += extra
            # share-weighted average cost keeps pnl and r_multiple correct
            pos.entry_price = ((pos.entry_price * pos.shares + fill_slipped * add_n)
                               / (pos.shares + add_n))
            pos.shares += add_n
            pos.costs += extra
            pos.slippage += (fill_slipped - fill) * add_n
            pos.adds += 1
            if pos.shares >= pos.target_shares:
                pos.target_shares = 0

        # ---- 1. exits ----------------------------------------------------
        for sym, pos in list(positions.items()):
            df = prices.get(sym)
            if df is None or today not in df.index:
                continue
            bar = df.loc[today]

            if policy.mode == "minervini":
                _manage_minervini(sym, pos, df, bar, today, policy, close_out, sell, fee_rate, cfg)
                continue

            if policy.managed:
                _manage_bracket(sym, pos, df, bar, today, policy, close_out, sell, fee_rate, cfg)
                continue

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
            close_out(sym, pos, raw, reason, today)

        # ---- 2. resting orders -------------------------------------------
        # PF-06 / MKT-01: in risk-off, nothing new is bought. Signals are already
        # filtered out before the simulation, but an order placed while the market
        # was open can still be resting when it closes, and filling it would buy a
        # breakout the regime rule says to refuse. The filter never forces an exit,
        # so open positions above are untouched.
        if regime_ok is not None and not bool(regime_ok.asof(today)):
            for sym in list(pending):
                skip("cancelled: market filter is risk-off")
                del pending[sym]

        # Rank the ones that triggered today, because slots are scarce.
        triggered = []
        for sym, order in list(pending.items()):
            df = prices.get(sym)
            if df is None or today not in df.index:
                continue
            bar = df.loc[today]
            meta = order["meta"]
            if meta.get("order") == "open":
                # EN-01: the next session's open, that day only
                o = float(bar["open"])
                if o > meta.get("max_fill", math.inf):
                    skip("gapped above the buy range")
                    del pending[sym]
                elif o <= meta.get("min_open", -math.inf):
                    skip("opened at or below the tight low")
                    del pending[sym]
                else:
                    triggered.append((sym, order, bar))
                continue
            if today > order["expires"]:
                skip("the resting order expired unfilled")
                del pending[sym]
                continue
            if bar["high"] >= order["entry"]:
                # A resting buy-stop fills on any intraday poke. When the signal asks
                # for confirmation, a bar that pokes through and closes back below the
                # level is not a breakout -- it is the thing the failed-breakout exit
                # then sells at the next open, for a guaranteed small loss. Measured on
                # India, 9 of 14 trades filled that way and 11 exited FAILED_BREAKOUT
                # with a median hold of one day. Leave the order resting instead; the
                # base is intact until it closes below the tight low.
                lvl = meta.get("confirm_close_above")
                if lvl is not None and float(bar["close"]) < float(lvl):
                    skip("poked through the pivot but closed back below it")
                else:
                    triggered.append((sym, order, bar))
            elif bar["low"] <= order["stop"]:
                del pending[sym]  # fell away before ever filling
            elif float(bar["close"]) < meta.get("cancel_close_below", -math.inf):
                del pending[sym]  # closed below the tight low: the setup is gone

        triggered.sort(key=lambda t: t[1]["quality"], reverse=True)
        for sym, order, bar in triggered:
            meta = order["meta"]
            if sym in positions:
                del pending[sym]
                continue
            if len(positions) >= slots_today:
                missed_slot += 1
                if meta.get("order") == "open":
                    del pending[sym]
                continue  # keep it resting; a slot may free up before it expires

            if meta.get("order") == "open":
                raw_entry = float(bar["open"])
            elif meta.get("confirm_close_above") is not None:
                # the close is what confirmed it, so the close is what you can pay:
                # filling at the intraday stop price would be buying on information
                # (how the bar closed) that did not exist at the moment of the touch
                raw_entry = max(order["entry"], float(bar["close"]))
            else:
                raw_entry = max(order["entry"], float(bar["open"]))  # gap fills worse
            if "max_fill" in meta:
                if raw_entry > meta["max_fill"]:
                    skip("gapped above the buy range")
                    del pending[sym]
                    continue
            elif raw_entry >= order["target"]:
                skip("gapped past the whole reward")
                del pending[sym]
                continue
            if meta.get("base_id") is not None and (sym, meta["base_id"]) in bases_entered:
                skip("base already entered")
                del pending[sym]
                continue
            slip = meta.get("slippage_bps", base_slip)
            entry = _slip(raw_entry, slip, "buy")
            risk_per_share = entry - order["stop"]
            if risk_per_share <= 0:
                skip("fill at or below the stop")
                del pending[sym]
                continue
            if risk_per_share / entry > meta.get("max_risk_pct", math.inf):
                skip("stop too far below the fill")
                del pending[sym]
                continue
            # The reward-to-risk minimum was tested on the signal bar's CLOSE, but the order
            # fills at the next open. An overnight gap up moves the entry without moving the
            # stop or the target, so it shortens the reward and lengthens the risk at once: a
            # plan that cleared the minimum on the close can be bought at less than it. The
            # strategy's own number, re-tested on the price actually paid -- the same shape as
            # the two checks above, which also re-test a signal-time rule against the fill.
            min_r = meta.get("min_structural_r")
            if min_r and (order["target"] - entry) / risk_per_share < min_r:
                skip(f"projects under {min_r:g}:1 at the fill")
                del pending[sym]
                continue

            equity_now = cash + sum(
                _mark(p, prices, today) for p in positions.values()
            )
            risk_budget = equity_now * risk_pct_today
            shares = int(risk_budget // risk_per_share)
            max_notional = equity_now * cfg.max_position_pct
            if shares * entry > max_notional:
                shares = int(max_notional // entry)
            if max_adv_pct is not None and meta.get("adv") and shares * entry > max_adv_pct * meta["adv"]:
                skip("order too large for the stock's traded value")
                del pending[sym]
                continue
            if max_open_risk_pct is not None:
                # CAPITAL at risk, not distance-to-stop. Measuring from the last
                # close made a winner consume budget in proportion to its gain: a
                # position up 50% with a trailing stop still ate a large share of
                # the cap while risking house money, so a handful of winners shut
                # the book to everything else. 2,113 of 3,225 fill-stage rejections
                # in the US run were this cap, and NVDA took 1 trade from 31 setups
                # because of it. Minervini frees risk budget by raising stops to
                # breakeven, which only works if a stop at or above entry counts as
                # zero risk -- which is what capping at the entry price does.
                open_risk = sum(
                    max(0.0, min(_last_close(p, prices, today), p.entry_price) - p.stop) * p.held
                    for p in positions.values())
                if open_risk + risk_per_share * shares > max_open_risk_pct * equity_now:
                    skip("open-risk cap")
                    if meta.get("order") == "open":
                        del pending[sym]
                    continue   # keep resting: risk frees up as stops rise or positions close
            # Scale down to what cash allows rather than declining outright.
            # A trader who can afford 70% of target size buys 70%; they do not
            # skip the breakout. Under-filling puts LESS than risk_pct at risk
            # on that position, never more, so this cannot inflate leverage --
            # it only stops a fully-invested book from being deaf for months.
            full_shares = shares
            if pyramid_frac and 0 < pyramid_frac < 1:
                # the first tranche only; the rest rests above as a buy-stop
                shares = int(shares * pyramid_frac)
                if shares < 1:
                    shares = full_shares          # too small to split meaningfully
            affordable = int((cash - cfg.commission_per_order) // (entry * (1 + fee_rate)))
            if affordable < shares:
                shares = affordable
                partial_fills += 1
            # computed after the final share count, not before
            fee = entry * shares * fee_rate
            cost = cfg.commission_per_order + (entry - raw_entry) * shares + fee
            if shares < 1:
                missed_cash += 1
                del pending[sym]
                continue

            cash -= shares * entry + cfg.commission_per_order + fee
            costs_total += cost
            positions[sym] = PortfolioTrade(
                symbol=sym, setup=order["setup"], decision=order["decision"],
                entry_date=today, entry_price=entry, stop=order["stop"],
                initial_stop=order["stop"],
                target=order["target"], shares=shares, costs=cost, meta=dict(meta),
                slippage=(entry - raw_entry) * shares,
                target_shares=(full_shares if pyramid_frac and shares < full_shares else 0),
                add_price=(entry * (1 + pyramid_add_pct / 100)
                           if pyramid_frac and shares < full_shares else float("nan")),
            )
            if meta.get("base_id") is not None:
                bases_entered.add((sym, meta["base_id"]))
            taken += 1
            del pending[sym]
            if policy.mode == "minervini":
                # the entry bar's close counts for the close-based exits (EX-02, EX-06)
                df = prices[sym]
                _manage_minervini(sym, positions[sym], df, bar, today, policy, close_out, sell, fee_rate, cfg, entry_day=True)

        # ---- 3. today's new signals become resting orders ----------------
        for s in by_date.get(today, []):
            if s.symbol in positions:
                skip("already holding this symbol")
                continue
            if s.symbol in pending:
                skip("an order is already resting in this symbol")
                continue
            pending[s.symbol] = {
                "entry": s.entry, "stop": s.stop, "target": s.target,
                "setup": s.setup, "decision": s.decision, "quality": s.quality,
                "expires": today + pd.tseries.offsets.BDay(PENDING_EXPIRY_BDAYS),
                "meta": s.meta,
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
            c = float(df.loc[:last, "close"].iloc[-1])
            pos.exit_price = (pos.sold_value + c * pos.held) / pos.shares if pos.partial_shares else c
        closed.append(pos)

    idx = pd.DatetimeIndex(all_dates)
    return PortfolioResult(
        equity=pd.Series(eq_rows, index=idx),
        positions_open=pd.Series(pos_rows, index=idx),
        cash=pd.Series(cash_rows, index=idx),
        trades=closed, costs_paid=costs_total,
        signals_seen=len(signals), signals_taken=taken,
        signals_missed_no_slot=missed_slot, signals_missed_no_cash=missed_cash,
        partial_fills=partial_fills, skipped=skipped,
    )


def _manage_minervini(sym, pos: PortfolioTrade, df: pd.DataFrame, bar, today, policy: ExitPolicy,
                      close_out, sell, fee_rate: float, cfg: MarketConfig, entry_day: bool = False) -> None:
    """One session of the strategy's exit rules, in their priority order.

    EX-01 fills during the day; EX-04 at R sells part during the day; the strength sale, a climax
    and EX-02/05/06/07 act on the close and are queued for the next session's open. On the entry
    bar only the close-based rules run: the order of the day's high and low relative to the fill is
    unknown."""
    o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
    m = pos.meta
    if pos.queued_exit and not entry_day:
        close_out(sym, pos, o, pos.queued_exit, today)
        return
    if m.pop("_queued_partial", False) and not entry_day and not pos.partial_shares:
        # a part queued on yesterday's close (selling into strength, or a climax), sold at this open
        n = int(pos.shares * policy.partial_frac)
        if 0 < n < pos.held:
            sell(pos, o, n, today)
            pos.partial_shares = n
    if not entry_day:
        pos.bars_held += 1
    entry, r = pos.entry_price, pos.entry_price - pos.initial_stop
    i = df.index.get_loc(today)
    prev = float(df["close"].iloc[i - 1]) if i > 0 else c
    vol = float(bar.get("volume", 0) or 0)
    v50 = float(bar.get("vol_sma50", float("nan")))
    day_gain = c / prev - 1 if prev else 0.0
    # running records since entry, for the climax test and the time stop
    rec_gain, rec_vol = m.get("_max_gain", -math.inf), m.get("_max_vol", -math.inf)
    m["_max_gain"], m["_max_vol"] = max(rec_gain, day_gain), max(rec_vol, vol)
    if not entry_day:
        m["_max_high"] = max(m.get("_max_high", -math.inf), h)

    if entry_day and m.get("min_breakout_vol") and v50 == v50 and v50 > 0 and vol < m["min_breakout_vol"] * v50:
        # a buy-stop that filled on a light-volume close is not a valid breakout: sold at the next open
        pos.queued_exit = "LIGHT_VOLUME_BREAKOUT"
        return
    if not entry_day:
        # EX-01: the stop; the stop wins a tie with any profit level the same day
        if l <= pos.stop:
            reason = "STOP" if pos.stop <= pos.initial_stop else "BREAKEVEN_STOP"
            close_out(sym, pos, min(pos.stop, o), reason, today)
            return
    # EX-02: failed breakout
    pivot = m.get("pivot")
    if pivot and policy.fail_days and pos.bars_held <= policy.fail_days and c < pivot:
        pos.queued_exit = "FAILED_BREAKOUT"
        return
    if not entry_day and r > 0:
        # EX-03: breakeven, effective from the next session
        if policy.breakeven_r and h >= entry + policy.breakeven_r * r:
            pos.stop = max(pos.stop, _breakeven(pos, fee_rate, cfg))
        # EX-04 (1.7's version): a part off at a fixed R, first time only
        if policy.partial_r and not pos.partial_shares and h >= entry + policy.partial_r * r:
            n = int(pos.shares * policy.partial_frac)
            if 0 < n < pos.held:
                sell(pos, max(o, entry + policy.partial_r * r), n, today)
                pos.partial_shares = n
    ma = float(bar.get(policy.ma_col, float("nan")))
    # EX-04: sell into strength -- a part, once the close is far enough above the average
    if policy.strength_ext and not pos.partial_shares and ma == ma and ma > 0 and c >= (1 + policy.strength_ext) * ma:
        m["_queued_partial"] = True
    # EX-05: climax run
    if policy.climax and c / entry - 1 >= policy.climax_gain:
        closes = df["close"].iloc[max(0, i - 10): i + 1]
        up = int((closes.diff().iloc[1:] > 0).sum()) if len(closes) > 1 else 0
        s200 = float(bar.get("sma200", float("nan")))
        climax = (
            (day_gain > rec_gain and vol > rec_vol)
            or up >= policy.climax_up_days
            or (s200 == s200 and s200 > 0 and c >= (1 + policy.climax_ext_200) * s200)
            or (prev and o / prev - 1 >= policy.climax_gap and c / entry - 1 > policy.climax_gap_after)
        )
        if climax and policy.climax_partial:
            if not pos.partial_shares:
                m["_queued_partial"] = True     # the strength part; the rest waits for EX-06
        elif climax:
            pos.queued_exit = "CLIMAX"
            return
    # EX-06: trend break (on volume, when trend_volume)
    if ma == ma and c < ma and (not policy.trend_volume or (v50 == v50 and vol >= v50)):
        pos.queued_exit = "TREND_EXIT"
        return
    # EX-07: time stop -- the high has not reached +1R within time_stop_days sessions
    if (policy.time_stop_days and pos.bars_held == policy.time_stop_days and r > 0
            and m.get("_max_high", -math.inf) < entry + r):
        pos.queued_exit = "TIME_STOP"


def _breakeven(pos: PortfolioTrade, fee_rate: float, cfg: MarketConfig) -> float:
    """Entry plus the round trip's charges and commissions: a stop here loses only the exit's slippage."""
    return pos.entry_price * (1 + 2 * fee_rate) + 2 * cfg.commission_per_order / max(pos.shares, 1)


def _time_stop_bars(pos: PortfolioTrade, df: pd.DataFrame, policy: ExitPolicy) -> int:
    """Sessions a trade may be held: `time_stop_mult` × the setup's duration in bars (from
    meta["setup_start"] up to the entry session) when the signal carries a start, else
    `time_stop_bars`. 0 = no time stop."""
    start = pos.meta.get("setup_start")
    if policy.time_stop_mult and start:
        dur = int(((df.index >= pd.Timestamp(start)) & (df.index < pos.entry_date)).sum())
        if dur > 0:
            return max(1, math.ceil(policy.time_stop_mult * dur))
    return policy.time_stop_bars


def _manage_bracket(sym, pos: PortfolioTrade, df: pd.DataFrame, bar, today, policy: ExitPolicy,
                    close_out, sell, fee_rate: float, cfg: MarketConfig) -> None:
    """One session of the shared exit modes plus the opt-in trade management (`ExitPolicy.managed`).

    Order within the bar, conservative wherever the bar's path is unknown:
      1. the stop (at the open if the stock gapped through it) -- it wins a tie with the target;
      2. the target: everything, or `partial_at_target` of the shares, after which the rest has no
         target and trails `atr_mult` × ATR14 under its highest close (a trailing mode keeps its own);
      3. the mode's close-based exit (ma, donchian), at the close;
      4. the time stop, at the close of its last session;
    then, for tomorrow: break-even once the high reached entry + `be_r` × R, and the trail.
    Exit reasons: STOP, BREAKEVEN (the raised stop), TRAIL_STOP (the remainder after a partial),
    TARGET, TREND_EXIT, TIME."""
    o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
    m = pos.meta
    pos.bars_held += 1
    entry, r = pos.entry_price, pos.entry_price - pos.initial_stop

    if l <= pos.stop:
        be = m.get("_be")
        if pos.stop <= pos.initial_stop:
            reason = "STOP"
        elif be is not None and pos.stop <= be + 1e-9:
            reason = "BREAKEVEN"
        elif pos.partial_shares:
            reason = "TRAIL_STOP"
        else:
            reason = "STOP"          # a trailing mode's own raised stop, labelled as it always was
        close_out(sym, pos, min(pos.stop, o), reason, today)
        return

    target_live = not pos.partial_shares and (policy.use_target or policy.partial_at_target)
    if target_live and h >= pos.target:
        fill = max(pos.target, o)
        n = int(pos.shares * policy.partial_at_target) if policy.partial_at_target else 0
        if not 0 < n < pos.held:
            close_out(sym, pos, fill, "TARGET", today)
            return
        sell(pos, fill, n, today)
        pos.partial_shares = n

    if policy.mode in ("ma", "donchian"):
        if policy.mode == "ma":
            ma = bar.get(policy.ma_col, float("nan"))
            broke = ma == ma and c < float(ma)
        else:
            hist = df.loc[:today, "low"]
            broke = (len(hist) > policy.donchian_bars
                     and c < float(hist.iloc[-(policy.donchian_bars + 1): -1].min()))
        if broke:
            close_out(sym, pos, c, "TREND_EXIT", today)
            return

    if "_time_n" not in m:
        m["_time_n"] = _time_stop_bars(pos, df, policy)
    if m["_time_n"] and pos.bars_held >= m["_time_n"]:
        close_out(sym, pos, c, "TIME", today)
        return

    # ---- for tomorrow
    if policy.be_r and r > 0 and "_be" not in m and h >= entry + policy.be_r * r:
        m["_be"] = _breakeven(pos, fee_rate, cfg)
        pos.stop = max(pos.stop, m["_be"])
    pos.peak_close = c if pos.peak_close != pos.peak_close else max(pos.peak_close, c)
    if policy.mode == "trail_atr" or (pos.partial_shares and policy.mode == "bracket"):
        atr = bar.get("atr14", float("nan"))
        if atr == atr and atr:
            pos.stop = max(pos.stop, pos.peak_close - policy.atr_mult * float(atr))


def _last_close(pos: PortfolioTrade, prices: dict[str, pd.DataFrame], today: pd.Timestamp) -> float:
    df = prices.get(pos.symbol)
    if df is None:
        return pos.entry_price
    upto = df.loc[:today, "close"]
    return float(upto.iloc[-1]) if len(upto) else pos.entry_price


def _mark(pos: PortfolioTrade, prices: dict[str, pd.DataFrame], today: pd.Timestamp) -> float:
    df = prices.get(pos.symbol)
    if df is None:
        return pos.entry_price * pos.shares
    upto = df.loc[:today, "close"]
    price = float(upto.iloc[-1]) if len(upto) else pos.entry_price
    return price * pos.held


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
            **({"partial_shares": t.partial_shares, "pivot": t.meta.get("pivot"), "base_id": t.meta.get("base_id"),
                "base_no": t.meta.get("base_no"), "rs": t.meta.get("rs"), "sepa": t.meta.get("sepa")} if t.meta else {}),
        }
        for t in trades
    ]
    cols = [
        "symbol", "setup", "decision", "entry_date", "entry_price", "stop",
        "initial_stop", "target",
        "shares", "exit_date", "exit_reason", "exit_price", "notional", "costs",
        "pnl", "r_multiple", "holding_days",
    ]
    if any(t.meta for t in trades):
        cols += ["partial_shares", "pivot", "base_id", "base_no", "rs", "sepa"]
    return pd.DataFrame(rows, columns=cols)
