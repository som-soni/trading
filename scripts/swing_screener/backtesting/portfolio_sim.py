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

A fill sees only what had happened by its own moment in the session (`AT_OPEN`,
`INTRADAY`, `AT_CLOSE`). An exit frees its slot and cash for a fill at or after
the exit, never before it: a position sold at today's close cannot pay for an
order that filled at today's open. Sizing reads the other positions at the
previous session's close (today's close only for an order that buys the close),
and resting orders are cancelled on the previous session's market filter. Until
2026-10-31 all three read today's close, a same-day look-ahead.

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
  fill_min_vol        with confirm_close_above: a close through the level on volume under this × its
                      50-day average does not fill; the order keeps resting
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
from ..core import indicators as ind
from ..strategies import minervini_spec as _ms
from ..strategies import kullamagi as _km
from ..strategies import supertrend as _st
from ..strategies import darvas as _dv
from ..strategies import stage_analysis as _sa
from ..core import darvas as darvas_boxes

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


# Exit modes that read `ExitPolicy.ma_col` off each day's bar.
MA_COL_MODES = frozenset({"ma", "ma_low", "minervini"})


def check_ma_col(policy: "ExitPolicy", frames: dict) -> None:
    """Refuse an exit that reads a moving average the price frames do not carry.

    `bar.get(missing)` is NaN, every comparison with NaN is False, and the exit then never fires --
    silently. `--ma-col sma10` (no daily 10-day average is computed; `sma10` exists only on the
    MONTHLY frame) ran a whole earnings_gaps backtest as buy-and-hold-until-stopped: zero trend
    exits, one position held 3,262 days, filed as the 10-day trail and reported as the best variant.
    """
    if policy.mode not in MA_COL_MODES or not frames:
        return
    missing = [s for s, df in frames.items() if policy.ma_col not in df.columns]
    if missing:
        cols = next(iter(frames.values())).columns
        have = sorted(c for c in cols if c.startswith(("sma", "ema")) and c[3:].isdigit())
        raise ValueError(
            f"exit mode {policy.mode!r} reads {policy.ma_col!r}, which the daily price frames do not carry "
            f"({len(missing)} of {len(frames)} symbols); the averages available are: {', '.join(have)}")


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
    mode: str = "bracket"        # bracket | trail_atr | trail_pct | ma | ma_low | weekly_ma | donchian | supertrend | kullamagi | minervini
    use_target: bool = True      # False lets winners run indefinitely
    atr_mult: float = 3.0        # for trail_atr
    trail_pct: float = 0.04      # for trail_pct: the stop sits this fraction below the highest HIGH since entry
                                 #   (the "fixed % from the peak" trail); it only ever rises
    ma_col: str = "sma50"        # for ma and ma_low, and minervini's EX-06. ma_low: a close below this line
                                 #   is not an exit; the NEXT session trading under that candle's low is
                                 #   (see `_ma_low_level`)
    ma_weeks: int = 30           # for weekly_ma: a completed week closing below the simple average of
                                 #   this many weekly closes sells at that close (Weinstein's 30-week line)
    # for weekly_ma: stage analysis's sells on an EARLIER warning that Stage 2 is failing (2.8) -- Stage 3,
    # distribution weeks, a lower high -- read from its own constants through factories, for the reason
    # given under `minervini` (`--const` patches them after import). All 0 is Weinstein's exit alone, and
    # the simulator then adds nothing. The rules live in `stage_analysis.deterioration`.
    wk_stage3: int = field(default_factory=lambda: int(_sa.EXIT_ON_STAGE3))
    wk_dist_weeks: int = field(default_factory=lambda: int(_sa.EXIT_DIST_WEEKS))
    wk_dist_window: int = field(default_factory=lambda: int(_sa.DIST_WINDOW_WEEKS))
    wk_lower_high: int = field(default_factory=lambda: int(_sa.EXIT_ON_LOWER_HIGH))
    # for weekly_ma: a decisive break (stage analysis 2.10) -- the week's close must be more than this percent
    # below the line to sell; 0 sells on any close below it, Weinstein's rule as the guide states it
    wk_below_pct: float = field(default_factory=lambda: float(_sa.TREND_EXIT_BELOW_PCT))
    donchian_bars: int = 50      # for donchian
    # for supertrend: a close that turns the Supertrend down sells at that close. The strategy's own
    # constants, through a factory for the reason given under `minervini` below (`--const` patches them
    # after import).
    st_period: int = field(default_factory=lambda: _st.ATR_PERIOD)
    st_mult: float = field(default_factory=lambda: _st.MULTIPLIER)
    # for kullamagi: the strategy's own management, read through a factory for the same reason. At the
    # close of session `km_partial_bars` after the entry, if above the entry, 1/`km_partial_divisor` sells
    # there and the stop moves to the entry; the rest sells at the first close below its `km_trail_sma`-day
    # simple average, or at the close of session `km_max_bars`. See `_manage_kullamagi`.
    km_partial_bars: int = field(default_factory=lambda: _km.PARTIAL_AFTER_BARS)
    km_partial_divisor: int = field(default_factory=lambda: _km.PARTIAL_DIVISOR)
    km_trail_sma: int = field(default_factory=lambda: _km.TRAIL_SMA)
    km_trail_ema: bool = field(default_factory=lambda: bool(_km.TRAIL_EMA))   # the trail is an EMA, not an SMA
    km_max_bars: int = field(default_factory=lambda: _km.MAX_HOLD_BARS)
    # for darvas: the stop trails by Darvas boxes (core/darvas.py), found with the darvas strategy's own
    # constants through a factory, as above. A box completed today whose top is above the last box's
    # raises the stop to one tick under its bottom, from tomorrow; never lowered. The optional time stop
    # sells at the close of session `dv_time_stop_bars` if no higher box has formed and the close is
    # under the entry (0 = off). See `_manage_darvas`. The generic trade management below is not used.
    dv_lookback: int = field(default_factory=lambda: _dv.NEW_HIGH_LOOKBACK)
    dv_top_confirm: int = field(default_factory=lambda: _dv.TOP_CONFIRM)
    dv_bottom_confirm: int = field(default_factory=lambda: _dv.BOTTOM_CONFIRM)
    dv_time_stop_bars: int = field(default_factory=lambda: _dv.TIME_STOP_BARS)
    # ---- minervini: the strategy's exit ladder. Defaults are minervini_spec's constants, so a
    # --spec run trades the strategy's documented numbers (1.8: the SEPA Learn guide's).
    #
    # Read through a default_factory, NOT as a plain default. A plain default is evaluated once,
    # when this class is created at import -- which is before `--const` patches the strategy
    # module. So `--const BREAKEVEN_R=0` set the constant, changed the fingerprint and the run
    # directory, and left the policy on 2.0: an experiment that silently measured the control
    # while being filed as a distinct arm. `--const TREND_EXIT_NEEDS_VOLUME=1` was no-op the same
    # way. A factory runs at construction, after the patch, so an override means what it says.
    fail_days: int = field(default_factory=lambda: _ms.FAIL_DAYS)              # EX-02: a close below the pivot within this many sessions of entry (0 = off)
    fail_sma20_days: int = field(default_factory=lambda: _ms.FAIL_SMA20_DAYS)  # EX-02b: a close below the 20-day average within this many sessions of entry (0 = off)
    breakeven_r: float = field(default_factory=lambda: _ms.BREAKEVEN_R)        # EX-03: stop to entry + round-trip costs once the high reaches entry + this × R (0 = off)
    partial_r: float = field(default_factory=lambda: _ms.PARTIAL_R)            # EX-04: sell `partial_frac` at entry + this × R (0 = off)
    partial_frac: float = field(default_factory=lambda: _ms.STRENGTH_FRAC)
    partial_by_sepa: int = field(default_factory=lambda: int(_ms.PARTIAL_BY_SEPA))   # EX-04 by trade type: 0 every trade;
                                                #   1 skip it for an ACCEPTABLE / LEADER company (meta["sepa"]); 2 also NO DATA
    strength_ext: float = field(default_factory=lambda: _ms.STRENGTH_EXT_PCT / 100)   # EX-04: sell `partial_frac` at the next open once the close is
                                                #   this far above `ma_col` (0 = off)
    climax: bool = True          # EX-05
    climax_partial: bool = field(default_factory=lambda: bool(_ms.CLIMAX_IS_PARTIAL))  # a climax sells `partial_frac` (if not yet sold), not everything
    climax_second: bool = False  #   … and, once that part is sold, a climax sells a SECOND `partial_frac` of the position
                                 #   (once): Minervini sells more into the exhaustion day itself (--climax-second)
    climax_gain: float = 0.25    #   only once the position is up this much
    climax_up_days: int = 8      #   … at least this many up closes in the last 10
    climax_ext_200: float = 0.70 #   … close this far above SMA200
    climax_gap: float = 0.03     #   … a gap up this large after a rise of `climax_gap_after`
    climax_gap_after: float = 0.50
    trend_volume: bool = field(default_factory=lambda: bool(_ms.TREND_EXIT_NEEDS_VOLUME))  # EX-06 needs volume ≥ its 50-day average
    trend_closes: int = field(default_factory=lambda: int(_ms.TREND_EXIT_CLOSES))    # EX-06: closes in a row below the line to sell
    trend_loose_r: float = field(default_factory=lambda: float(_ms.TREND_LOOSE_R))   # EX-06: once the high reaches this many R ...
    trend_loose_sma: int = field(default_factory=lambda: int(_ms.TREND_LOOSE_SMA))   #   ... the line is this-day average (0 = off)
    time_stop_days: int = field(default_factory=lambda: _ms.TIME_STOP_DAYS)    # EX-07: sold if the high has not reached +1R within this many sessions (0 = off)
    # Minervini's follow-up buy ('add and reduce', 1.58): while held, a breakout of a NEW base adds this fraction of
    # the first buy, at most `add_max` times, the stop on the whole position raised so its risk stays the first
    # trade's (`_fill_add`). 0 = off.
    add_frac: float = field(default_factory=lambda: float(_ms.ADD_ON_NEW_BASE))
    add_max: int = field(default_factory=lambda: int(_ms.ADD_MAX))
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
        return self.mode not in ("minervini", "darvas") and bool(
            self.be_r or self.time_stop_bars or self.time_stop_mult or self.partial_at_target)

    def label(self) -> str:
        bits = [self.mode]
        if self.mode == "minervini":
            bits.append(self.ma_col)
            if self.partial_r:
                bits.append(f"partial{self.partial_r:g}R")
                if self.partial_by_sepa:
                    bits.append(f"bySepa{self.partial_by_sepa}")
            if self.climax_second:
                bits.append("climax2nd")
            if self.strength_ext != _ms.STRENGTH_EXT_PCT / 100:
                bits.append(f"strength{self.strength_ext * 100:g}" if self.strength_ext else "noStrength")
            if self.fail_days != _ms.FAIL_DAYS:
                bits.append(f"fail{self.fail_days}" if self.fail_days else "noFail")
            if self.fail_sma20_days != _ms.FAIL_SMA20_DAYS:
                bits.append(f"fail20d{self.fail_sma20_days}" if self.fail_sma20_days else "noFail20d")
            if self.time_stop_days != _ms.TIME_STOP_DAYS:
                bits.append(f"time{self.time_stop_days}" if self.time_stop_days else "noTime")
            return "-".join(bits)
        if self.mode == "trail_atr":
            bits.append(f"{self.atr_mult:g}ATR")
        elif self.mode == "trail_pct":
            bits.append(f"{self.trail_pct * 100:g}pct")
        elif self.mode in ("ma", "ma_low"):
            bits.append(self.ma_col)
        elif self.mode == "weekly_ma":
            bits.append(f"{self.ma_weeks}w")
        elif self.mode == "donchian":
            bits.append(f"{self.donchian_bars}d")
        elif self.mode == "supertrend":
            bits.append(f"{self.st_period}x{self.st_mult:g}")
        elif self.mode == "kullamagi":
            bits.append(f"p{self.km_partial_bars}d{self.km_partial_divisor}-{'ema' if self.km_trail_ema else 'sma'}"
                        f"{self.km_trail_sma}-max{self.km_max_bars}")
        elif self.mode == "darvas":
            bits.append(f"h{self.dv_lookback}t{self.dv_top_confirm}b{self.dv_bottom_confirm}"
                        + (f"-time{self.dv_time_stop_bars}" if self.dv_time_stop_bars else ""))
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
    # Cash received from special dividends and demergers while held (`credit_action`). It is a return
    # of capital: every price level the trade carries -- entry_price included -- is lowered by the
    # payout per share on the ex-date, so pnl and R already contain it; this field only reports it.
    credited: float = 0.0

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
    # The same refusals one by one, as (symbol, session) -- what the funnel names, so a stored run
    # answers "why didn't this stock trade?". Reporting only: nothing reads them to decide a trade.
    skipped_at: dict = field(default_factory=dict)   # reason -> [(symbol, date)]
    missed_slot_at: list = field(default_factory=list)
    missed_cash_at: list = field(default_factory=list)


