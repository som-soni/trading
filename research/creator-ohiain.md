# @ohiain (X) — research notes

*Raw material, synthesized: what @ohiain teaches in four annotated diagrams on X
([x.com/ohiain](https://x.com/ohiain)), shared by the owner on 2026-11-17. The diagrams are schematic drawings,
not real charts, and carry no numbers. Everything below is **their** view unless marked otherwise. My inferences
are marked **[inferred]**. Where a claim was checked against stored prices, the check is shown.*

*What went where: the undercut-and-reclaim entry became a strategy spec,
[Undercut and reclaim](undercut-reclaim-spec.md) (draft 0), built as strategy `undercut_reclaim` v1.0. It is also listed as candidate setup L12 in
[Longs](system-swing-longs.md) §3. The EMA cycle in diagram 1 is Oliver Kell's, already built as `kell_cycle`
([spec](kell-cycle-spec.md)). The Learn guides are not updated yet.*

**In short**

- A swing trader of leading stocks who reads trend through the **9- and 21-day EMAs** and enters on structure:
  higher lows, pivots, undercuts.
- The central lesson: **stop buying the obvious breakout; buy strength after an undercut and reclaim** of
  support. The same stop distance then gives far more room to the breakout pivot.
- **Buy the right side**, never the falling knife: wait for the level to be undercut and reclaimed, or for the
  first bounce's high to break.
- **The higher low must hold the EMAs.** A pullback that loses them voids the setup, even if price later
  breaks out.
- The full trend cycle, wedge drop and 9/21 EMA crossback included, is Kell's cycle of price action in this
  creator's drawing.

---

## 0. Template

The same sections as every creator note (see [Martin Luk](creator-martin-luk.md) §0). Sections with nothing in
the source are kept, marked *not covered*, so creators can be compared side by side.

## 1. Style at a glance

| | |
|---|---|
| Horizon | Swing: days to weeks **[inferred]** from daily EMAs and "weekly" pivots |
| Direction | Long in the diagrams; the cycle diagram ends in a decline but marks no short |
| Instruments | Individual stocks, leaders in uptrends **[inferred]** |
| Core tools | 9/21-day EMAs, horizontal pivots (support pivot, weekly breakout pivot), higher lows/highs, volume against its average |
| Entry style | Early, anticipatory: inside the base, after an undercut and reclaim, or at a higher low on the EMAs. Not at the breakout |

## 2. How they read the market

*Not covered.* The diagrams are about a single stock; none shows an index or exposure rule.

## 3. What they trade

Stocks in an uptrend above rising 9/21 EMAs, building a base under a breakout pivot (diagrams 2 and 4). No screen,
sector or fundamental rule appears.

## 4. Setups

### D1 — The cycle: support, breakout, wedge drop, crossback (diagram 1)

A schematic of one full trend.

1. Price rises from a low and holds the **21 EMA as support**. A long green box marks the trade from there,
   with a small red box (the risk) under the support low.
2. A breakout on **above-average buying volume**.
3. A pullback holds the **9 EMA as support**: a second trade with a tighter red box.
4. The stock bases and makes a last high, also on above-average buying volume.
5. It then stalls in a rising wedge and falls out of it (**"wedge drop"**), and the 9 EMA rolls under the 21.
6. A bounce back up to the EMAs fails (**"9/21 EMA crossback"**): the EMAs are now resistance. **Above-average
   selling volume** follows, and the shaded boxes now mark short-side risk and reward **[inferred]**.

The words are Oliver Kell's: wedge pop, EMA crossback, wedge drop. See the [Kell spec](kell-cycle-spec.md).

### D2 — Undercut and reclaim, not the obvious breakout (diagram 2)

The headline: *"STOP buying the OBVIOUS breakout… START buying the STRENGTH after the UNDERCUT + RECLAIM."*

1. A stock in an uptrend (9/21 EMAs rising) ranges between a **support pivot** and a **weekly breakout pivot**.
   Support is tested twice.
2. Price dips **under the support pivot** for a few bars, its low meeting the rising EMAs, then **reclaims** it.
3. It makes a higher high (HH), a pullback to a higher low (HL), and a break of that HH. The trade box starts
   at the reclaim, with the risk (red) a thin strip from the undercut low up to support.
4. Price later reaches the weekly pivot and pops through it (the grey circle, "the obvious breakout"). It
   rallies a little more, then reverses back under the pivot and the EMAs.

The point **[inferred]**: the entry after the reclaim sits near the bottom of the base. Its stop, under the
undercut low, is a few percent away, and the reward room is the whole base height. The breakout buyer pays the
top of the base and, in the drawing, is caught by the reversal.

### D3 — Buy the right side (diagram 3)

Two sketches at a **weekly pivot**:

- ✗ Price falls straight into the pivot and is bought there, with the stop under it. This is the falling knife.
- ✓ Price falls **through** the pivot, turns, and comes back above it. **1st entry:** the reclaim of the pivot,
  stop under the undercut low. **2nd entry:** the break of the first bounce's high after a higher low. The
  second entry's risk box is smaller, and it starts higher.

### D4 — The higher low on the EMAs (diagram 4)

Three versions of the same higher high, pullback and breakout pivot:

| Panel | Pullback | Entry | Verdict |
|---|---|---|---|
| Left | A higher low that **holds the EMAs** (green arc) | At the higher low as it turns up ("focus here") | ✓ ✓ |
| Middle | The same good higher low | At the breakout pivot instead | ✓ setup, ✗ entry: late, wider risk |
| Right | The pullback **loses the EMAs** (red arc), then rallies through the pivot anyway | — | ✗ ✗: not a setup, even though it worked |

## 5. Execution

- Enter on **strength after confirmation**: the reclaim close or the break of the bounce high, never a resting
  bid into a falling stock (D3).
- Two-step entry (D3): a first tranche at the reclaim, a second at the higher-high break. Whether these are
  adds or alternatives is not said **[unclear]**.
- Do not chase the obvious breakout of the weekly pivot (D2, D4 middle).

## 6. Risk and sizing

- The stop goes **under the undercut low** (D2, D3) or **under the higher low** (D4). In every diagram the red
  box is small against the green: the method is built on a tight stop **[inferred]**.
- No position size or account-risk figure is given.

## 7. Management and exits

- Stay with the trade while the 9/21 EMAs hold as support (D1).
- The trend is over at a **wedge drop and a failed 9/21 EMA crossback**, confirmed by above-average selling
  volume (D1).
- The D2 box ends at the high just after the breakout. It is not said whether that is a target, a sale into
  strength, or a stop raised under the EMAs **[unclear]**.

## 8. Process

*Not covered.*

## 9. Nuances worth keeping

- **Judge the setup, not the outcome.** D4's right panel goes up but is still ✗, because the higher low lost
  the EMAs.
- **The undercut and the EMA hold work at different scales.** On daily bars, a dip under a six-week base's
  low almost never keeps the 21-day EMA. Over 2013–2021, eight leaders in stored data gave no case with a
  30-session base, and none with a 60-session one. Holding a slow line instead, the 100-day EMA as a stand-in
  for the weekly 21, gave 20 cases. The "weekly pivot" wording fits that **[inferred]**: the base and its
  support are weekly-chart features; the 9/21 EMAs govern the daily higher low (D4). See the
  [spec](undercut-reclaim-spec.md) §3.
- **The drawings are chosen to make the point.** In D2 the obvious breakout fails. Breakouts from proper bases
  are the core entry of O'Neil and Minervini; the defensible claim is *cheaper risk*, not *breakouts fail*.

## 10. How it compares

| Idea | Here | Nearest elsewhere |
|---|---|---|
| EMA cycle, wedge drop | D1 | Kell's cycle of price action (`kell_cycle`) |
| Undercut and reclaim of support | D2, D3 | Wyckoff's spring (`wyckoff_spring`); Minervini's shakeout (`minervini` S9) and his "failure reset" (L5 in [Longs](system-swing-longs.md)); O'Neil's W-bottom undercut |
| 2nd entry over the bounce high | D3 | Sperandeo's 1-2-3 (`one_two_three`) |
| Higher low on the EMAs | D4 | Kell's EMA crossback (`kell_cycle` S2); 21-EMA pullback (`ema_pullback`) |

What differs: Wyckoff's spring comes after a decline and Minervini's shakeout is bought at the base's high. Here
the undercut sits **inside an uptrend's base** and is bought **on the reclaim**, well before the pivot.

## 11. Open questions

- Is the support pivot a daily or a weekly level? D3 says weekly, D2 shows only daily-looking swings.
- Are the 1st and 2nd entries two tranches of one position, or a choice?
- What is the exit after the breakout: a target, a partial sale, or an EMA trail?
- Does a volume rule apply to the reclaim? D1 stresses volume; D2–D4 do not show it.

## 12. Source log

| # | Diagram | Shared | Content |
|---|---|---|---|
| 1 | The cycle, 9/21 EMAs and volume | 2026-11-17 | 21 EMA support, above-average buying volume, 9 EMA support, wedge drop, 9/21 EMA crossback, above-average selling volume |
| 2 | "STOP buying the OBVIOUS breakout" | 2026-11-17 | Support pivot, weekly B/O pivot, undercut, reclaim, HH/HL, entry box |
| 3 | "How to BUY the RIGHT side" | 2026-11-17 | Weekly pivot; ✗ buying the fall, ✓ undercut, reclaim; 1st and 2nd entries |
| 4 | HH / HL / b/o pivot, three panels | 2026-11-17 | The higher low on the EMAs; ✓ early, ✗ at the pivot, ✗ when the EMAs are lost |

All four carry the "@ohiain on X" mark. No dates or tickers are given on the diagrams.
