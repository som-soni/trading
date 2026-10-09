# Chart Pattern Detection — Programmatic Specification

Oct 9, 2026 · @Som Soni

## 1. Purpose and scope

This spec defines the most widely used classic chart patterns as rules a computer can detect on daily price and volume data. It is a companion to the Minervini VCP backtest spec: a pattern found here can be passed to that spec's Trend Template, VCP checks, entries and exits, or tested on its own with the shared breakout rules in Section 3.

Every pattern is specified the same way, in this order:

1. **Key points.** The swing highs and lows that make up the pattern, labelled with letters (A, B, C…) in time order.
2. **Context.** The trend that must come before the pattern, because the same shape means different things after a rise and after a fall.
3. **Geometry.** Rules on the prices, depths, durations and slopes connecting the key points.
4. **Volume.** Rules on how volume should behave, where the textbook descriptions require it.
5. **Trigger, invalidation and target.** The level whose break confirms the pattern, the level that cancels it, and the price objective.

The patterns are grouped by family. Sections 4 to 6 cover patterns built from a few distinct swing points (cup with handle, double tops and bottoms, head and shoulders). Sections 7 to 10 cover patterns built from two boundary lines (triangles, rectangles, flags and pennants, wedges).

Chart patterns have no single official definition. Where a threshold comes from a widely used source, such as William O'Neil's descriptions of the cup with handle or Thomas Bulkowski's pattern statistics, the spec says so. Every other number is marked **[assumption]** and listed in Section 12 so that you can test alternatives. As in the VCP spec, prices are split- and bonus-adjusted, and every rule uses only data up to the close of the day being evaluated, day t.

## 2. Shared building blocks

All patterns are built from the same five tools. Defining them once keeps the pattern rules short and consistent.

### 2.1 Swing points

Use the same confirmed swing points as the VCP spec. A bar is a swing high if its high is the highest of the k bars before and after it, and a swing low is defined the same way using lows. A swing point at bar i only becomes known at the close of bar i + k.

Two extra rules make swing points usable for patterns:

1. **Alternation.** The list of swing points must alternate high, low, high, low. If two highs appear in a row, keep the higher one; if two lows appear in a row, keep the lower one.
2. **Minimum swing size.** Drop any swing whose move from the previous swing point is smaller than max(min_swing_pct, atr_mult × ATR14 / close). The default is max(3%, 1.5 × ATR14 / close) **[assumption]**. Using ATR means a volatile stock needs a larger move to count as a swing.

Patterns appear at different sizes. Run the detector at two scales: a **minor** scale with k = 3 for flags, pennants and handles, and a **major** scale with k = 8 for cups, double tops and bottoms, and head and shoulders **[assumption]**.

### 2.2 Price tolerance

Many rules say two prices are "about equal", such as two bottoms of a double bottom. Two prices p1 and p2 are **equal within tolerance** when:

```latex
\frac{|p_1 - p_2|}{(p_1 + p_2)/2} \le tol
```

The default is tol = max(3%, 0.75 × ATR14 / close) **[assumption]**.

### 2.3 Trendlines

Boundary patterns (Sections 7 to 10) need an upper line through swing highs and a lower line through swing lows.

| ID | Rule | Default |
| --- | --- | --- |
| TL-01 | Fit each line by least squares through its swing points | At least 2 points; at least 3 touches in total across both lines |
| TL-02 | A touch is a swing point within tol of the line | tol from 2.2 |
| TL-03 | Containment: no close lies beyond either line by more than tol before the breakout | Required |
| TL-04 | Slope is measured as percent per day: slope ÷ line value at the pattern's midpoint | — |
| TL-05 | A line is **flat** if its absolute slope is at most flat_slope | 0.05% per day **[assumption]** |

### 2.4 Prior trend

The trend before the pattern's first point A decides whether the pattern is a continuation or a reversal.

| ID | Rule | Default |
| --- | --- | --- |
| PT-01 | Prior uptrend: price at A is at least prior_move above the lowest low of the prior_window days before A | prior_move = 20%, prior_window = 120 days **[assumption]** |
| PT-02 | Prior downtrend: price at A is at least prior_move below the highest high of the prior_window days before A | Same defaults |

### 2.5 Volume