PENDING_EXPIRY_BDAYS = 10

# When in its session an exit or a fill happens, in order. A fill counts only the exits at or before
# its own moment (step 2 of `simulate`). Two INTRADAY events keep the old convention: the exit counts,
# because the bar does not say which came first.
AT_OPEN, INTRADAY, AT_CLOSE = 0, 1, 2
# A base reopens only after one of these: the trade was shaken out, not finished. A trend exit
# (EX-06) says the move itself is over, so buying the same base again is chasing it.
# The exits that say the trade was shaken out rather than that the move is over. FAILED_SMA20 (minervini
# EX-02b) is a pivot failure, which is exactly what Minervini's "failure reset" re-buys.
RE_ENTRY_AFTER = frozenset({"STOP", "BREAKEVEN_STOP", "FAILED_SMA20"})


# price levels a position or its order carries in `meta`, lowered with the price on an ex-date
_META_LEVELS = ("pivot", "_be", "_max_high", "max_fill", "min_open", "cancel_close_below", "confirm_close_above")


def credit_action(pos: "PortfolioTrade", cash_per_share: float) -> float:
    """A special dividend or demerger while `pos` is held: the cash it receives, with every level it
    carries moved down by the payout, as if the stop and target were re-placed against the ex-date
    price. Brokers do not move a resting stop for a dividend, but a stop hit only because the stock
    went ex a payout the holder received is not a loss of the trade's thesis, and leaving it would
    count the payout as a stop-out. Returns the cash for the account."""
    c = float(cash_per_share)
    held = pos.held
    for attr in ("entry_price", "initial_stop", "stop", "target", "peak_close", "add_price"):
        v = getattr(pos, attr)
        if v == v:
            setattr(pos, attr, v - c)
    # shares sold before the ex-date keep their proceeds; on the lowered basis they are worth c less each
    pos.sold_value -= c * (pos.shares - held)
    for k in _META_LEVELS:
        v = pos.meta.get(k)
        if isinstance(v, (int, float)) and v == v:
            pos.meta[k] = v - c
    pos.credited += c * held
    return c * held


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

WEEKLY_LINE = "_weekly_line"   # the weekly_ma exit's level, added to each price frame by `simulate`
ST_DIR = "_st_dir"             # the supertrend exit's direction (1 up, -1 down), added the same way
KM_TRAIL = "_km_trail"         # the kullamagi exit's trailing average (simple or exponential), added the same way


