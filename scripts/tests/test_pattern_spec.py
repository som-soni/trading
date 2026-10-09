"""Check `core/pattern_spec.py` against research/chart-pattern-spec.md.

Two kinds of check, and the second is the one that matters:

  * the §2 and §3 primitives do what the spec says (swings alternate and
    de-wiggle, tolerance scales with ATR, lines fit, BO-01..BO-06 fire);
  * **one mutation per cup rule.** A textbook cup is drawn, then broken in
    eleven ways, and each break must be caught by the rule written for it.
    A rule that no mutation can trip is a rule that is not wired in, which is
    how a detector ends up with documentation it does not implement.

Run: `PYTHONPATH=. python3 -m tests.test_pattern_spec`
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.core import indicators as ind
from swing_screener.core import pattern_spec as ps

rng = np.random.default_rng(17)
P = ps.PatternParams()

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'ok  ' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(f"{name}{': ' + detail if detail else ''}")


def frame(close: np.ndarray, volume: np.ndarray | None = None,
          seed: int = 17) -> pd.DataFrame:
    """Wicks come from a generator seeded HERE, not from module state.

    Drawing them from a shared `rng` made every chart depend on how many
    charts had been built before it, so adding a test silently changed the
    data every later test ran on — which is how a mutation that should have
    tripped HS-01 came back with no pattern at all.
    """
    r = np.random.default_rng(seed)
    n = len(close)
    d = pd.DataFrame(
        {
            "open": close,
            "high": close * (1 + r.uniform(0.0005, 0.004, n)),
            "low": close * (1 - r.uniform(0.0005, 0.004, n)),
            "close": close,
            "volume": volume if volume is not None else np.full(n, 1_000_000.0),
        },
        index=pd.bdate_range("2018-01-01", periods=n),
    )
    return ind.enrich_daily(d)


def seg(a: float, b: float, n: int) -> np.ndarray:
    return np.linspace(a, b, n, endpoint=False)


# --------------------------------------------------------------- the cup

def build_cup(
    *, prior: float = 0.60, depth: float = 0.22, lip: float = 1.00,
    left: int = 60, right: int = 60, handle_depth: float = 0.07,
    handle_len: int = 14, handle_shape: str = "down", v_shape: bool = False,
    handle_vol: float = 0.55, pre: int = 150,
) -> pd.DataFrame:
    """A textbook cup, with every knob a mutation needs.

    A = 100 by construction, so `depth`, `lip` and `handle_depth` read as
    fractions of it.
    """
    A, B, C = 100.0, 100.0 * (1 - depth), 100.0 * lip
    if v_shape:
        # the same duration and depth, but almost no time spent at the low
        body = np.concatenate([
            seg(A, A * 0.93, left - 4), seg(A * 0.93, B, 4),
            seg(B, C * 0.93, 4), seg(C * 0.93, C, right - 4),
        ])
    else:
        down = seg(A, B, left)
        arc = B + (A - B) * 0.04 * np.sin(np.linspace(0, np.pi, 12))
        up = seg(B, C, right)
        body = np.concatenate([down, arc, up])
    low_point = C * (1 - handle_depth)
    if handle_shape == "wedge_up":
        # dips far enough to pass CH-08, then wedges back up so the fitted
        # slope of its closes is positive — the thing O'Neil warns about
        half = handle_len // 2
        handle = np.concatenate([
            np.linspace(C, low_point, half),
            np.linspace(low_point, C * 1.02, handle_len - half),
        ])
    else:
        handle = np.linspace(C, low_point, handle_len)
    close = np.concatenate([seg(A / (1 + prior), A, pre), body, handle])
    n_body = len(body)
    vol = np.concatenate([
        np.full(pre, 1_000_000.0),
        np.full(n_body, 900_000.0),
        np.full(handle_len, handle_vol * 1_000_000.0),
    ])
    return frame(close, vol)


# ------------------------------------------------------ §2.1 swing points

d = build_cup()
majors, minors = ps.swings(d, P.k_major, P), ps.swings(d, P.k_minor, P)
check("§2.1 swings alternate H/L/H/L",
      all(a.kind != b.kind for a, b in zip(majors, majors[1:])))
noisy = frame(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.016, 600))))
check("§2.1 minor scale finds more swings than major",
      len(ps.swings(noisy, P.k_minor, P)) > len(ps.swings(noisy, P.k_major, P)),
      f"{len(ps.swings(noisy, P.k_minor, P))} vs {len(ps.swings(noisy, P.k_major, P))}")
check("§2.1 every move clears the minimum swing size",
      all(abs(b.price - a.price) / a.price >= P.min_swing_pct / 100 - 1e-9
          for a, b in zip(majors, majors[1:])))
check("§2.1 no look-ahead: the newest k bars are never swings",
      all(s.pos <= len(d) - 1 - P.k_major for s in majors),
      f"newest swing at {max(s.pos for s in majors)} of {len(d) - 1}")

# a wiggle inside a trend must be dropped, and dropping it must not break
# alternation
wiggly = frame(np.concatenate([
    seg(50, 100, 200), seg(100, 99, 10), seg(99, 140, 100),
]))
w = ps.swings(wiggly, P.k_major, P)
check("§2.1 a 1% wiggle is dropped",
      all(abs(b.price - a.price) / a.price >= 0.03 - 1e-9 for a, b in zip(w, w[1:])))

# ------------------------------------------------------- §2.2 tolerance

check("§2.2 tolerance floors at tol_pct", ps.tol(100.0, 0.5, P) == P.tol_pct / 100)
check("§2.2 tolerance scales with ATR on a volatile name",
      ps.tol(100.0, 8.0, P) > P.tol_pct / 100,
      f"{ps.tol(100.0, 8.0, P):.4f}")
check("§2.2 about_equal", ps.about_equal(100, 102, 0.03) and not ps.about_equal(100, 110, 0.03))

# ------------------------------------------------------ §2.3 trendlines

line = ps.fit_line([(0, 10.0), (10, 12.0), (20, 14.0)])
check("§2.3 TL-01 least squares recovers the slope", abs(line.slope - 0.2) < 1e-9)
check("§2.3 TL-04/05 a 0.2/12 per-day line is not flat", not line.is_flat(10, P))
check("§2.3 TL-05 a level line is flat", ps.fit_line([(0, 50.0), (20, 50.0)]).is_flat(10, P))
check("§2.3 TL-02 touches counted within tol",
      ps.touches(line, [ps.Swing(0, "H", 10.1), ps.Swing(10, "H", 12.0),
                        ps.Swing(20, "H", 20.0)], 0.03) == 2)
flat_hi, flat_lo = ps.fit_line([(0, 110.0), (20, 110.0)]), ps.fit_line([(0, 90.0), (20, 90.0)])
inside = np.full(21, 100.0)
outside = inside.copy()
outside[10] = 130.0
check("§2.3 TL-03 containment", ps.contained(flat_hi, flat_lo, inside, 0, 20, 0.03))
check("§2.3 TL-03 a close beyond the band breaks containment",
      not ps.contained(flat_hi, flat_lo, outside, 0, 20, 0.03))

# ----------------------------------------------------- §2.4 prior trend

lows = np.concatenate([np.full(100, 50.0), np.full(50, 80.0)])
check("§2.4 PT-01 passes a 60% advance", ps.prior_uptrend(lows, 150, 80.0, P)[0])
check("§2.4 PT-01 fails a 5% advance", not ps.prior_uptrend(np.full(150, 76.0), 150, 80.0, P)[0])
check("§2.4 PT-02 passes a 40% decline",
      ps.prior_downtrend(np.concatenate([np.full(150, 100.0)]), 150, 60.0, P)[0])

# ---------------------------------------------------------- §2.5 volume

vol = np.concatenate([np.full(50, 1e6), np.array([2.1e6])])
check("§2.5 VOL50 excludes the pattern's own bars", ps.vol50(vol, 50) == 1e6)
check("§2.5 RV(t)", abs(ps.rv(vol, 50, 1e6) - 2.1) < 1e-9)
check("§2.5 declining volume gives a negative log slope",
      ps.log_volume_slope(np.linspace(2e6, 1e6, 30), 0, 29) < 0)

# ------------------------------------------------------------- §3 rules

lv = ps.Levels(trigger=100.0, invalidation=90.0, height=20.0)
check("§3 BO-06 target is T + H", lv.target == 120.0)
check("§3 BO-01 a close 0.2% through T is not a breakout",
      not ps.broke_out(100.2, 2.0, lv, P))
check("§3 BO-01+BO-02 a close 1% through T on 2x volume is",
      ps.broke_out(101.0, 2.0, lv, P))
check("§3 BO-02 the same close on 1.1x volume is not",
      not ps.broke_out(101.0, 1.1, lv, P))
bear = ps.Levels(trigger=100.0, invalidation=110.0, height=20.0, direction=ps.BEARISH)
check("§3 BO-02 is off for bearish breakouts", ps.broke_out(98.0, 0.5, bear, P))
check("§3 BO-06 bearish target is T - H", bear.target == 80.0)
check("§3 BO-03 a close below X voids", ps.voided(89.0, lv) and not ps.voided(95.0, lv))
check("§3 BO-04 expiry", ps.expired(P.max_wait + 1, P) and not ps.expired(P.max_wait - 1, P))

# §3.3 outcomes on a breakout that reaches target then gives half of it back
path = np.concatenate([np.full(50, 95.0), [101.0], np.linspace(101, 125, 30),
                       np.linspace(125, 112, 30)])
od = frame(path)
oc = ps.outcomes(od, 50, lv, P)
check("§3.3 hit_target recorded", oc.hit_target and oc.hit_day is not None)
check("§3.3 mfe/mae measured from the breakout close",
      oc.mfe > 20 and oc.mae <= 0, f"mfe={oc.mfe:.1f} mae={oc.mae:.1f}")
check("§3.3 ret_5/20/60 present when the horizon fits",
      all(v == v for v in (oc.ret_5, oc.ret_20, oc.ret_60)))
short = ps.outcomes(frame(path[:60]), 50, lv, P)
check("§3.3 a truncated window leaves ret_60 NaN rather than 0",
      short.ret_5 == short.ret_5 and short.ret_60 != short.ret_60)

# --------------------------------------------------- §4 cup, base case

cup_df = build_cup()
base = ps.detect_cup(cup_df)
check("§4 a textbook cup passes CH-01..CH-11", base["ok"], f"failed {base['fail']}")
if base["ok"]:
    m, lvl = base["metrics"], base["levels"]
    print(f"      depth {m['depth_pct']:.1f}%  cup {m['cup_days']}d  "
          f"handle {m['handle_depth_pct']:.1f}% over {m['handle_days']}d  "
          f"vol {m['handle_vol_ratio']:.2f}x  T={lvl.trigger:.2f} X={lvl.invalidation:.2f} "
          f"target={lvl.target:.2f}")
    check("§4 X is the handle low D", abs(lvl.invalidation - base["points"]["D"]["price"]) < 1e-9)
    check("§4 H is max(A, C) - B",
          abs(lvl.height - (max(base["points"]["A"]["price"], base["points"]["C"]["price"])
                            - base["points"]["B"]["price"])) < 1e-6)

# §13 pitfall 2: the breakout bar may not raise its own trigger
spiked = cup_df.copy()
spiked.iloc[-1, spiked.columns.get_loc("high")] = 500.0
after = ps.detect_cup(spiked)
check("§13 the trigger is frozen at t-1",
      after["ok"] and abs(after["levels"].trigger - base["levels"].trigger) < 1e-9,
      f"T moved to {after['levels'].trigger if after['ok'] else 'n/a'}")

# ------------------------------------------- §4 one mutation per rule

MUTATIONS = [
    ("CH-01", "no prior uptrend into A", dict(prior=0.05)),
    ("CH-02", "cup 60% deep", dict(depth=0.60)),
    # lip=0.70 would put C below B and change the cup's depth instead
    ("CH-03", "right lip 20% under the left", dict(lip=0.80)),
    ("CH-04", "cup only 20 days long", dict(left=10, right=10)),
    ("CH-05", "V-shaped bottom", dict(v_shape=True)),
    ("CH-06", "lopsided: the bottom sits against A", dict(left=8, right=110)),
    # a 30% handle would dig below B and redefine the cup; this one stays
    # inside CH-08's 3-12% and still finishes under the midpoint
    ("CH-07", "handle below the cup's midpoint",
     dict(depth=0.30, lip=0.95, handle_depth=0.115)),
    ("CH-08", "handle 2% deep", dict(handle_depth=0.02)),
    ("CH-09", "handle 60 days long", dict(handle_len=60)),
    ("CH-10", "handle wedges upward", dict(handle_shape="wedge_up")),
    ("CH-11", "handle volume 1.5x VOL50", dict(handle_vol=1.5)),
]
for rule, what, kw in MUTATIONS:
    r = ps.detect_cup(build_cup(**kw))
    hit = (not r["ok"]) and r["fail"] == rule
    check(f"§4 {rule} catches {what}", hit,
          f"got ok={r['ok']} fail={r['fail']}")

# the cup-without-handle variant drops CH-07..CH-11 and triggers at C
nh = ps.detect_cup(build_cup(handle_depth=0.02), require_handle=False)
check("§4 cup-without-handle ignores the handle rules and sets T = C",
      nh["ok"] and abs(nh["levels"].trigger - nh["points"]["C"]["price"]) < 1e-9,
      f"ok={nh['ok']} fail={nh['fail']}")

# --------------------------------------------- §5 doubles and triples

def build_double(*, direction: str = ps.BULLISH, prior: float = 0.30,
                 middle: float = 0.20, second: float = 0.005, span: int = 50,
                 tail: int = 16, second_vol: float = 0.6) -> pd.DataFrame:
    """A W (or an M), with knobs for each DB/DT rule.

    `tail` keeps the last point inside BO-04's window: the pattern completes
    k bars after it prints, and expires 20 bars later.
    """
    half = span // 2
    if direction == ps.BULLISH:
        B = 70.0
        pre = seg(B * (1 + prior), B, 130)
        C = B * (1 + middle)
        D = B * (1 - second)
        body = np.concatenate([seg(B, C, half), seg(C, D, span - half)])
        end = np.linspace(D, D * 1.08, tail)
    else:
        B = 100.0
        pre = seg(B / (1 + prior), B, 130)
        C = B * (1 - middle)
        D = B * (1 + second)
        body = np.concatenate([seg(B, C, half), seg(C, D, span - half)])
        end = np.linspace(D, D * 0.92, tail)
    close = np.concatenate([pre, body, end])
    vol = np.concatenate([
        np.full(len(pre) + half, 1_000_000.0),
        np.full(span - half, second_vol * 1_000_000.0),
        np.full(tail, 1_000_000.0),
    ])
    return frame(close, vol)


db = ps.detect_double_bottom(build_double())
check("§5.1 a textbook W passes DB-01..DB-04", db["ok"], f"failed {db['fail']}")
if db["ok"]:
    lvl, pts = db["levels"], db["points"]
    print(f"      B={pts['B']['price']:.2f} C={pts['C']['price']:.2f} "
          f"D={pts['D']['price']:.2f} sep={db['metrics']['separation_days']}d "
          f"state={db['state']} T={lvl.trigger:.2f} X={lvl.invalidation:.2f} "
          f"target={lvl.target:.2f}")
    check("§5.1 T is the middle peak C",
          abs(lvl.trigger - pts["C"]["price"]) < 1e-9)
    check("§5.1 H is C - min(B, D)",
          abs(lvl.height - (pts["C"]["price"] - min(pts["B"]["price"], pts["D"]["price"]))) < 1e-6)
    check("§5.1 X sits a tolerance below the lower bottom",
          lvl.invalidation < min(pts["B"]["price"], pts["D"]["price"]))

for rule, what, kw in [
    # prior=0.02 makes the run-in flat, and B disappears into the wick noise
    # instead of failing a rule — the decline has to be real but short of 20%
    ("DB-01", "only a 10% decline into B", dict(prior=0.10)),
    ("DB-02", "second bottom 15% below the first", dict(second=0.15)),
    ("DB-03", "middle peak only 5%", dict(middle=0.05)),
    ("DB-04", "bottoms 220 days apart", dict(span=220)),
]:
    r = ps.detect_double_bottom(build_double(**kw))
    check(f"§5.1 {rule} catches {what}", (not r["ok"]) and r["fail"] == rule,
          f"got ok={r['ok']} fail={r['fail']}")

heavy = ps.PatternParams(db_second_volume=True)
r = ps.detect_double_bottom(build_double(second_vol=1.6), heavy)
check("§5.1 DB-05 (opt-in) catches a heavier second bottom",
      (not r["ok"]) and r["fail"] == "DB-05", f"got fail={r['fail']}")
check("§5.1 DB-05 is off by default",
      ps.detect_double_bottom(build_double(second_vol=1.6))["ok"])

# O'Neil's W: prior UPTREND and a second low that undercuts by 0-5%
# the first draft had no first bottom at all: seg(50,70) then seg(70,84) is
# one unbroken rise, so the swing list held two points and no L,H,L run
# PT-01 and PT-02 are not mutually exclusive: a 22% pullback inside a longer
# uptrend satisfies BOTH. For the variant to be distinguishable the pullback
# has to stay under PT-02's 20%.
w_chart = frame(np.concatenate([
    seg(50, 90, 130),                      # an advance into the base
    seg(90, 76, 20),                       # B, a 15.6% pullback — not a downtrend
    seg(76, 85, 22), seg(85, 74.5, 22),    # C, then a second low 2% under B
    np.linspace(74.5, 80, 16),
]))
check("§5.1 O'Neil's W variant accepts an undercut inside an uptrend",
      ps.detect_double_bottom(w_chart, oneil_w=True)["ok"],
      f"fail={ps.detect_double_bottom(w_chart, oneil_w=True)['fail']}")
check("§5.1 the same chart fails the classic DB-01",
      ps.detect_double_bottom(w_chart)["fail"] == "DB-01")

dt = ps.detect_double_top(build_double(direction=ps.BEARISH))
check("§5.2 a textbook M passes DT-01..DT-04", dt["ok"], f"failed {dt['fail']}")
if dt["ok"]:
    check("§5.2 the double top is bearish and triggers on the middle trough",
          dt["levels"].direction == ps.BEARISH
          and abs(dt["levels"].trigger - dt["points"]["C"]["price"]) < 1e-9)
    check("§5.2 its target sits below the trigger", dt["levels"].target < dt["levels"].trigger)

triple = frame(np.concatenate([
    seg(100, 70, 130),
    seg(70, 84, 22), seg(84, 70.4, 22), seg(70.4, 83.6, 22), seg(83.6, 70.2, 22),
    np.linspace(70.2, 76, 16),
]))
tb = ps.detect_triple_bottom(triple)
check("§5 a triple bottom is detected", tb["ok"], f"fail={tb['fail']}")
if tb["ok"]:
    check("§5 its trigger is the HIGHER of the two middle peaks",
          abs(tb["levels"].trigger - max(tb["points"]["P1"]["price"],
                                         tb["points"]["P2"]["price"])) < 1e-9)

# ------------------------------------------- §6 head and shoulders

def build_hs(*, inverse: bool = False, prior: float = 0.60, head: float = 0.12,
             rs_off: float = 0.01, left: int = 25, right: int = 27,
             neck_drift: float = 0.005, shoulder_gap: float = 0.11,
             tail: int = 16) -> pd.DataFrame:
    """LS, N1, HD, N2, RS and the move away, with a knob per HS rule."""
    sign = 1 if not inverse else -1
    LS = 100.0
    neck = LS * (1 - sign * shoulder_gap)
    HD = LS * (1 + sign * head)
    N2 = neck * (1 + sign * neck_drift)
    RS = LS * (1 + sign * rs_off)
    pre = (seg(LS / (1 + prior), LS, 130) if not inverse
           else seg(LS * (1 + prior), LS, 130))
    close = np.concatenate([
        pre,
        seg(LS, neck, left // 2), seg(neck, HD, left - left // 2),
        seg(HD, N2, right // 2), seg(N2, RS, right - right // 2),
        np.linspace(RS, neck * (1 + sign * 0.02), tail),
    ])
    return frame(close)


hs = ps.detect_head_shoulders(build_hs())
check("§6.1 a textbook H&S top passes HS-01..HS-07", hs["ok"], f"failed {hs['fail']}")
if hs["ok"]:
    m, lvl, pts = hs["metrics"], hs["levels"], hs["points"]
    print(f"      LS={pts['LS']['price']:.2f} HD={pts['HD']['price']:.2f} "
          f"RS={pts['RS']['price']:.2f} neck(t)={m['neck_at_t']:.2f} "
          f"slope={m['neck_slope']:.5f}/day ratio={m['time_ratio']:.2f} "
          f"state={hs['state']}")
    check("§6.1 it is bearish, triggering on the neckline",
          lvl.direction == ps.BEARISH and abs(lvl.trigger - m["neck_at_t"]) < 1e-9)
    check("§6.1 X is the right shoulder",
          abs(lvl.invalidation - pts["RS"]["price"]) < 1e-9)
    check("§6.1 H is HD - neck(date of HD)", lvl.height > 0)

for rule, what, kw in [
    ("HS-01", "no prior uptrend into LS", dict(prior=0.02)),
    ("HS-02", "head only 1% above the shoulders", dict(head=0.01)),
    # -0.15 would put RS below the neckline, which deletes the right shoulder
    # swing entirely rather than making it an uneven one
    ("HS-03", "right shoulder 8% under the left", dict(rs_off=-0.08)),
    ("HS-04", "right side four times the left", dict(left=12, right=60)),
    # a rising neckline steep enough to fail would cross the head; a falling
    # one of the same steepness keeps the shape and still breaks HS-05
    ("HS-05", "neckline falling 0.6% per day", dict(neck_drift=-0.15)),
]:
    r = ps.detect_head_shoulders(build_hs(**kw))
    check(f"§6.1 {rule} catches {what}", (not r["ok"]) and r["fail"] == rule,
          f"got ok={r['ok']} fail={r['fail']}")

# HS-06 cannot fire at the default parameters — §2.1's 3% minimum swing size
# already guarantees a shoulder stands at least 3% off its neighbouring
# neckline point, and HS-05 caps how far the extended line can close that gap.
# The rule is still wired, which this proves by lowering the floor that blocks
# it; the unreachability itself is recorded in the module docstring.
loose = ps.PatternParams(min_swing_pct=1.0)
r = ps.detect_head_shoulders(build_hs(shoulder_gap=0.02), loose)
check("§6.1 HS-06 catches shoulders flush with the neckline (min_swing_pct=1%)",
      (not r["ok"]) and r["fail"] == "HS-06", f"got ok={r['ok']} fail={r['fail']}")
check("§6.1 HS-06 is unreachable at the default 3% minimum swing size",
      ps.detect_head_shoulders(build_hs(shoulder_gap=0.02))["fail"] != "HS-06")

ihs = ps.detect_head_shoulders(build_hs(inverse=True), inverse=True)
check("§6.2 an inverse H&S is detected", ihs["ok"], f"failed {ihs['fail']}")
if ihs["ok"]:
    check("§6.2 it is bullish, with the target above the neckline",
          ihs["levels"].direction == ps.BULLISH
          and ihs["levels"].target > ihs["levels"].trigger)
    check("§6.2 the head is the lowest of the three",
          ihs["points"]["HD"]["price"] < min(ihs["points"]["LS"]["price"],
                                             ihs["points"]["RS"]["price"]))

# ------------------------------------------------- §3 state transitions

stale = build_double(tail=70)        # completes, then sits for 50 more bars
r = ps.detect_double_bottom(stale)
check("§3 BO-04 voids a pattern that never broke out",
      (not r["ok"]) and r["state"] == ps.VOID, f"state={r['state']}")

broke = frame(np.concatenate([
    seg(100, 70, 130), seg(70, 84, 25), seg(84, 70.3, 25),
    np.linspace(70.3, 86.5, 14),          # straight up through C on the way
]), np.concatenate([np.full(180, 1_000_000.0), np.full(14, 2_500_000.0)]))
r = ps.detect_double_bottom(broke)
check("§3 BO-01+BO-02 mark a volume breakout CONFIRMED",
      r["ok"] and r["state"] == ps.CONFIRMED, f"state={r['state']} fail={r['fail']}")

# ------------------------------------------- §7-§10 boundary patterns

def zigzag(start: float, legs: list[tuple[float, int]]) -> np.ndarray:
    """A piecewise-linear path: each leg is (price to reach, bars to take)."""
    out, cur = [], start
    for price, bars in legs:
        out.append(np.linspace(cur, price, bars, endpoint=False))
        cur = price
    return np.concatenate(out)


def decaying(n: int, start: float = 2.0, end: float = 0.6) -> np.ndarray:
    return np.linspace(start, end, n) * 1_000_000.0


def build_triangle(*, top: float = 100.0, lows=(85.0, 90.0, 94.0), leg: int = 14,
                   lead: int = 60, vol_end: float = 0.6, tail: int = 4) -> pd.DataFrame:
    """An ascending triangle: flat resistance, rising lows."""
    legs: list[tuple[float, int]] = []
    for lo in lows:
        legs += [(lo, leg), (top, leg)]
    legs.append((lows[-1] + (top - lows[-1]) * 0.5, tail))
    close = np.concatenate([zigzag(60.0, [(top, lead)]), zigzag(top, legs)])
    return frame(close, decaying(len(close), 2.0, vol_end))


tri = ps.detect_triangle(build_triangle())
check("§7 an ascending triangle passes TR-01..TR-07", tri["ok"], f"failed {tri['fail']}")
if tri["ok"]:
    m = tri["metrics"]
    print(f"      kind={tri['kind']} touches={m['touches_upper']}+{m['touches_lower']} "
          f"dur={m['duration_days']}d apex={m['apex_progress']:.0%} "
          f"height={m['height_pct']:.1f}% T={tri['levels'].trigger:.2f}")
    check("§7.2 flat upper + rising lower classifies as ascending",
          tri["kind"] == ps.ASCENDING)
    check("§7.3 T is upper(t) for a bullish triangle",
          tri["levels"].direction == ps.BULLISH)

check("§7 TR-03 apex(): parallel lines have none",
      ps.apex(ps.fit_line([(0, 10.0), (10, 11.0)]), ps.fit_line([(0, 5.0), (10, 6.0)])) is None)
check("§7 TR-03 apex(): converging lines meet ahead",
      ps.apex(ps.fit_line([(0, 10.0), (10, 10.0)]), ps.fit_line([(0, 5.0), (10, 7.0)])) > 10)

for rule, what, kw in [
    ("TR-02", "only two touches in total", dict(lows=(85.0, 92.0), leg=30)),
    ("TR-06", "volume rising through the pattern", dict(vol_end=4.0)),
]:
    r = ps.detect_triangle(build_triangle(**kw))
    check(f"§7 {rule} catches {what}", (not r["ok"]) and r["fail"] == rule,
          f"got ok={r['ok']} kind={r.get('kind')} fail={r['fail']}")

# TR-04 and TR-07 cannot be failed by any chart at the default parameters, so
# they are exercised by moving the threshold onto a chart that passes:
#   * TR-04 — every anchor is tried, so a 300-day triangle simply yields a
#     shorter sub-window that satisfies the rule. Only the parameter can fail.
#   * TR-07 — §2.1 drops swings under 3% and TR-02 demands five touches, which
#     together force the initial height above 6% before the rule is reached.
r = ps.detect_triangle(build_triangle(), ps.PatternParams(tr_days=(15, 60)))
check("§7 TR-04 catches a triangle longer than its limit",
      (not r["ok"]) and r["fail"] == "TR-04", f"got fail={r['fail']}")
r = ps.detect_triangle(build_triangle(), ps.PatternParams(tr_min_height=25.0))
check("§7 TR-07 catches a triangle shorter than its minimum height",
      (not r["ok"]) and r["fail"] == "TR-07", f"got fail={r['fail']}")
check("§7 TR-04/TR-07 are unreachable at the default parameters",
      ps.detect_triangle(build_triangle())["ok"])

# §7.2 the other two classes, and §10's wedges, from the same classifier
flat_up = ps.fit_line([(0, 100.0), (50, 100.0)])
check("§7.2 descending = falling upper, flat lower",
      ps.classify_lines(ps.fit_line([(0, 110.0), (50, 100.0)]),
                        ps.fit_line([(0, 90.0), (50, 90.0)]), 25, P) == ps.DESCENDING)
check("§7.2 symmetrical = both converging at a similar rate",
      ps.classify_lines(ps.fit_line([(0, 110.0), (50, 102.0)]),
                        ps.fit_line([(0, 90.0), (50, 98.0)]), 25, P) == ps.SYMMETRICAL)
check("§7.2 a rectangle is two flat lines",
      ps.classify_lines(flat_up, ps.fit_line([(0, 90.0), (50, 90.0)]), 25, P) == ps.RECTANGLE)
check("§10 WG-01/02 rising wedge = both rising, lower faster",
      ps.classify_lines(ps.fit_line([(0, 100.0), (50, 105.0)]),
                        ps.fit_line([(0, 90.0), (50, 101.0)]), 25, P) == ps.RISING_WEDGE)
check("§10 WG-01/02 falling wedge = both falling, upper faster",
      ps.classify_lines(ps.fit_line([(0, 110.0), (50, 95.0)]),
                        ps.fit_line([(0, 100.0), (50, 96.0)]), 25, P) == ps.FALLING_WEDGE)
check("§10 lines diverging in opposite directions are none of them",
      ps.classify_lines(ps.fit_line([(0, 100.0), (50, 115.0)]),
                        ps.fit_line([(0, 95.0), (50, 80.0)]), 25, P) is None)

rect_chart = frame(np.concatenate([
    zigzag(60.0, [(100.0, 60)]),
    zigzag(100.0, [(88.0, 14), (100.0, 14), (88.2, 14), (99.8, 14), (88.1, 14), (94.0, 6)]),
]), decaying(60 + 76))
rc = ps.detect_rectangle(rect_chart)
check("§8.1 a rectangle passes RC-01..RC-04", rc["ok"], f"failed {rc['fail']}")
if rc["ok"]:
    check("§8.1 its trigger is the upper line and H the range",
          rc["levels"].trigger > rc["levels"].invalidation and rc["levels"].height > 0)

wedge_chart = frame(np.concatenate([
    zigzag(60.0, [(100.0, 60)]),
    zigzag(100.0, [(90.0, 14), (103.0, 14), (96.0, 14), (105.0, 14), (101.0, 14), (103.0, 5)]),
]), decaying(60 + 75))
wg = ps.detect_wedge(wedge_chart)
check("§10 a rising wedge is detected and is bearish",
      wg["ok"] and wg["kind"] == ps.RISING_WEDGE
      and wg["levels"].direction == ps.BEARISH, f"ok={wg['ok']} fail={wg['fail']}")

# ----------------------------------------------------- §8.2 flat base

def build_flat_base(*, advance: float = 0.40, depth: float = 0.08,
                    window: int = 45, below_high: float = 0.0) -> pd.DataFrame:
    top = 100.0 * (1 - below_high)
    base = top - np.abs(np.sin(np.linspace(0, 3 * np.pi, window))) * top * depth
    pre = zigzag(top / (1 + advance), [(top, 150)])
    after = np.concatenate([pre, base])
    if below_high:
        after = np.concatenate([zigzag(60.0, [(100.0, 60)]), zigzag(100.0, [(top, 40)]), base])
    return frame(after)


fb = ps.detect_flat_base(build_flat_base())
check("§8.2 a flat base passes FB-01..FB-04", fb["ok"], f"failed {fb['fail']}")
if fb["ok"]:
    m = fb["metrics"]
    print(f"      window={m['window_days']}d depth={m['depth_pct']:.1f}% "
          f"advance={m['prior_advance_pct']:.0f}% of52wk={m['pct_of_52w_high']:.0f}% "
          f"T={fb['levels'].trigger:.2f}")
    check("§8.2 the window search takes the LONGEST qualifying N",
          m["window_days"] >= 45)
    check("§8.2 H is the range, not the prior advance",
          abs(fb["levels"].height - (fb["levels"].trigger - fb["levels"].invalidation)) < 1e-9)

for rule, what, kw in [
    ("FB-01", "no prior advance", dict(advance=0.02)),
    ("FB-02", "a 25% range", dict(depth=0.25)),
    ("FB-04", "a base 30% under the 52-week high", dict(below_high=0.30)),
]:
    r = ps.detect_flat_base(build_flat_base(**kw))
    check(f"§8.2 {rule} catches {what}", (not r["ok"]) and r["fail"] == rule,
          f"got ok={r['ok']} fail={r['fail']}")

# -------------------------------------------------- §9 flags and HTF

def build_flag(*, gain: float = 0.30, pole_days: int = 12, flag_days: int = 16,
               retrace: float = 0.30, pole_vol: float = 2.0, flag_vol: float = 0.6,
               wild: bool = False, wedge: bool = False) -> pd.DataFrame:
    P0 = 50.0
    P1 = P0 * (1 + gain)
    low = P1 - (P1 - P0) * retrace
    pre = zigzag(P0 * 1.1, [(P0, 120)])
    pole = zigzag(P0, [(P1, pole_days)])
    # A pause has to OSCILLATE, or TL-01 has no swing points to fit lines to,
    # and the two lines have to stay roughly PARALLEL, or FL-04 reads the
    # shape as a wedge. Turning prices are derived from the channel geometry
    # (width w, per-leg drift s) so both hold by construction:
    #   upper: P1, P1 - 0.22R      lower: P1 - 0.78R, P1 - R
    # which puts the final low exactly on the requested retracement.
    q = max(4, flag_days // 4)
    R = P1 - low
    if wild:
        flag = zigzag(P1, [(low, q), (P1 * 1.04, flag_days - q)])
    else:
        drop = 3.0 if wedge else 1.0        # a lower line falling faster
        flag = zigzag(P1, [(P1 - 0.78 * R * drop, q), (P1 - 0.22 * R, q),
                           (P1 - R * drop, q), (P1 - R * drop * 0.97,
                                                flag_days - 3 * q)])
    close = np.concatenate([pre, pole, flag])
    vol = np.concatenate([
        np.full(len(pre), 1_000_000.0),
        np.full(len(pole), pole_vol * 1_000_000.0),
        (np.linspace(flag_vol * 0.35, flag_vol, len(flag)) if flag_vol > 1.5
         else np.linspace(flag_vol, flag_vol * 0.6, len(flag))) * 1_000_000.0,
    ])
    return frame(close, vol)


# FL-04 needs two swings per line inside a 5-20 bar pause, and §2.1 drops
# moves under 3%. A flag retracing 30% of a 30% pole oscillates by ~2%, so no
# line can be fitted and every one of them failed FL-04. Only a deep-ish flag
# on a big pole is detectable at the default min_swing_pct — recorded in the
# module docstring, and the reason this base case uses 0.40/0.45.
fl = ps.detect_flag(build_flag(gain=0.40, retrace=0.45, flag_days=20))
check("§9 a bull flag passes FP-01..FL-04", fl["ok"], f"failed {fl['fail']}")
if fl["ok"]:
    m = fl["metrics"]
    print(f"      kind={fl['kind']} pole={m['pole_gain_pct']:.0f}% in {m['pole_days']}d "
          f"flag={m['flag_days']}d retrace={m['retrace_pct']:.0f}% "
          f"rv={m['pole_rv']:.1f}x T={fl['levels'].trigger:.2f}")
    check("§9 H is the pole height",
          abs(fl["levels"].height - (fl["points"]["P1"]["price"]
                                     - fl["points"]["P0"]["price"])) < 1e-6)
    check("§9 X is the lowest low since P1",
          abs(fl["levels"].invalidation - fl["points"]["X"]["price"]) < 1e-9)

for rule, what, kw in [
    ("FP-01", "a 5% pole", dict(gain=0.05)),
    ("FP-02", "a pole that took 30 days", dict(pole_days=30)),
    ("FP-03", "a pole on below-average volume", dict(pole_vol=0.8)),
    ("FL-02", "a 70% retracement", dict(retrace=0.70)),
    ("FL-03", "volume rising through the pause", dict(flag_vol=4.0)),
    ("FL-04", "a pause whose lines are not parallel", dict(wedge=True, retrace=0.15)),
]:
    r = ps.detect_flag(build_flag(**{"gain": 0.40, "retrace": 0.45,
                                     "flag_days": 20, **kw}))
    check(f"§9 {rule} catches {what}", (not r["ok"]) and r["fail"] == rule,
          f"got ok={r['ok']} fail={r['fail']}")

htf = ps.detect_flag(build_flag(gain=1.30, pole_days=30, flag_days=18, retrace=0.15,
                                pole_vol=2.0), high_tight=True)
check("§9.3 a high tight flag passes HTF-01..HTF-04", htf["ok"], f"failed {htf['fail']}")
if htf["ok"]:
    check("§9.3 it carries no measured target", htf["levels"].height == 0.0)
r = ps.detect_flag(build_flag(gain=0.50, pole_days=30, flag_days=18), high_tight=True)
check("§9.3 HTF-01 catches a pole that only gained 50%",
      (not r["ok"]) and r["fail"] == "HTF-01", f"got fail={r['fail']}")
r = ps.detect_flag(build_flag(gain=1.30, pole_days=30, flag_days=18, retrace=0.55),
                   high_tight=True)
check("§9.3 HTF-03 catches a flag deeper than 25%",
      (not r["ok"]) and r["fail"] == "HTF-03", f"got fail={r['fail']}")

# --------------------------------------------------- §11 the scanner

def walk(scanner, symbol: str, d: pd.DataFrame, days: int) -> list:
    """Feed the last `days` bars one at a time, as §11's outer loop does."""
    seen = []
    for i in range(len(d) - days, len(d) + 1):
        seen = scanner.scan_day(symbol, d.iloc[:i])
    return seen