Volume rules use VOL50, the 50-day average volume measured on the day before the pattern starts, so the pattern's own volume does not distort the baseline. Relative volume is RV(t) = volume(t) ÷ VOL50. "Volume declines through the pattern" means the slope of a straight line fitted to log(volume) over the pattern's days is negative.

## 3. Shared rules: breakout, invalidation and targets

Every pattern in Sections 4 to 10 defines three levels: a **trigger** (T), an **invalidation level** (X), and a **height** (H). The rules below then apply to all of them, so each pattern section only needs to say what T, X and H are.

### 3.1 Pattern states

A detected pattern moves through these states in order. Storing the state makes the scanner easy to debug and lets you study patterns that never broke out.

1. **Forming:** some key points exist, but not all.
2. **Complete:** all key points are confirmed and all geometry rules pass. The pattern is waiting for a breakout.
3. **Confirmed:** price has broken through T under BO-01 and BO-02.
4. **Failed:** after confirmation, price closed back through T under BO-05.
5. **Void:** before confirmation, price broke X, or the pattern expired under BO-04.

### 3.2 Rules

| ID | Rule | Default |
| --- | --- | --- |
| BO-01 | Breakout: for a bullish pattern, close(t) > T × (1 + bo_buffer); for a bearish pattern, close(t) < T × (1 − bo_buffer) | bo_buffer = 0.5% **[assumption]** |
| BO-02 | Breakout volume: RV(t) ≥ bo_vol | 1.4 for bullish breakouts **[assumption]**; off for bearish breakouts, which often occur without a volume surge |
| BO-03 | Void before breakout: a close beyond X | Required |
| BO-04 | Expiry: no breakout within max_wait days of completion (boundary patterns use their own limit) | 20 days **[assumption]** |
| BO-05 | Failure after breakout: within fail_days, a close back through T by more than tol | 10 days **[assumption]** |
| BO-06 | Measured target: bullish T + H; bearish T − H | The standard textbook "measured move" |

### 3.3 Outcomes to record

For every confirmed pattern, record the following over a fixed horizon after the breakout, for example 60 trading days **[assumption]**. These are the raw material for testing which patterns and parameters work:

| Field | Meaning |
| --- | --- |
| hit_target | Whether price reached the BO-06 target within the horizon, and on which day |
| mfe | Maximum favourable excursion: the best price reached, as a % of the breakout close |
| mae | Maximum adverse excursion: the worst price reached, as a % of the breakout close |
| throwback | Whether price returned to within tol of T after the breakout (bullish), or pulled back to T (bearish) |
| failed | Whether BO-05 fired |
| ret_5, ret_20, ret_60 | Return from the breakout close after 5, 20 and 60 days |

## 4. Cup with handle (bullish continuation)

The cup with handle is a rounded, U-shaped base followed by a small, shallow pullback near the top. Most thresholds below follow William O'Neil's descriptions; the rules that turn "rounded" into numbers are assumptions.

### Key points

| Point | Definition |
| --- | --- |
| A | Left lip: a major-scale swing high |
| B | Cup bottom: the lowest low between A and C |
| C | Right lip: the first major-scale swing high after B that satisfies CH-03 |
| D | Handle low: the lowest low after C, using minor-scale swings |

### Rules