def _below(policy: ExitPolicy) -> float:
    """The fraction of the line a close must fall under to break it: 1, except for weekly_ma with
    `wk_below_pct` set (a decisive break)."""
    return 1 - policy.wk_below_pct / 100 if policy.mode == "weekly_ma" else 1.0


def weekly_line(df: pd.DataFrame, weeks: int) -> pd.Series:
    """The weekly_ma exit's level on each daily bar: on the LAST session of a week, the simple average of
    the last `weeks` weekly closes, that week's included; NaN on every other session, so the exit is read
    only off a completed week. Weeks are `ind.resample_weekly`, the bars the weekly strategies read. The
    final stored bar counts as a week's last only on a Friday: mid-week, its week is not over."""
    out = pd.Series(float("nan"), index=df.index)
    if df.empty:
        return out
    line = ind.resample_weekly(df)["close"].rolling(weeks, min_periods=weeks).mean()
    week = pd.Series(df.index.to_period("W-FRI"), index=df.index)
    last = week != week.shift(-1)
    last.iloc[-1] = df.index[-1].weekday() == 4
    ends = week[last].map(lambda p: p.end_time.normalize())
    out[last] = line.reindex(ends.values).values
    return out


def _weekly_early_exit(pos, df: pd.DataFrame, today, bar, policy: "ExitPolicy") -> str | None:
    """Stage analysis's earlier sells (policy.wk_*), read off `stage_analysis.deterioration`'s columns on a
    completed week after the entry. The reason, or None. Sold at that week's close, like the weekly_ma
    exit itself, so the three differ from it only in WHEN, never in how they fill."""
    if today <= pos.entry_date:
        return None
    if policy.wk_stage3 and bool(bar.get(_sa.DET_STAGE3, False)):
        return "STAGE3_EXIT"
    if policy.wk_dist_weeks and bool(bar.get(_sa.DET_DIST, False)):
        lo = max(pos.entry_date, today - pd.Timedelta(weeks=policy.wk_dist_window))
        n = int(df.loc[(df.index > lo) & (df.index <= today), _sa.DET_DIST].sum())
        if n >= policy.wk_dist_weeks:
            return "DISTRIBUTION_EXIT"
    if policy.wk_lower_high:
        swing = bar.get(_sa.DET_LH, pd.NaT)
        if pd.notna(swing) and pd.Timestamp(swing) >= pos.entry_date:
            return "LOWER_HIGH_EXIT"
    return None


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
    pyramid_at: str = "pct",
    credits=None,
    equal_alloc_pct: float | None = None,
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
    partial profit has been taken. None or 1.0 keeps the old single-tranche fill.

    `pyramid_at="box"` is Darvas's add instead: nothing rests at first; when a box higher than the
    bought one (meta["box_top"]) completes while the position is held, the remainder rests as a buy-stop
    over its top (darvas.buy_above), and on that fill the stop rises to one tick under its bottom
    (darvas.stop_below). A later, higher box moves an unfilled add up to its own top. Boxes come from
    the same causal scan as the darvas exit (`darvas_levels`), read from the previous session's row, so
    an add rests only from the session after its box completed. `pyramid_add_pct` is unused.

    `credits` (marketdata.corporate_actions.Credits): on a special dividend's or demerger's ex-date a
    held position receives the cash and its levels move down by it (`credit_action`); an order
    still resting in that symbol is cancelled, its levels set against the pre-payout price."""
    cap = max_positions if max_positions is not None else cfg.max_open_positions
    policy = exit_policy or ExitPolicy()
    base_slip = cfg.slippage_bps if slippage_bps is None else slippage_bps
    fee_rate = cost_bps / 10_000.0
    prices = exit_frames(prices, policy)
    if pyramid_at not in ("pct", "box"):
        raise ValueError(f"pyramid_at must be 'pct' or 'box', not {pyramid_at!r}")
    if pyramid_at == "box" and pyramid_frac:
        # the box add reads the darvas exit's box columns, whatever the exit mode
        prices = {s: (df if DV_TOP in df.columns else df.assign(**darvas_levels(df, policy)))
                  for s, df in prices.items()}

    check_ma_col(policy, prices)   # every caller, not only the command line

    # the calendar is the union of the dates of every symbol we might trade
    all_dates = sorted({d for df in prices.values() for d in df.index if d >= start})
    if end is not None:
        all_dates = [d for d in all_dates if d <= end]
    if not all_dates:
        raise ValueError("no trading dates in range")

    regime_known = regime_ok.dropna() if regime_ok is not None else None
    by_date: dict[pd.Timestamp, list[Signal]] = {}
    for s in signals:
        by_date.setdefault(s.date, []).append(s)

    cash = float(cfg.account_size)
    positions: dict[str, PortfolioTrade] = {}
    pending: dict[str, dict] = {}
    adds_pending: dict[str, dict] = {}   # follow-up buys into held positions (policy.add_frac), by symbol
    closed: list[PortfolioTrade] = []
    costs_total = 0.0
    taken = missed_slot = missed_cash = partial_fills = 0
    skipped: dict[str, int] = {}
    skipped_at: dict[str, list] = {}
    missed_slot_at: list = []
    missed_cash_at: list = []
    # (symbol, base_id) -> entries taken, and how the last one ended. A base used to be barred
    # for good after one entry, which also barred the re-entry a shakeout invites: a trade stopped
    # at breakeven has given up nothing about the base, it has only been shaken out of it. A
    # strategy says how many attempts it allows via `max_entries_per_base` (default 1 = the old
    # behaviour), and only a shakeout reopens it -- a trend exit means the move is over.
    bases_entered: dict = {}
    base_last_exit: dict = {}

    def skip(reason: str, sym: str, day) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1
        skipped_at.setdefault(reason, []).append((sym, day))

    # today's sales so far, as (at, cash received, slot freed, position, shares, its stop then): step 2
    # sizes a fill from the book as it stood at the fill's own moment, so a later sale is undone there
    sold_today: list[tuple] = []
    ex_today: dict[str, float] = {}     # payout per share of a position that went ex today

    def prior_close(pos: PortfolioTrade, today) -> float:
        """A share of `pos` as a fill during today's session knows it: the previous session's close,
        less a payout it went ex today (already in cash). A position bought today is at its cost."""
        df = prices.get(pos.symbol)
        if pos.entry_date == today or df is None:
            return pos.entry_price
        i = df.index.searchsorted(today)
        return float(df["close"].iloc[i - 1]) - ex_today.get(pos.symbol, 0.0) if i else pos.entry_price

    def book_at(at: int, today) -> tuple[float, float]:
        """(cash, equity) at moment `at` of today's session: the sales after `at` undone, and every
        position held then -- those sold later included -- at the previous session's close. An order
        that buys the close sees the whole session, at today's close."""
        if at == AT_CLOSE:
            return cash, cash + sum(_mark(p, prices, today) for p in positions.values())
        late = [e for e in sold_today if e[0] > at]
        c = cash - sum(e[1] for e in late)
        return c, c + (sum(prior_close(p, today) * p.held for p in positions.values())
                       + sum(prior_close(e[3], today) * e[4] for e in late))

    def open_risk_at(at: int, today) -> float:
        """Capital at risk at moment `at` (see the open-risk cap in step 2), priced as `book_at` does."""
        def risk(p, n, stop):
            px = _last_close(p, prices, today) if at == AT_CLOSE else prior_close(p, today)
            return max(0.0, min(px, p.entry_price) - stop) * n
        return (sum(risk(p, p.held, p.stop) for p in positions.values())
                + sum(risk(e[3], e[4], e[5]) for e in sold_today if e[0] > at))

    def sell(pos: PortfolioTrade, raw: float, n: int, today, *, at: int, slot: bool = False) -> float:
        """Sell n shares at raw (before slippage), at moment `at` of the session. Cash receives the
        slipped fill less commission and charges — the slippage is inside the fill, so it is not
        deducted again (it is still reported in `costs`)."""
        nonlocal cash, costs_total
        fill = _slip(raw, pos.meta.get("slippage_bps", base_slip), "sell")
        cost = cfg.commission_per_order + (raw - fill) * n + fill * n * fee_rate
        pos.costs += cost
        pos.slippage += (raw - fill) * n
        costs_total += cost
        got = fill * n - cfg.commission_per_order - fill * n * fee_rate
        cash += got
        sold_today.append((at, got, slot, pos, n, pos.stop))
        pos.sold_value += fill * n
        pos.open_shares = pos.held - n
        return fill

    def close_out(sym: str, pos: PortfolioTrade, raw: float, reason: str, today, *, at: int) -> None:
        fill = sell(pos, raw, pos.held, today, at=at, slot=True)
        pos.exit_date, pos.exit_reason = today, reason
        if pos.meta.get("base_id") is not None:
            base_last_exit[(sym, pos.meta["base_id"])] = reason
        # blended over any partial sale; exactly the fill when there was none
        pos.exit_price = pos.sold_value / pos.shares if pos.partial_shares else fill
        closed.append(pos)
        del positions[sym]

    eq_rows, pos_rows, cash_rows = [], [], []
    credit_after = all_dates[0] - pd.Timedelta(days=1)

    for today in all_dates:
        sold_today.clear()
        ex_today.clear()
        # ---- corporate actions: the payout of a special dividend or demerger, before the session
        if credits is not None:
            for sym, c in credits.on(today, credit_after, set(positions) | set(pending)).items():
                if sym in positions:
                    cash += credit_action(positions[sym], c)
                    ex_today[sym] = float(c)
                if sym in pending:
                    skip("cancelled: the stock went ex a special dividend or demerger", sym, today)
                    del pending[sym]
            credit_after = today

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
            if pyramid_at == "box":
                _box_add_level(pos, df, today, cfg)
            if not (float(bar["high"]) >= pos.add_price):
                continue
            fill = max(pos.add_price, float(bar["open"]))        # a gap fills worse
            ceiling = pos.meta.get("max_fill")
            if ceiling is not None and fill > float(ceiling):
                skip("add would lift the average cost past the buy range", sym, today)
                pos.target_shares = 0
                continue
            want = pos.target_shares - pos.shares
            fill_slipped = _slip(fill, pos.meta.get("slippage_bps", base_slip), "buy")
            affordable = int((cash - cfg.commission_per_order) // (fill_slipped * (1 + fee_rate)))
            add_n = min(want, max(0, affordable))
            if add_n < 1:
                skip("not enough cash to add", sym, today)
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
            if pyramid_at == "box":
                # Darvas: the add is bought on the next box's breakout, and the stop goes under that box
                pos.stop = max(pos.stop, _dv.stop_below(pos.meta["_py_bottom"], cfg.tick_size))
            if pos.shares >= pos.target_shares:
                pos.target_shares = 0

        # ---- 0b. follow-up buys (policy.add_frac): at this open, before the exits, like the pyramid adds above
        for sym, add in list(adds_pending.items()):
            del adds_pending[sym]
            pos, df = positions.get(sym), prices.get(sym)
            if pos is None or df is None or today not in df.index:
                continue
            got = _fill_add(pos, add, float(df.loc[today, "open"]), cash, fee_rate, cfg, base_slip)
            if isinstance(got, str):
                skip(got, sym, today)
                continue
            spent, extra = got
            cash -= spent
            costs_total += extra

        # ---- 1. exits ----------------------------------------------------
        for sym, pos in list(positions.items()):
            df = prices.get(sym)
            if df is None or today not in df.index:
                continue
            manage_exit(sym, pos, df, df.loc[today], today, policy, close_out, sell, fee_rate, cfg)

        # ---- 2. resting orders -------------------------------------------
        # PF-06 / MKT-01: in risk-off, nothing new is bought. Signals are already
        # filtered out before the simulation, but an order placed while the market
        # was open can still be resting when it closes, and filling it would buy a
        # breakout the regime rule says to refuse. The filter never forces an exit,
        # so open positions above are untouched. The cancel acts before today's open, so it reads
        # the PREVIOUS session's state: today's filter is computed from today's close, which does not
        # exist yet when the order would fill (until 2026-10-31 it read today's).
        if regime_ok is not None and not _risk_on(regime_known, today, before=True):
            for sym in list(pending):
                skip("cancelled: market filter is risk-off", sym, today)
                del pending[sym]

        # A close order (meta["order"] == "close") buys at the close of its own signal session: the
        # signal is the completed bar, so the price is known and nothing later is read. It joins
        # today's fills here, so it ranks, sizes and takes a slot with them; one that cannot fill
        # today is dropped. Its stop and exits are first tested tomorrow (step 1 has already run).
        for s in by_date.get(today, []):
            if s.meta.get("order") != "close" or s.symbol in positions or s.symbol in pending:
                continue
            if regime_ok is not None and not _risk_on(regime_known, today):   # it buys today's close
                skip("cancelled: market filter is risk-off", s.symbol, today)
                continue
            pending[s.symbol] = {
                "entry": s.entry, "stop": s.stop, "target": s.target,
                "setup": s.setup, "decision": s.decision, "quality": s.quality,
                "expires": today, "meta": s.meta,
            }

        # Rank the ones that triggered today, because slots are scarce.
        triggered = []
        for sym, order in list(pending.items()):
            df = prices.get(sym)
            if df is None or today not in df.index:
                continue
            bar = df.loc[today]
            meta = order["meta"]
            if meta.get("order") == "close":
                triggered.append((sym, order, bar))
                continue
            if meta.get("order") == "open":
                # EN-01: the next session's open, that day only
                o = float(bar["open"])
                if o > meta.get("max_fill", math.inf):
                    skip("gapped above the buy range", sym, today)
                    del pending[sym]
                elif o <= meta.get("min_open", -math.inf):
                    skip("opened at or below the tight low", sym, today)
                    del pending[sym]
                else:
                    triggered.append((sym, order, bar))
                continue
            if today > order["expires"]:
                skip("the resting order expired unfilled", sym, today)
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
                fmv = meta.get("fill_min_vol")
                v50 = float(bar.get("vol_sma50", float("nan")))
                if lvl is not None and float(bar["close"]) < float(lvl):
                    skip("poked through the pivot but closed back below it", sym, today)
                elif (lvl is not None and fmv and v50 == v50 and v50 > 0
                      and float(bar.get("volume", 0) or 0) < fmv * v50):
                    # The fill is at this close, and this close's volume is already known to be light: the
                    # breakout is unconfirmed, which the entry-day check below would sell at the next open
                    # for a round trip of costs and an overnight gap (517 of 574 S2 fills in the 1.46 US
                    # optimise run). Leave the order resting, as for a close back below the pivot.
                    skip("closed through the pivot on light volume", sym, today)
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

            if meta.get("order") == "open":
                raw_entry, at = float(bar["open"]), AT_OPEN
            elif meta.get("order") == "close":
                raw_entry, at = float(bar["close"]), AT_CLOSE
            elif meta.get("confirm_close_above") is not None:
                # the close is what confirmed it, so the close is what you can pay:
                # filling at the intraday stop price would be buying on information
                # (how the bar closed) that did not exist at the moment of the touch
                raw_entry, at = max(order["entry"], float(bar["close"])), AT_CLOSE
            else:
                o = float(bar["open"])
                raw_entry = max(order["entry"], o)  # gap fills worse
                at = AT_OPEN if o >= order["entry"] else INTRADAY
            # The book as it stood at the fill: a sale later in the session has not happened yet, so
            # its slot is still taken (and its cash and shares still the position's, `book_at`).
            slots_used = len(positions) + sum(1 for e in sold_today if e[2] and e[0] > at)
            if slots_used >= slots_today:
                missed_slot += 1
                missed_slot_at.append((sym, today))
                if meta.get("order") in ("open", "close"):
                    del pending[sym]
                continue  # keep it resting; a slot may free up before it expires

            if "max_fill" in meta:
                if raw_entry > meta["max_fill"]:
                    skip("gapped above the buy range", sym, today)
                    del pending[sym]
                    continue
            elif raw_entry >= order["target"]:
                skip("gapped past the whole reward", sym, today)
                del pending[sym]
                continue
            if meta.get("base_id") is not None:
                _key = (sym, meta["base_id"])
                _taken = bases_entered.get(_key, 0)
                if _taken >= int(meta.get("max_entries_per_base", 1) or 1):
                    skip("base already entered", sym, today)
                    del pending[sym]
                    continue
                if _taken and base_last_exit.get(_key) not in RE_ENTRY_AFTER:
                    skip("base's last trade was not shaken out", sym, today)
                    del pending[sym]
                    continue
            slip = meta.get("slippage_bps", base_slip)
            entry = _slip(raw_entry, slip, "buy")
            risk_per_share = entry - order["stop"]
            if risk_per_share <= 0:
                skip("fill at or below the stop", sym, today)
                del pending[sym]
                continue
            if risk_per_share / entry > meta.get("max_risk_pct", math.inf):
                skip("stop too far below the fill", sym, today)
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
                skip(f"projects under {min_r:g}:1 at the fill", sym, today)
                del pending[sym]
                continue

            cash_at, equity_now = book_at(at, today)
            if equal_alloc_pct:
                # equal allocation: every position is the same share of equity, whatever its stop
                # (five slots at 20%); the stop still decides the exit, not the size
                shares = int(equity_now * equal_alloc_pct // entry)
            else:
                risk_budget = equity_now * risk_pct_today
                if regime_ok is not None and regime_ok.dtype == float:
                    # the bottoming pilot (minervini_spec MKT_PILOT): pilot size while the gate is open only
                    # on a bottoming signal, read as the order is: a close order on today's close, any
                    # other on the previous session's (the cancel above reads the same)
                    size = _regime_size(regime_known, today, before=at != AT_CLOSE)
                    if 0 < size < 1:
                        risk_budget = equity_now * cfg.risk_pct * min(risk_mult, size)
                        meta = {**meta, "mkt_pilot": True}
                shares = int(risk_budget // risk_per_share)
                max_notional = equity_now * cfg.max_position_pct
                if shares * entry > max_notional:
                    shares = int(max_notional // entry)
            if max_adv_pct is not None and meta.get("adv") and shares * entry > max_adv_pct * meta["adv"]:
                skip("order too large for the stock's traded value", sym, today)
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
                open_risk = open_risk_at(at, today)
                if open_risk + risk_per_share * shares > max_open_risk_pct * equity_now:
                    skip("open-risk cap", sym, today)
                    if meta.get("order") in ("open", "close"):
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
            affordable = int((cash_at - cfg.commission_per_order) // (entry * (1 + fee_rate)))
            if affordable < shares:
                shares = affordable
                partial_fills += 1
            # computed after the final share count, not before
            fee = entry * shares * fee_rate
            cost = cfg.commission_per_order + (entry - raw_entry) * shares + fee
            if shares < 1:
                missed_cash += 1
                missed_cash_at.append((sym, today))
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
                # box: nothing rests until a higher box completes (`_box_add_level`)
                add_price=((math.inf if pyramid_at == "box" else entry * (1 + pyramid_add_pct / 100))
                           if pyramid_frac and shares < full_shares else float("nan")),
            )
            if meta.get("base_id") is not None:
                _k = (sym, meta["base_id"])
                bases_entered[_k] = bases_entered.get(_k, 0) + 1
            taken += 1
            del pending[sym]
            manage_entry_bar(sym, positions[sym], prices[sym], bar, today, policy, at, close_out, sell, fee_rate, cfg)

        # ---- 3. today's new signals become resting orders ----------------
        for s in by_date.get(today, []):
            if s.symbol in positions and _add_wanted(positions[s.symbol], s, policy, today):
                adds_pending[s.symbol] = {"setup": s.setup, "meta": s.meta, "policy": policy}
                continue
            if s.meta.get("order") == "close":
                if s.symbol in positions and positions[s.symbol].entry_date != today:
                    skip("already holding this symbol", s.symbol, today)
                continue        # placed (and filled or dropped) in step 2
            if s.symbol in positions:
                skip("already holding this symbol", s.symbol, today)
                continue
            if s.symbol in pending:
                skip("an order is already resting in this symbol", s.symbol, today)
                continue
            pending[s.symbol] = {
                "entry": s.entry, "stop": s.stop, "target": s.target,
                "setup": s.setup, "decision": s.decision, "quality": s.quality,
                # a strategy may name its own entry window: an episodic pivot's buy-stop is
                # stale after a few sessions, because the move it was chasing has gone without it
                "expires": today + pd.tseries.offsets.BDay(
                    int(s.meta.get("expiry_bdays") or PENDING_EXPIRY_BDAYS)),
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
        skipped_at=skipped_at, missed_slot_at=missed_slot_at, missed_cash_at=missed_cash_at,
    )


def exit_frames(prices: dict[str, pd.DataFrame], policy: ExitPolicy) -> dict[str, pd.DataFrame]:
    """Each price frame with the columns its exit policy reads (the weekly line, the Supertrend
    direction, the trailing average, the Darvas boxes) -- added once, before the walk. `simulate` and
    the open-position tracker (`backtesting/tracker.py`) both call it."""
    if policy.mode == "weekly_ma":
        early = policy.wk_stage3 or policy.wk_dist_weeks or policy.wk_lower_high
        return {s: df.assign(**{WEEKLY_LINE: weekly_line(df, policy.ma_weeks)},
                             **(dict(_sa.deterioration(df).items()) if early else {}))
                for s, df in prices.items()}
    if policy.mode == "supertrend":
        return {s: df.assign(**{ST_DIR: ind.supertrend(df, policy.st_period, policy.st_mult)["dir"]})
                for s, df in prices.items()}
    if policy.mode == "kullamagi":
        avg = ind.ema if policy.km_trail_ema else ind.sma
        return {s: df.assign(**{KM_TRAIL: avg(df["close"].astype(float), policy.km_trail_sma)})
                for s, df in prices.items()}
    if policy.mode == "darvas":
        return {s: df.assign(**darvas_levels(df, policy)) for s, df in prices.items()}
    return prices


def manage_entry_bar(sym, pos: "PortfolioTrade", df: pd.DataFrame, bar, today, policy: ExitPolicy, at: int,
                     close_out, sell, fee_rate: float, cfg: MarketConfig) -> None:
    """What the session a position was bought in does to it, after the fill at moment `at`. The one
    implementation for `simulate` and the open-position tracker."""
    if policy.mode == "minervini":
        # the entry bar's close counts for the close-based exits (EX-02, EX-06)
        _manage_minervini(sym, pos, df, bar, today, policy, close_out, sell, fee_rate, cfg, entry_day=True)
    elif at != AT_CLOSE and float(bar["low"]) <= pos.stop:
        # The fill bar reached the stop. After an open fill the rest of the bar came later, so
        # the stop was hit; after an intraday buy-stop the bar does not say which came first,
        # and the stop wins the tie, as in step 1. It fills at the stop: the price passed through
        # it after the buy. Until 2026-10-31 the fill bar was never tested, so a buy that
        # reversed through its stop that session survived to the next one.
        close_out(sym, pos, pos.stop, "STOP", today, at=INTRADAY)
    elif policy.mode == "darvas" and pos.meta.get("min_breakout_vol"):
        # a light-volume breakout session: sold at the next open (the darvas strategy's switch)
        v50 = float(bar.get("vol_sma50", float("nan")))
        if v50 == v50 and v50 > 0 and float(bar.get("volume", 0) or 0) < pos.meta["min_breakout_vol"] * v50:
            pos.queued_exit = "LIGHT_VOLUME_BREAKOUT"


def manage_exit(sym, pos: "PortfolioTrade", df: pd.DataFrame, bar, today, policy: ExitPolicy,
                close_out, sell, fee_rate: float, cfg: MarketConfig) -> None:
    """One session of an open position under `policy`: sell it (`close_out`), sell part (`sell`), or
    ratchet its stop for tomorrow. `simulate` calls it for every held position each session, and the
    open-position tracker replays a live position's bars through it -- one implementation of the exits.
    `df` is the position's frame from `exit_frames`, `bar` its row for `today`."""
    if policy.mode == "minervini":
        _manage_minervini(sym, pos, df, bar, today, policy, close_out, sell, fee_rate, cfg)
        return

    if policy.mode == "kullamagi":
        _manage_kullamagi(sym, pos, bar, today, policy, close_out, sell)
        return

    if policy.mode == "darvas":
        _manage_darvas(sym, pos, bar, today, policy, close_out, cfg)
        return

    if policy.managed:
        _manage_bracket(sym, pos, df, bar, today, policy, close_out, sell, fee_rate, cfg)
        return

    hit_stop = bar["low"] <= pos.stop
    # ma_low: a sell-stop under the low of a held session that closed below the line. It acts during
    # the bar, after the stop (which wins a tie, as always) and before the target (conservative)
    low_break = (_ma_low_level(pos, df, today, bar, policy)
                 if policy.mode == "ma_low" and not hit_stop else None)
    hit_target = low_break is None and policy.use_target and bar["high"] >= pos.target
    trend_break = False
    if not hit_stop and not hit_target and policy.mode in ("ma", "weekly_ma", "donchian", "supertrend"):
        # trend-failure exits act on the CLOSE, so they are evaluated
        # only once the bar is complete -- no intrabar clairvoyance
        if policy.mode == "supertrend":
            trend_break = bar.get(ST_DIR, 0) == -1
        elif policy.mode in ("ma", "weekly_ma"):
            ma = bar.get(policy.ma_col if policy.mode == "ma" else WEEKLY_LINE, float("nan"))
            trend_break = ma == ma and float(bar["close"]) < float(ma) * _below(policy)
        else:
            hist = df.loc[:today, "low"]
            if len(hist) > policy.donchian_bars:
                floor_ = float(hist.iloc[-(policy.donchian_bars + 1) : -1].min())
                trend_break = float(bar["close"]) < floor_

    early = (_weekly_early_exit(pos, df, today, bar, policy)
             if policy.mode == "weekly_ma" and not (hit_stop or hit_target or trend_break) else None)

    if not (hit_stop or hit_target or trend_break or low_break is not None or early):
        # nothing exited: ratchet the trailing stop upward for tomorrow
        c = float(bar["close"])
        pos.peak_close = c if pos.peak_close != pos.peak_close else max(pos.peak_close, c)
        if policy.mode == "trail_atr":
            atr = bar.get("atr14", float("nan"))
            if atr == atr and atr:
                pos.stop = max(pos.stop, pos.peak_close - policy.atr_mult * float(atr))
        elif policy.mode == "trail_pct":
            _trail_pct(pos, bar, policy)
        return

    o = float(bar["open"])
    if hit_stop:  # conservative: the stop wins a same-bar tie
        raw = min(pos.stop, o)  # gap-through fills at the open
        reason, at = "STOP", AT_OPEN if o <= pos.stop else INTRADAY
    elif low_break is not None:
        raw = min(low_break, o)  # a gap under the candle's low fills at the open
        reason, at = "TREND_EXIT", AT_OPEN if o <= low_break else INTRADAY
    elif hit_target:
        raw = max(pos.target, o)
        reason, at = "TARGET", AT_OPEN if o >= pos.target else INTRADAY
    else:
        raw = float(bar["close"])  # trend-failure exit, at the close
        reason, at = early or "TREND_EXIT", AT_CLOSE
    close_out(sym, pos, raw, reason, today, at=at)


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
        close_out(sym, pos, o, pos.queued_exit, today, at=AT_OPEN)
        return
    if m.pop("_queued_partial", False) and not entry_day and not pos.partial_shares:
        # a part queued on yesterday's close (selling into strength, or a climax), sold at this open
        n = int(pos.shares * policy.partial_frac)
        if 0 < n < pos.held:
            sell(pos, o, n, today, at=AT_OPEN)
            pos.partial_shares = n
    if m.pop("_queued_second", False) and not entry_day and pos.partial_shares and not m.get("_second_sold"):
        # the second part a climax sells (climax_second), once the strength part is already gone
        n = int(pos.shares * policy.partial_frac)
        if 0 < n < pos.held:
            sell(pos, o, n, today, at=AT_OPEN)
            pos.partial_shares += n
            m["_second_sold"] = True
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
            close_out(sym, pos, min(pos.stop, o), reason, today, at=AT_OPEN if o <= pos.stop else INTRADAY)
            return
    # EX-02: failed breakout
    pivot = m.get("pivot")
    if pivot and policy.fail_days and pos.bars_held <= policy.fail_days and c < pivot:
        pos.queued_exit = "FAILED_BREAKOUT"
        return
    # EX-02b: the breakout did not hold its 20-day average
    s20 = float(bar.get("sma20", float("nan")))
    if policy.fail_sma20_days and pos.bars_held <= policy.fail_sma20_days and s20 == s20 and c < s20:
        pos.queued_exit = "FAILED_SMA20"
        return
    if not entry_day and r > 0:
        # EX-03: breakeven, effective from the next session
        if policy.breakeven_r and h >= entry + policy.breakeven_r * r:
            pos.stop = max(pos.stop, _breakeven(pos, fee_rate, cfg))
        # EX-04 (1.7's version): a part off at a fixed R, first time only
        if (policy.partial_r and not pos.partial_shares and h >= entry + policy.partial_r * r
                and not _holds_for_trend(pos, policy)):
            n = int(pos.shares * policy.partial_frac)
            if 0 < n < pos.held:
                lvl = entry + policy.partial_r * r
                sell(pos, max(o, lvl), n, today, at=AT_OPEN if o >= lvl else INTRADAY)
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
            elif policy.climax_second and not m.get("_second_sold"):
                m["_queued_second"] = True      # a second part into the climax itself
        elif climax:
            pos.queued_exit = "CLIMAX"
            return
    # EX-06: trend break (on volume, when trend_volume). With trend_loose_r, a trade whose high has reached that many R
    # watches the slower trend_loose_sma-day average instead; with trend_closes, it takes that many closes in a row below.
    line = ma
    if policy.trend_loose_r and r > 0 and m.get("_max_high", -math.inf) >= entry + policy.trend_loose_r * r:
        slow = bar.get(f"sma{policy.trend_loose_sma}")
        if slow is None:
            k = df["close"].iloc[max(0, i - policy.trend_loose_sma + 1): i + 1]
            slow = float(k.mean()) if len(k) == policy.trend_loose_sma else float("nan")
        line = float(slow)
    under = line == line and c < line
    m["_under_n"] = m.get("_under_n", 0) + 1 if under else 0
    if under and m["_under_n"] >= max(1, policy.trend_closes) and (not policy.trend_volume or (v50 == v50 and vol >= v50)):
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


def _ma_low_level(pos: PortfolioTrade, df: pd.DataFrame, today, bar, policy: ExitPolicy) -> float | None:
    """The ma_low exit: the price at which today sells, or None.

    A close below `ma_col` is not an exit by itself; it arms one. The session after it sells if it trades
    under that candle's low -- a sell-stop resting there, filled at it (at the open on a gap below it).
    Only the previous session is read: a close back above the line cancels the armed exit, and each new
    close below it arms at that candle's own low, so "a close below, then a break of that candle's low"
    always means the next session. The armed candle must be one the position held (the entry session
    or later): a dip before the buy is the setup, not an exit. Reads nothing past today's bar."""
    i = df.index.get_loc(today)
    if i < 1 or df.index[i - 1] < pos.entry_date:
        return None
    prev = df.iloc[i - 1]
    ma = prev.get(policy.ma_col, float("nan"))
    if not (ma == ma and float(prev["close"]) < float(ma)):
        return None
    level = float(prev["low"])
    return level if float(bar["low"]) < level else None


def _manage_bracket(sym, pos: PortfolioTrade, df: pd.DataFrame, bar, today, policy: ExitPolicy,
                    close_out, sell, fee_rate: float, cfg: MarketConfig) -> None:
    """One session of the shared exit modes plus the opt-in trade management (`ExitPolicy.managed`).

    Order within the bar, conservative wherever the bar's path is unknown:
      1. the stop (at the open if the stock gapped through it) -- it wins a tie with the target;
      1b. ma_low only: a trade under the low of a held session that closed below `ma_col` (at the open
         if the stock gapped under it), before the target;
      2. the target: everything, or `partial_at_target` of the shares, after which the rest has no
         target and trails `atr_mult` × ATR14 under its highest close (a trailing mode keeps its own);
      3. the mode's close-based exit (ma, donchian, supertrend), at the close;
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
        close_out(sym, pos, min(pos.stop, o), reason, today, at=AT_OPEN if o <= pos.stop else INTRADAY)
        return

    if policy.mode == "ma_low":
        level = _ma_low_level(pos, df, today, bar, policy)
        if level is not None:
            close_out(sym, pos, min(level, o), "TREND_EXIT", today, at=AT_OPEN if o <= level else INTRADAY)
            return

    target_live = not pos.partial_shares and (policy.use_target or policy.partial_at_target)
    if target_live and h >= pos.target:
        fill = max(pos.target, o)
        n = int(pos.shares * policy.partial_at_target) if policy.partial_at_target else 0
        if not 0 < n < pos.held:
            close_out(sym, pos, fill, "TARGET", today, at=AT_OPEN if o >= pos.target else INTRADAY)
            return
        sell(pos, fill, n, today, at=AT_OPEN if o >= pos.target else INTRADAY)
        pos.partial_shares = n

    if policy.mode in ("ma", "weekly_ma", "donchian", "supertrend"):
        if policy.mode == "supertrend":
            broke = bar.get(ST_DIR, 0) == -1
        elif policy.mode in ("ma", "weekly_ma"):
            ma = bar.get(policy.ma_col if policy.mode == "ma" else WEEKLY_LINE, float("nan"))
            broke = ma == ma and c < float(ma) * _below(policy)
        else:
            hist = df.loc[:today, "low"]
            broke = (len(hist) > policy.donchian_bars
                     and c < float(hist.iloc[-(policy.donchian_bars + 1): -1].min()))
        if broke:
            close_out(sym, pos, c, "TREND_EXIT", today, at=AT_CLOSE)
            return

    if "_time_n" not in m:
        m["_time_n"] = _time_stop_bars(pos, df, policy)
    if m["_time_n"] and pos.bars_held >= m["_time_n"]:
        close_out(sym, pos, c, "TIME", today, at=AT_CLOSE)
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
    elif policy.mode == "trail_pct":
        _trail_pct(pos, bar, policy)


def _manage_kullamagi(sym, pos: PortfolioTrade, bar, today, policy: ExitPolicy, close_out, sell) -> None:
    """One session of the kullamagi strategy's management, in this order:
      1. the stop, at the stop or at the open if the stock gapped through it (STOP, or BREAKEVEN once moved);
      2. a close below the `km_trail_sma`-day average sells everything left at that close (TREND_EXIT);
      3. at the close of session `km_partial_bars`, if that close is above the entry, 1/`km_partial_divisor`
         of the shares sells there and the stop moves up to the entry, from the next session;
      4. at the close of session `km_max_bars`, whatever is left sells (TIME)."""
    o, l, c = float(bar["open"]), float(bar["low"]), float(bar["close"])
    pos.bars_held += 1
    if l <= pos.stop:
        reason = "BREAKEVEN" if pos.stop > pos.initial_stop else "STOP"
        close_out(sym, pos, min(pos.stop, o), reason, today, at=AT_OPEN if o <= pos.stop else INTRADAY)
        return
    ma = bar.get(KM_TRAIL, float("nan"))
    if ma == ma and c < float(ma):
        close_out(sym, pos, c, "TREND_EXIT", today, at=AT_CLOSE)
        return
    if (policy.km_partial_bars and pos.bars_held == policy.km_partial_bars and not pos.partial_shares
            and c > pos.entry_price and policy.km_partial_divisor):
        n = int(pos.shares // policy.km_partial_divisor)
        if 0 < n < pos.held:
            sell(pos, c, n, today, at=AT_CLOSE)
            pos.partial_shares = n
            pos.stop = max(pos.stop, pos.entry_price)
    if policy.km_max_bars and pos.bars_held >= policy.km_max_bars:
        close_out(sym, pos, c, "TIME", today, at=AT_CLOSE)


DV_TOP = "_dv_top"             # the darvas exit's boxes: top and bottom on the session that completes each
DV_BOTTOM = "_dv_bottom"       #   box, NaN on every other session


def darvas_levels(df: pd.DataFrame, policy: ExitPolicy) -> dict:
    """The darvas exit's boxes as two columns: on the session that confirms a box's bottom, its top and
    bottom; NaN elsewhere. One causal scan (core/darvas.py) per symbol: a box is written on the bar that
    completed it, from bars up to that bar only, so reading a session's row is reading the boxes found
    on the bars up to that session (tests/test_darvas_exit.py checks the two agree)."""
    top = pd.Series(float("nan"), index=df.index)
    bottom = top.copy()
    if len(df):
        for b in darvas_boxes.boxes(df["high"], df["low"], policy.dv_lookback, policy.dv_top_confirm,
                                    policy.dv_bottom_confirm):
            top.iat[b.done_i], bottom.iat[b.done_i] = b.top, b.bottom
    return {DV_TOP: top, DV_BOTTOM: bottom}


ADD_SETUPS = ("S1", "S2", "S7", "S8")   # the minervini breakouts a follow-up buy is made on (`policy.add_frac`)


def _add_wanted(pos: "PortfolioTrade", s, policy: ExitPolicy, today) -> bool:
    """Whether today's signal `s`, in a stock `pos` already holds, is a follow-up buy -- Minervini's "add and reduce":
    a breakout (ADD_SETUPS) of a base other than the one the position was bought from, its pivot above the
    position's average cost (adding into strength, never into weakness), with fewer than `add_max` adds so far."""
    if policy.mode != "minervini" or not policy.add_frac or pos.adds >= policy.add_max or pos.entry_date == today:
        return False
    if s.setup not in ADD_SETUPS or s.meta.get("base_id") is None or s.meta.get("base_id") == pos.meta.get("base_id"):
        return False
    piv = s.meta.get("pivot")
    return piv is not None and float(piv) > pos.entry_price


def _fill_add(pos: "PortfolioTrade", add: dict, o: float, cash: float, fee_rate: float, cfg: MarketConfig,
              base_slip: float):
    """A follow-up buy into `pos` at the open `o`, the session after its signal. Size: `add_frac` of the FIRST buy.
    The stop on the whole position rises only as far as it must to keep its open risk at the first trade's risk --
    the add is paid for by the profit, not by new risk. Not to the new base's own stop: in the smoke test that
    tightened Netflix's 2013 position from a +3.5R trend exit to a +0.5R stop-out. Returns (cash spent, costs), or
    the reason it was refused. `entry_price` becomes the share-weighted average, as for the pyramid adds."""
    m, policy = add["meta"], add["policy"]
    if o > float(m.get("max_fill", math.inf)):
        return "add gapped above the new base's buy range"
    pos.meta.setdefault("_n0", pos.shares)
    pos.meta.setdefault("_risk0", (pos.entry_price - pos.initial_stop) * pos.shares)
    fill = _slip(o, pos.meta.get("slippage_bps", base_slip), "buy")
    n = min(int(pos.meta["_n0"] * policy.add_frac), int((cash - cfg.commission_per_order) // (fill * (1 + fee_rate))))
    if n < 1:
        return "not enough cash to add"
    held = pos.held + n
    avg_held = (pos.entry_price * pos.held + fill * n) / held   # the average cost of the shares still held
    stop = max(pos.stop, avg_held - pos.meta["_risk0"] / held)
    if stop >= fill:
        return "add would need a stop at or above its own fill"
    fee = fill * n * fee_rate
    extra = cfg.commission_per_order + (fill - o) * n + fee
    pos.entry_price = (pos.entry_price * pos.shares + fill * n) / (pos.shares + n)
    pos.shares += n
    if pos.open_shares >= 0:
        pos.open_shares += n
    pos.stop = stop
    pos.costs += extra
    pos.slippage += (fill - o) * n
    pos.adds += 1
    return n * fill + cfg.commission_per_order + fee, extra


def _box_add_level(pos: "PortfolioTrade", df: pd.DataFrame, today, cfg: MarketConfig) -> None:
    """`pyramid_at="box"`: rest the add over a box higher than the last one, read from the PREVIOUS
    session's row (a box completes at a close, so its buy-stop acts from the next session). Only boxes
    completed while the position was held count, starting above the bought box (meta["box_top"])."""
    i = df.index.get_loc(today)
    if i < 1 or df.index[i - 1] < pos.entry_date:
        return
    prev = df.iloc[i - 1]
    top = prev.get(DV_TOP, float("nan"))
    m = pos.meta
    if top == top and top > m.get("_py_top", m.get("box_top", -math.inf)):
        m["_py_top"], m["_py_bottom"] = float(top), float(prev[DV_BOTTOM])
        pos.add_price = _dv.buy_above(top, cfg.tick_size)


def _manage_darvas(sym, pos: "PortfolioTrade", bar, today, policy: ExitPolicy, close_out, cfg: MarketConfig) -> None:
    """One session of the darvas exit, in this order:
      1. a light-volume fill queued on the entry session sells at this open (LIGHT_VOLUME_BREAKOUT);
      2. the stop, at the stop or at the open if the stock gapped through it (STOP, or TRAIL_STOP once
         a box has raised it);
      3. the time stop, when on: at the close of session `dv_time_stop_bars`, if no higher box has
         formed and the close is below the entry (TIME);
      4. for tomorrow: a box completed today whose top is above the last box's -- the bought box's
         (meta["box_top"]) at first -- raises the stop to one tick under its bottom
         (darvas.stop_below). Never lowered. Today's high and low are known by then: the box is
         complete at today's close, so the raised stop acts from the next session."""
    o, l, c = float(bar["open"]), float(bar["low"]), float(bar["close"])
    m = pos.meta
    if pos.queued_exit:
        close_out(sym, pos, o, pos.queued_exit, today, at=AT_OPEN)
        return
    pos.bars_held += 1
    if l <= pos.stop:
        reason = "STOP" if pos.stop <= pos.initial_stop else "TRAIL_STOP"
        close_out(sym, pos, min(pos.stop, o), reason, today, at=AT_OPEN if o <= pos.stop else INTRADAY)
        return
    if (policy.dv_time_stop_bars and pos.bars_held == policy.dv_time_stop_bars
            and not m.get("_dv_boxes") and c < pos.entry_price):
        close_out(sym, pos, c, "TIME", today, at=AT_CLOSE)
        return
    top = bar.get(DV_TOP, float("nan"))
    if top == top and top > m.get("_dv_last_top", m.get("box_top", -math.inf)):
        m["_dv_last_top"] = float(top)
        m["_dv_boxes"] = m.get("_dv_boxes", 0) + 1
        pos.stop = max(pos.stop, _dv.stop_below(float(bar[DV_BOTTOM]), cfg.tick_size))


def _trail_pct(pos: "PortfolioTrade", bar, policy: ExitPolicy) -> None:
    """The fixed-percentage trail: raise the stop to `trail_pct` below the highest high since entry.
    Called after the session's exits, so today's high moves tomorrow's stop, never today's."""
    peak = max(pos.meta.get("_peak_high", float("-inf")), float(bar["high"]))
    pos.meta["_peak_high"] = peak
    pos.stop = max(pos.stop, peak * (1 - policy.trail_pct))


_SEPA_HOLD = {1: {"ACCEPTABLE", "LEADER"}, 2: {"ACCEPTABLE", "LEADER", "NO DATA"}}


def _holds_for_trend(pos: PortfolioTrade, policy: ExitPolicy) -> bool:
    """EX-04 by trade type (minervini_spec PARTIAL_BY_SEPA): a company whose results on the trade's own
    date pass the growth tests skips the +PARTIAL_R part and holds to the trend exit."""
    return bool(policy.partial_by_sepa) and (pos.meta or {}).get("sepa") in _SEPA_HOLD.get(policy.partial_by_sepa, ())


def _regime_size(known: pd.Series, today, before: bool = False) -> float:
    """The market filter's size for a new entry: 1.0, or minervini_spec's pilot fraction while its
    bottoming pilot (MKT_PILOT) holds the gate open in a risk-off market. Read like `_risk_on`."""
    i = known.index.searchsorted(today, side="left" if before else "right")
    return float(known.iloc[i - 1]) if i else 0.0


def _risk_on(known: pd.Series, today, before: bool = False) -> bool:
    """The market filter's state on `today`'s close, or with `before` on the previous session's. `known`
    is the filter with its missing readings dropped, so each day reads the last real one. No reading yet
    (before the benchmark starts) is risk-off: `bool(NaN)` is True, which read a missing state as open."""
    i = known.index.searchsorted(today, side="left" if before else "right")
    return bool(known.iloc[i - 1]) if i else False


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
            "holding_days": t.holding_days, "credited": round(t.credited, 2),
            **({"partial_shares": t.partial_shares, "pivot": t.meta.get("pivot"), "base_id": t.meta.get("base_id"),
                "base_no": t.meta.get("base_no"), "rs": t.meta.get("rs"), "sepa": t.meta.get("sepa")} if t.meta else {}),
            **({"mkt_pilot": 1} if t.meta and t.meta.get("mkt_pilot") else {}),
        }
        for t in trades
    ]
    cols = [
        "symbol", "setup", "decision", "entry_date", "entry_price", "stop",
        "initial_stop", "target",
        "shares", "exit_date", "exit_reason", "exit_price", "notional", "costs",
        "pnl", "r_multiple", "holding_days", "credited",
    ]
    if any(t.meta for t in trades):
        cols += ["partial_shares", "pivot", "base_id", "base_no", "rs", "sepa"]
    if any(t.meta and t.meta.get("mkt_pilot") for t in trades):
        cols += ["mkt_pilot"]           # bought at pilot size on the market filter's bottoming signal
    return pd.DataFrame(rows, columns=cols)