# a W that completes and then sits there: one instance, not one per bar
tracker = ps.PatternScanner()
chart = build_double(tail=30)
walk(tracker, "WWW", chart, 14)
dbs = [i for i in tracker.instances.values() if i.type == "double_bottom"]
check("§11 rule 1: re-detection updates one instance per anchor",
      len(dbs) == 1, f"{len(dbs)} instances")
if dbs:
    inst = dbs[0]
    print(f"      {inst.type} anchor={inst.anchor.date()} state={inst.state} "
          f"first_seen={inst.first_seen.date()} last_seen={inst.last_seen.date()}")
    check("§11 the instance keeps its original anchor and first_seen",
          inst.first_seen <= inst.last_seen and inst.anchor <= inst.first_seen)

# the same chart carried forward until BO-04 expires it
tracker2 = ps.PatternScanner()
walk(tracker2, "EXP", build_double(tail=70), 50)
expired_ = [i for i in tracker2.instances.values()
            if i.type == "double_bottom" and i.state == ps.VOID]
check("§11 BO-04 expires an instance that never broke out",
      len(expired_) >= 1, f"states={[i.state for i in tracker2.instances.values()]}")

# one that breaks out on volume, then runs: CONFIRMED, with §3.3 recorded
breakout_chart = frame(np.concatenate([
    seg(100, 70, 130), seg(70, 84, 25), seg(84, 70.3, 25),
    np.linspace(70.3, 86.0, 12), np.linspace(86.0, 104.0, 70),
]), np.concatenate([np.full(180, 1_000_000.0), np.full(82, 2_500_000.0)]))
tracker3 = ps.PatternScanner()
tracker3.scan_history("BO", breakout_chart)
conf = [i for i in tracker3.instances.values() if i.state == ps.CONFIRMED]
check("§11 a volume breakout is tracked to CONFIRMED", len(conf) >= 1,
      f"states={sorted({i.state for i in tracker3.instances.values()})}")