| ID | Rule | Default |
| --- | --- | --- |
| CH-01 | Context: prior uptrend into A (PT-01) | prior_move = 30% (O'Neil) |
| CH-02 | Cup depth: (A − B) ÷ A | 12% to 33% (O'Neil); test up to 50% in weak markets |
| CH-03 | Right lip near the left lip: 0.85 × A ≤ C ≤ 1.03 × A | **[assumption]** |
| CH-04 | Cup duration: days from A to C | 35 to 325 days, about 7 to 65 weeks (O'Neil) |
| CH-05 | Rounded bottom, not a V: at least max(5, 15% of the cup's days) have a low inside the bottom third of the cup's range | **[assumption]** |
| CH-06 | Balanced sides: the days from A to B and from B to C are each at least 25% of the cup's duration | **[assumption]** |
| CH-07 | Handle in the upper half of the cup: D ≥ B + 0.5 × (A − B) | O'Neil |
| CH-08 | Handle depth: (C − D) ÷ C | 3% to 12% (O'Neil cites 8–12% as typical) |
| CH-09 | Handle duration: days from C to day t | 5 to 25 days (at least one week, per O'Neil) |
| CH-10 | Handle drifts down or sideways: the slope of a line fitted to the handle's closes is at most 0 | O'Neil warns against handles that wedge upward |
| CH-11 | Volume dries up in the handle: average handle volume ≤ 0.8 × VOL50 | **[assumption]** |

### Trigger, invalidation and height

| Level | Definition |
| --- | --- |
| T (trigger) | The highest high of the handle, which O'Neil calls the pivot point |
| X (invalidation) | The handle low D |
| H (height) | max(A, C) − B |

A **cup without a handle** can be tested as a variant: drop CH-07 to CH-11 and set T = C. Expect more failed breakouts, because there is no handle to shake out weak holders.

## 5. Double bottom and double top

A double bottom is a "W": two lows at about the same price with a peak between them. A double top is the mirror image, an "M". Both use major-scale swing points. The double bottom is described first; the double top reverses every comparison.

### 5.1 Double bottom (bullish)

| Point | Definition |
| --- | --- |
| B | First bottom: a major-scale swing low |
| C | Middle peak: the highest high between B and D |
| D | Second bottom: the next major-scale swing low after C |

| ID | Rule | Default |
| --- | --- | --- |
| DB-01 | Context: prior downtrend into B (PT-02) for the classic reversal | prior_move = 20% **[assumption]** |
| DB-02 | Bottoms about equal: B and D equal within tol (Section 2.2) | tol default |
| DB-03 | Middle peak high enough: (C − min(B, D)) ÷ min(B, D) ≥ min_peak | 10% **[assumption]** |
| DB-04 | Bottoms far enough apart: days from B to D | 20 to 150 days **[assumption]**; Edwards and Magee suggest at least about a month |
| DB-05 | Optional: lighter volume at the second bottom. Average volume over the 5 days centred on D is below that around B | Off by default |

| Level | Definition |
| --- | --- |
| T | The middle peak C |
| X | min(B, D) × (1 − tol) |
| H | C − min(B, D) |

**O'Neil's "W" base variant.** O'Neil uses a double bottom as a continuation base inside an uptrend, and he prefers the second low to slightly undercut the first. To test this version, replace DB-01 with PT-01 (a prior uptrend into the high before B), and replace DB-02 with: D is 0% to 5% below B **[assumption]**. The trigger stays at C.

### 5.2 Double top (bearish)

The double top uses the same rules with every comparison reversed:

| ID | Rule | Default |
| --- | --- | --- |
| DT-01 | Context: prior uptrend into B (PT-01) | prior_move = 20% **[assumption]** |
| DT-02 | Two peaks B and D equal within tol | tol default |
| DT-03 | Middle trough C deep enough: (max(B, D) − C) ÷ max(B, D) ≥ min_peak | 10% **[assumption]** |
| DT-04 | Peaks far enough apart: days from B to D | 20 to 150 days **[assumption]** |

| Level | Definition |
| --- | --- |
| T | The middle trough C; the pattern confirms on a close below it |
| X | max(B, D) × (1 + tol) |
| H | max(B, D) − C |

**Triple bottoms and tops** are the same pattern with a third swing point. Require all three bottoms (or tops) to be equal within tol, and set T to the higher of the two middle peaks (or the lower of the two middle troughs).

## 6. Head and shoulders (top and inverse)

A head and shoulders top is three peaks with the middle one highest, sitting on a support line called the neckline. It is a bearish reversal. The inverse head and shoulders is the mirror image at a bottom and is bullish. The top is described first.

### 6.1 Head and shoulders top (bearish)

The pattern is five consecutive major-scale swing points, alternating high and low:

| Point | Definition |
| --- | --- |
| LS | Left shoulder: a swing high |
| N1 | Left neckline point: the swing low after LS |
| HD | Head: the swing high after N1 |
| N2 | Right neckline point: the swing low after HD |
| RS | Right shoulder: the swing high after N2 |

The **neckline** is the straight line through N1 and N2, extended to the right. Its value on any day is written neck(t).

| ID | Rule | Default |
| --- | --- | --- |
| HS-01 | Context: prior uptrend into LS (PT-01) | prior_move = 20% **[assumption]** |
| HS-02 | Head clearly highest: HD ≥ (1 + min_head) × max(LS, RS) | min_head = 3% **[assumption]** |
| HS-03 | Shoulders similar in height: LS and RS equal within shoulder_tol | 2 × tol **[assumption]** |
| HS-04 | Shoulders similar in time: (days from HD to RS) ÷ (days from LS to HD) between 0.5 and 2.0 | **[assumption]** |
| HS-05 | Neckline not too steep: absolute neckline slope ≤ max_neck_slope | 0.3% per day **[assumption]** |
| HS-06 | Shoulders stand out from the neckline: LS and RS are each at least min_shoulder above neck at their dates | 3% **[assumption]** |
| HS-07 | Duration from LS to RS | 20 to 250 days **[assumption]** |
| HS-08 | Optional classic volume: average volume on the rise into HD is below that on the rise into LS | Off by default |

| Level | Definition |
| --- | --- |
| T | neck(t), the neckline's value on day t. A close below it confirms the pattern |
| X | A close above RS voids the pattern |
| H | HD − neck(date of HD) |

### 6.2 Inverse head and shoulders (bullish)

Use the same five points with highs and lows swapped: LS, HD and RS are swing lows, and N1 and N2 are swing highs. Reverse every comparison in HS-01 to HS-07, so the context is a prior downtrend (PT-02), the head is the lowest low, and the shoulders sit below the neckline. The trigger is a close above neck(t), BO-02's volume rule applies because the breakout is bullish, X is a close below RS, and H = neck(date of HD) − HD.

## 7. Triangles: ascending, descending and symmetrical

A triangle is two converging trendlines that contain price. All three types share the rules in 7.1. They differ only in the slopes of the two lines, which 7.2 uses to classify them.

### 7.1 Shared triangle rules

The pattern starts at the first swing point touching either line, called S, and is evaluated on day t. The **apex** is the date where the two lines would meet.

| ID | Rule | Default |
| --- | --- | --- |
| TR-01 | Lines fitted under TL-01 to TL-03, using minor-scale swings for patterns under 40 days and major-scale swings otherwise | **[assumption]** |
| TR-02 | Enough touches: at least 2 on each line and at least 5 in total, alternating between the lines | 5 total (Bulkowski uses at least 5 touches) |
| TR-03 | The lines converge: the apex is after day t | Required |
| TR-04 | Duration from S to day t | 15 to 200 days **[assumption]** |
| TR-05 | Breakout timing: the breakout happens between 50% and 80% of the distance from S to the apex | Edwards and Magee describe breakouts in roughly this zone **[assumption on exact bounds]** |
| TR-06 | Volume declines through the pattern: the slope of log(volume) from S to t is negative | Required |
| TR-07 | Initial height: upper(S) − lower(S) is at least min_height of price | 6% **[assumption]** |

### 7.2 Classification by slope

The three types are listed from the most bullish bias to the most bearish. "Flat", "rising" and "falling" use the flat_slope threshold from TL-05.

| Type | Upper line | Lower line | Usual bias |
| --- | --- | --- | --- |
| Ascending | Flat | Rising | Bullish |
| Symmetrical | Falling | Rising, and the two slopes differ in size by no more than a factor of 2 **[assumption]** | Neutral; often continues the prior trend |
| Descending | Falling | Flat | Bearish |

If both lines slope the same way, the pattern is a wedge (Section 10), not a triangle. If both are flat, it is a rectangle (Section 8).

### 7.3 Trigger, invalidation and height

A triangle can break either way, so record both directions and label each breakout with the triangle's type.

| Level | Definition |
| --- | --- |
| T, bullish | upper(t). A close above it confirms an upward breakout |
| T, bearish | lower(t). A close below it confirms a downward breakout |
| X | Reaching 80% of the way to the apex without a breakout (TR-05); the pattern is void |
| H | The initial height, upper(S) − lower(S). The target is the breakout price ± H |

## 8. Rectangles and flat bases

Both patterns are sideways ranges with roughly horizontal boundaries. They differ in what defines them. A rectangle is defined by repeated touches of two flat lines and can break either way. A flat base is O'Neil's continuation pattern, defined simply by a shallow range after an advance; it does not need repeated touches.

### 8.1 Rectangle

| ID | Rule | Default |
| --- | --- | --- |
| RC-01 | Both lines are flat under TL-05 | flat_slope default |
| RC-02 | Enough touches: at least 2 on each line and at least 4 in total | **[assumption]** |
| RC-03 | Range height: (upper − lower) ÷ lower | 5% to 25% **[assumption]** |
| RC-04 | Duration from the first touch to day t | 20 to 250 days **[assumption]** |

| Level | Definition |
| --- | --- |
| T, bullish | The upper line |
| T, bearish | The lower line |
| X | None before breakout; a close beyond either line is a breakout in that direction |
| H | upper − lower |

### 8.2 Flat base (bullish continuation)

The flat base is evaluated over a window of the last N days ending on day t.

| ID | Rule | Default |
| --- | --- | --- |
| FB-01 | Context: prior uptrend of at least prior_move into the start of the window (PT-01) | 20% (O'Neil describes flat bases forming after a 20% or larger advance) |
| FB-02 | Shallow range: (max high − min low) ÷ max high over the window | At most 15% (O'Neil) |
| FB-03 | Long enough: window length N | At least 25 days, about 5 weeks (O'Neil) |
| FB-04 | Range sits near the highs: max high of the window ≥ 0.95 × HI52 | **[assumption]** |
| FB-05 | Optional: volume dries up, average volume in the last 10 days ≤ 0.8 × VOL50 | Off by default |

To find the window, take the longest N (from 25 up to 120 days) for which FB-02 still holds. This captures the full base instead of only its last few weeks.

| Level | Definition |
| --- | --- |
| T | The window's max high |
| X | The window's min low |
| H | Max high − min low |

A flat base that also shows shrinking pullbacks qualifies as a VCP as well, so it can be passed to the VCP spec.

## 9. Flags, pennants and the high tight flag

These are short pauses after a sharp move. Each has two parts: a **flagpole**, which is the sharp move, and a **flag**, which is the pause. The bull versions are described here; bear versions reverse every direction. All three use minor-scale swing points.

### 9.1 The flagpole

The pole runs from P0, the lowest low before the move, to P1, the highest high at the end of the move.

| ID | Rule | Default |
| --- | --- | --- |
| FP-01 | Steep rise: (P1 − P0) ÷ P0 ≥ pole_gain | 15% **[assumption]** |
| FP-02 | Fast: days from P0 to P1 ≤ pole_days | 15 days **[assumption]** |
| FP-03 | Strong volume: average RV over the pole ≥ 1.3 | **[assumption]** |

### 9.2 Flag and pennant

The pause starts at P1 and is evaluated on day t. It is fitted with an upper and a lower line, as in Section 2.3. The two patterns differ only in the lines' shape: a flag is a small channel with parallel lines, and a pennant is a small triangle with converging lines.

| ID | Rule | Default |
| --- | --- | --- |
| FL-01 | Short pause: days from P1 to t | 5 to 20 days (Bulkowski describes these as lasting up to about three weeks) |
| FL-02 | Shallow retracement: (P1 − lowest low since P1) ÷ (P1 − P0) | At most 50% **[assumption]** |
| FL-03 | Volume declines through the pause (log-volume slope < 0) | Required |
| FL-04, flag | Both lines slope down or are flat, and their slopes differ by no more than a factor of 2 (roughly parallel) | **[assumption]** |
| FL-04, pennant | Upper line falling, lower line rising (converging), with the apex after day t | Required |

| Level | Definition |
| --- | --- |
| T | upper(t), the flag's or pennant's upper line on day t |
| X | The lowest low since P1 |
| H | The pole height, P1 − P0. The target is the breakout price + H |

### 9.3 High tight flag

The high tight flag is a rare, extreme version of the bull flag that both O'Neil and Minervini single out. It replaces the pole and pause rules above with these:

| ID | Rule | Default |
| --- | --- | --- |
| HTF-01 | Pole: price at least doubles, P1 ≥ 2 × P0 | 100% (O'Neil) |
| HTF-02 | Pole duration: days from P0 to P1 | 20 to 40 days, about 4 to 8 weeks (O'Neil) |
| HTF-03 | Flag depth: (P1 − lowest low since P1) ÷ P1 | At most 25% (O'Neil cites 10–25%) |
| HTF-04 | Flag duration: days from P1 to t | 15 to 25 days, about 3 to 5 weeks (O'Neil) |

For the high tight flag, T is the highest high of the flag (often P1), X is the flag's low, and H is not used, because the textbook descriptions give no measured target for it.

## 10. Wedges: rising and falling

A wedge is like a triangle, but both lines slope in the same direction while converging. The textbook reading is that a rising wedge tends to break down and a falling wedge tends to break up, because the trend inside the wedge is losing strength. Wedges reuse the triangle rules TR-01 to TR-07 from Section 7.1, then add the slope rules below.

| ID | Rule | Rising wedge | Falling wedge |
| --- | --- | --- | --- |
| WG-01 | Both lines slope the same way | Both rising beyond flat_slope | Both falling beyond flat_slope |
| WG-02 | The lines converge | The lower line rises faster than the upper line | The upper line falls faster than the lower line |
| WG-03 | Usual bias | Bearish | Bullish |

| Level | Rising wedge | Falling wedge |
| --- | --- | --- |
| T (expected direction) | lower(t); a close below it confirms | upper(t); a close above it confirms |
| X | Reaching 80% of the way to the apex without a breakout | Same |
| H | The initial height, upper(S) − lower(S) | Same |

As with triangles, record breakouts in both directions. Edwards and Magee note that a wedge often retraces the whole wedge after breaking out, so an alternative target to test is the price at the wedge's start S **[assumption to test]**.

## 11. Scanner pseudocode and overlapping detections

The scanner runs once per stock per day. It updates swing points first, then the patterns already being tracked, and only then looks for new patterns. This order prevents the same pattern from being counted twice.

```
for each trading day t:
  for each stock in the universe:

    # 1. Swing points (Section 2.1), confirmed only up to bar t - k
    update minor swings (k = 3) and major swings (k = 8)

    # 2. Update patterns already tracked for this stock
    for each pattern p with state in {forming, complete, confirmed}:
        p.update_points(t)              # e.g. a new handle low, a new touch
        if p.state in {forming, complete}:
            if not p.geometry_ok(t):   p.state = void
            elif closes_beyond(p.X, t): p.state = void          # BO-03
            elif breakout(p, t):        p.state = confirmed      # BO-01, BO-02
            elif expired(p, t):         p.state = void          # BO-04
            elif p.all_points_ready():  p.state = complete
        elif p.state == confirmed:
            if failed(p, t):            p.state = failed        # BO-05
            record outcomes (Section 3.3) until the horizon ends

    # 3. Look for new patterns
    for each detector in [cup_handle, double_bottom, double_top, hs_top,
                          hs_inverse, triangle, rectangle, flat_base,
                          flag_pennant, high_tight_flag, wedge]:
        for each candidate found by detector using swings known at t:
            key = (stock, detector.type, candidate.anchor_date)
            if key not already tracked:
                track candidate with state = forming
```

### Handling overlapping detections

The same price action often matches more than one pattern. These rules are applied in order, from the one that removes the most duplicates to the most specific:

1. **One instance per anchor.** A pattern is identified by its stock, type and anchor date (its first key point: A, B, LS, S, P0 or the start of a flat base window). Re-detecting the same pattern on later days updates the tracked instance instead of creating a new one.
2. **Mutually exclusive slope classes.** Triangles, rectangles and wedges are classified by slope (Sections 7.2, 8.1 and 10), so a single pair of lines can only be one of them.
3. **Most specific wins within a family.** If a high tight flag and a bull flag share the same pole, keep the high tight flag. If a rectangle and a flat base cover the same days after an uptrend, keep the flat base as the primary label and mark the rectangle as secondary, so it is not counted twice.
4. **Different families are kept.** A cup with handle that is also a VCP, or a flat base that is also an ascending triangle, is recorded under each label. When you analyse results, count each breakout once per label and note the overlap, so you can see whether the combination performs differently from either pattern alone.

## 12. Parameters

This table collects the tunable numbers, grouped in the same order as the sections. "Source" says whether the default comes from a published description or is an assumption in this spec.

| Parameter | Rule | Default | Test range | Source |
| --- | --- | --- | --- | --- |
| k_minor, k_major | 2.1 | 3, 8 bars | 2–5, 5–12 | Assumption |
| min_swing_pct, atr_mult | 2.1 | 3%, 1.5 | 2–5%, 1–2.5 | Assumption |
| tol | 2.2 | max(3%, 0.75 × ATR%) | 2–5% | Assumption |
| flat_slope | TL-05 | 0.05% per day | 0.03–0.10% | Assumption |
| prior_move, prior_window | PT-01, PT-02 | 20%, 120 days | 15–40%, 60–250 | Assumption |
| bo_buffer | BO-01 | 0.5% | 0–1% | Assumption |
| bo_vol | BO-02 | 1.4 | 1.0–2.0 | Assumption |
| max_wait | BO-04 | 20 days | 10–40 | Assumption |
| fail_days | BO-05 | 10 days | 5–20 | Assumption |
| cup depth | CH-02 | 12–33% | Up to 50% | O'Neil |
| cup duration | CH-04 | 35–325 days | Fixed | O'Neil |
| handle depth | CH-08 | 3–12% | Up to 15% | O'Neil |
| handle duration | CH-09 | 5–25 days | Fixed | O'Neil |
| min_peak | DB-03, DT-03 | 10% | 5–20% | Assumption |
| bottom separation | DB-04, DT-04 | 20–150 days | 10–250 | Assumption |
| min_head | HS-02 | 3% | 2–8% | Assumption |
| max_neck_slope | HS-05 | 0.3% per day | 0.1–0.5% | Assumption |
| triangle touches | TR-02 | 5 | 4–6 | Bulkowski |
| apex window | TR-05 | 50–80% | 40–90% | Edwards and Magee (approximate) |
| flat base depth | FB-02 | 15% | 10–15% | O'Neil |
| pole_gain, pole_days | FP-01, FP-02 | 15%, 15 days | 10–30%, 5–25 | Assumption |
| flag retracement | FL-02 | 50% | 33–62% | Assumption |
| HTF rise, HTF flag depth | HTF-01, HTF-03 | 100%, 25% | Fixed | O'Neil |

As with the VCP spec, change one parameter at a time and keep a change only if it holds out of sample.

## 13. Validation and pitfalls

Pattern detection needs one extra check that ordinary strategy backtests do not: confirming that the detector actually finds the shapes a human would recognise. Without that check, good or bad results may come from a detector that is finding something else.

### Validation

Run these checks in order. The first two test the detector; the last three test whether the patterns are useful.

1. **Visual audit (precision).** For each pattern type, draw 50 to 100 random detections on charts with the key points and lines marked, and label each one as correct or not. If fewer than about 80% look right **[assumption]**, tighten the rules before testing returns.
2. **Known-examples check (recall).** Hand-label a set of clear textbook examples, then check what share the detector finds. Low recall usually means the swing scale or tolerance is wrong.
3. **Baseline comparison.** Compare post-breakout outcomes with a simple baseline: breakouts to a new 50-day high in the same stocks and periods, without any pattern. A pattern adds value only if it beats this baseline, not just if its returns are positive.
4. **Out-of-sample test.** Tune on one period (for example 2010–2019) and test once on a later period (for example 2020–2026).
5. **Regime breakdown.** Report results separately for rising and falling markets, using the benchmark's 200-day average. Bullish patterns often work only in rising markets.

### Pitfalls

These are ordered from the most common cause of misleading results to the least:

1. **Hindsight in the shape.** It is easy to fit lines or choose points using bars that came after day t, for example fitting a triangle's lines through touches that had not happened yet. Every point and line must use only swings confirmed by day t.
2. **The breakout bar inside the pattern.** If the breakout day is included when computing the trigger, the trigger moves up with the breakout and the signal is never valid. Freeze T from day t − 1, as in the VCP spec.
3. **Loose tolerances.** With wide tolerances almost any chart becomes a pattern, which weakens the results. With very tight ones you get too few examples to learn from. Check the detection count per pattern per year alongside the returns.
4. **Testing too many variants.** Eleven pattern types, each with several parameters, create hundreds of combinations. Some will look good by chance. Decide the main tests before running them, and treat surprising winners with suspicion until they hold out of sample.
5. **Data problems.** The same issues as the VCP spec apply: survivorship bias, unadjusted bonus issues and splits, and fills that are impossible on circuit-locked days.

This specification is for research and education. Pattern statistics describe the past and do not guarantee future results.