if conf:
    inst = max(conf, key=lambda i: i.breakout_on or pd.Timestamp.min)
    o = inst.outcome
    print(f"      {inst.type} broke out {inst.breakout_on.date()} "
          f"hit_target={o.hit_target if o else None} "
          f"mfe={o.mfe:.1f}% ret_20={o.ret_20:.1f}%" if o else "      no outcome")
    check("§11 §3.3 outcomes are attached to the confirmed instance",
          o is not None and o.mfe == o.mfe)
    check("§11 the breakout date is recorded once, not re-stamped each bar",
          inst.breakout_on is not None and inst.breakout_on <= inst.last_seen)

# §11 rule 3: the more specific label wins, and the other is kept and marked
insts = [ps.Instance(symbol="X", type=t, anchor=pd.Timestamp("2024-01-01"))
         for t in ("flag", "high_tight_flag", "rectangle", "flat_base")]
ps._apply_overlaps(insts)
by = {i.type: i for i in insts}
check("§11 rule 3: a high tight flag supersedes the bull flag",
      by["flag"].secondary_to == "high_tight_flag"
      and by["high_tight_flag"].secondary_to is None)
check("§11 rule 3: a flat base is primary over a rectangle",
      by["rectangle"].secondary_to == "flat_base")
check("§11 rule 3: the superseded instance is kept, not deleted", len(insts) == 4)

solo = [ps.Instance(symbol="X", type="flag", anchor=pd.Timestamp("2024-01-01"))]
ps._apply_overlaps(solo)
check("§11 rule 4: a label with no competitor stays primary",
      solo[0].secondary_to is None)

check("§11 anchor_of picks the pattern's first key point",
      ps.anchor_of({"points": {"B": {"date": pd.Timestamp("2024-02-02")},
                               "C": {"date": pd.Timestamp("2024-03-03")}}})
      == pd.Timestamp("2024-02-02"))

# the research table
rows = tracker3.rows()
check("§11 rows() returns one row per instance with its outcome columns",
      len(rows) == len([i for i in tracker3.instances.values()])
      and {"symbol", "type", "state", "hit_target", "ret_20"} <= set(rows.columns))

# no look-ahead: a day's scan can only see bars up to that day
peek = ps.PatternScanner()
cut = breakout_chart.iloc[:-40]
peek.scan_day("CUT", cut)
check("§11 a scan of day t cannot reference a later bar",
      all(i.last_seen <= cut.index[-1] for i in peek.instances.values()))

# ------------------------------------------------------- the noise floor

TRIALS = 120
noise_rng = np.random.default_rng(2024)
hits = 0
per_pattern: dict[str, int] = {}
for _ in range(TRIALS):
    walk = 100 * np.exp(np.cumsum(noise_rng.normal(0.0003, 0.018, 420)))
    n = len(walk)
    nd = pd.DataFrame(
        {
            "open": walk,
            "high": walk * (1 + noise_rng.uniform(0.001, 0.006, n)),
            "low": walk * (1 - noise_rng.uniform(0.001, 0.006, n)),
            "close": walk,
            "volume": noise_rng.lognormal(13.8, 0.35, n),
        },
        index=pd.bdate_range("2019-01-02", periods=n),
    )
    e = ind.enrich_daily(nd)
    hit_any = False
    for name, fn in (("cup", ps.detect_cup),
                     ("double bottom", ps.detect_double_bottom),
                     ("double top", ps.detect_double_top),
                     ("H&S top", ps.detect_head_shoulders),
                     ("inverse H&S", lambda f: ps.detect_head_shoulders(f, inverse=True)),
                     ("triangle", ps.detect_triangle),
                     ("rectangle", ps.detect_rectangle),
                     ("wedge", ps.detect_wedge),
                     ("flat base", ps.detect_flat_base),
                     ("flag", ps.detect_flag)):
        if fn(e)["ok"]:
            per_pattern[name] = per_pattern.get(name, 0) + 1
            hit_any = True
    hits += hit_any

# Measured 2026-10-09 over these 120 seeded walks: 35% matched something —
# H&S top 15.0%, double bottom 12.5%, double top 10.0%, inverse H&S 5.0%, cup
# 0.0%. The old `chart_patterns.py` put DBOT at 31% and VCP at 44%, with 75%
# matching something, so the §2 swing filter and the §2.4 context rules are
# doing most of the work. Ceilings are measured + ~5 points: regression
# guards, not targets.
# The flat base is the loosest of the ten by a distance: FB has no touch
# requirement, and FB-05's volume dry-up is off by default, so any quiet
# stretch of a random walk sitting near its own running high qualifies. That
# is worth knowing before trading one, and it is why the ceiling for it is
# high rather than why the detector is wrong.
CEILINGS = {"cup": 0.05, "inverse H&S": 0.10, "double top": 0.15,
            "rectangle": 0.15, "double bottom": 0.18, "H&S top": 0.20,
            "triangle": 0.20, "wedge": 0.20, "flag": 0.20, "flat base": 0.30}
print(f"\n      random-walk false positives over {TRIALS} walks "
      f"({hits / TRIALS * 100:.0f}% match something)")
for name, c in sorted(per_pattern.items(), key=lambda kv: -kv[1]):
    rate, ceiling = c / TRIALS, CEILINGS.get(name, 0.15)
    print(f"      {'ok   ' if rate <= ceiling else 'OVER '} {name:<14} "
          f"{rate * 100:5.1f}%  (ceiling {ceiling * 100:.0f}%)")
    if rate > ceiling:
        failures.append(
            f"the spec {name} fires on {rate * 100:.0f}% of random walks, over "
            f"its {ceiling * 100:.0f}% ceiling")
if hits / TRIALS > 0.70:
    failures.append(f"{hits / TRIALS * 100:.0f}% of random walks match something")

print()
if failures:
    print(f"{len(failures)} FAILURE(S):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("pattern_spec matches the spec on every rule checked.")
