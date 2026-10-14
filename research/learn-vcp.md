# VCP — the volatility contraction pattern

Learning material: Mark Minervini's volatility contraction pattern — what it
is, why it works when it does, how to read one on a chart step by step, where
to buy and where the stop goes, the usual mistakes, and how this app detects
it. Read [learn-bases.md](learn-bases.md) first: a VCP is a particular way of
looking at a base.

**Where this shows up in the app.** The VCP is the entry pattern of the
`minervini` strategy (Strategies → Minervini), detected by
`scripts/swing_screener/core/vcp_spec.py`; every threshold below is a named
parameter there and on the Strategies page. The formal rules are in
[minervini-backtest-spec.md](minervini-backtest-spec.md) §5–6.

---

## 1. The idea in one paragraph

A stock in a strong uptrend pauses. The first pullback is the biggest — say
25% — because that is when profit-taking and nervous holders are heaviest.
Buyers step in, price rallies, then sellers return, but **fewer of them**: the
second pullback is only 12%. Then 6%. Then 3%. Each contraction is smaller
because the supply of shares for sale is being used up while someone keeps
buying. At the end, price barely moves and volume is unusually low — sellers
are exhausted. Then a modest amount of buying lifts the stock through the top
of that last tight range, and with little supply left above, it can move fast.

```pattern
vcp
```

That is the whole pattern: **volatility contracts from left to right, volume
dries up, and price ends in a tight area near the high.** It is not a new
shape so much as the common core of every good base — a cup with handle is a
two-contraction VCP; a high tight flag is a one-contraction VCP.

## 2. Anatomy

| Part | Meaning |
|---|---|
| **Base high** | Where the pattern starts: the peak before the first pullback |
| **Contractions (T1, T2, T3…)** | Each high-to-low pullback inside the base, measured as % of its own high |
| **Depth sequence** | The contractions in order, e.g. 25% → 12% → 6% → 3% |
| **Tight area** | The last few days to two weeks: very small ranges, very low volume |
| **Pivot** | The high of the tight area — the buy point |
| **Tight low** | The low of the tight area — the stop goes just under it |

### The footprint

Minervini summarises a VCP in one line, e.g. **"20W 32/3 4T"**:

- **20W** — the base lasted 20 weeks
- **32/3** — the deepest contraction was 32%, the final one 3%
- **4T** — four contractions

Writing every base you study this way is good practice: it forces you to
measure instead of eyeball, and it makes bases comparable.

## 3. The rules of thumb

| Rule | Typical value | In this app (defaults) |
|---|---|---|
| Stage 2 uptrend | Trend Template passes | Gates M1–M8, plus RS rating ≥ 70 in the backtest |
| Prior advance into the base | 30%+ | ≥ 30% above the prior 126-session low |
| Base length | 3–65 weeks | 15–325 sessions |
| Number of contractions | 2–6 (usually 2–4) | 2–6 |
| First contraction | ≤ ~35% (up to ~50% in a bear market) | ≤ 35% |
| Each contraction vs the previous | Roughly half | ≤ 0.8 × the previous |
| Final contraction | ≤ ~10%, ideally under 5–6% | Tight area and last contraction ≤ 10% |
| Pivot location | Near the top of the base | Pivot ≥ 0.9 × base high |
| Volume in the tight area | Well below average | ≤ 0.7 × the 50-day average |

The two that matter most are **contracting depth** and **drying volume**. A
base can be any length and any of the named shapes; if its pullbacks are not
shrinking and its volume is not drying up, it is not a VCP.

## 4. Reading one on a chart, step by step

Use the weekly chart to see the base and the daily chart to measure it.

1. **Check the stock first.** Stage 2, strong RS (80+ is better), a real prior
   advance, a healthy industry group, a market that is not falling apart. A
   perfect VCP in a weak stock or a weak market is still a low-odds trade.
2. **Mark the base high** — the peak the stock has not closed decisively
   above since.
3. **Measure each pullback.** From each swing high to the lowest low before
   the next rally, as % of that high. Ignore wiggles of a percent or two —
   count only real reversals (in this app, a reversal must be at least
   ~1.5 ATRs to count).
4. **Check the sequence shrinks.** 25 → 12 → 6 is a VCP. 10 → 15 → 8 is not:
   a contraction that is *deeper* than the one before means supply came back.
5. **Check volume.** It should fade as the contractions shrink, and be at its
   lowest in the final tight area. Heavy-volume down days late in the base are
   a warning.
6. **Find the tight area.** Several sessions with small ranges and closes
   bunched together, near the top of the base. On the weekly chart this often
   looks like two or three weeks closing almost at the same price.
7. **Mark the pivot and the stop.** The pivot is the tight area's high; the
   stop sits just under its low. Check the distance: if the stop is more than
   about 8% below the pivot, the base is not tight enough to buy at the pivot.
8. **Wait.** Nothing happens until price crosses the pivot.

## 5. Where to buy

### The pivot buy (the default)

Buy as price moves through the pivot, **on volume** — ideally 40–50% or more
above the 50-day average — and **not more than about 5% above the pivot**.
Beyond that the stop is too far away and you are chasing.

This app tests two ways of doing it:

| Setup | Entry | Trade-off |
|---|---|---|
| **MV-01 — confirmed breakout** | The day closes above the pivot on 1.4× volume, in the upper half of its range; buy next morning's open | Fewer false starts; worse price; very few signals |
| **MV-02 — buy-stop** | An order just above the pivot; fills only on a session that closes at or above it | Better price; more failed breakouts |

### The cheat entries (inside the base)

Minervini also buys *before* the pivot when a smaller shelf forms inside the
base — a few quiet sessions with their own little high:

- **Cheat ("3C"), MV-04** — a shelf in the middle third of the base, bought as
  price clears the shelf high.
- **Low cheat, MV-03** — the same in the lower third. Riskier; off by default
  here.

The appeal is a much closer stop (the shelf low) and a lower price. The cost
is that the base is not finished — more of these fail.

## 6. Where the stop goes, and what happens next

- **Initial stop:** just below the tight low (0.5% under it here). Never more
  than 8% below your price; 10% is the absolute limit. If the structure needs
  a wider stop, don't take the trade — don't widen the stop.
- **Size from the stop:** risk about 1% of the account per trade. A tight VCP
  stop is what allows a meaningful position at small risk.
- **Failed breakout:** if price closes back under the pivot within the first
  few days, the breakout has failed — get out. Good breakouts usually do not
  look back.
- **Protect gains:** once the trade is up 2–3× the initial risk, move the stop
  to breakeven. Selling part into strength (e.g. a third at 3× risk) is common.
- **Exit on a climax or a trend break:** a run of unusually large up days late
  in a move, or a close under the 50-day on heavy volume.

The `minervini` strategy's exit rules (EX-01 to EX-07) implement exactly these;
see its Strategies page.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Counting every wiggle as a contraction | Makes any choppy chart look like a VCP |
| Contractions that are not shrinking | Expanding swings are distribution, not accumulation |
| A deep final contraction (10%+) | The stop is far away; the base is not finished |
| Buying a breakout on light volume | Little demand behind the move; many of these fail |
| Buying 5–10% above the pivot | The stop is now far below; the risk-reward is gone |
| Ignoring the market | In a correction most breakouts fail, however good the base |
| Late-stage bases (4th+) | The trend is mature and crowded |
| Trading the pattern in a non-leader | A VCP in a stock with weak RS has nothing to break out *with* |
| Holding through a failed breakout | The pattern was wrong; the loss only grows |

## 8. How this app detects a VCP

`core/vcp_spec.py` checks the rules in order and records the first one that
fails (the `vcp_fail` column), so you can see *why* a stock is not a VCP:

| Rule | Checks |
|---|---|
| VCP-01 | Prior advance ≥ 30% into the base high |
| VCP-02 | Base length 15–325 sessions |
| VCP-03 | Trend Template on the base-high bar; moving-average structure every day since |
| VCP-04 | 2–6 contractions |
| VCP-05 | First contraction ≤ 35% |
| VCP-06 | Each contraction ≤ 0.8 × the previous |
| VCP-08 | Final contraction and tight area ≤ 10% |
| VCP-09 | Pivot ≥ 0.9 × base high |
| VCP-10 | Tight-area volume ≤ 0.7 × average |

Two details worth knowing, because they are where a computer and a human
reading the same chart differ:

- **Contractions come from a zig-zag whose threshold shrinks.** One fixed
  threshold cannot see both a 25% first contraction and a 3% last one; here it
  starts wide and narrows to a fraction of the contraction just measured,
  never below ~1.5 ATRs (a smaller "reversal" is just one bar's noise).
- **No hindsight.** A swing high is only known 5 sessions later, and the
  breakout is judged against the pivot as it stood the day *before*, so the
  breakout bar cannot move its own pivot.

## 9. What the evidence says

The VCP is one of the best-known setups in trading, and this project tested it
hard. The honest summary (measured on the spec's original rules, before the
strategy was versioned; later versions changed some rules, and their results
are on its Strategies page under Backtests):

- **Strictly defined, complete VCPs are rare** on daily data. Confirmed
  breakouts (MV-01) gave only 9 trades in India and 26 in the US over 16 years.
- **The buy-stop version produced no edge** from 2010: about break-even per
  trade in India, slightly negative in the US, far behind both indexes. Most
  trades ended as failed breakouts — small losses that added up.
- **Changing the thresholds did not rescue it.** No setting at either end of
  any parameter's range held up both before and after 2020
  ([India](minervini-spec-sensitivity-india.md), [US](minervini-spec-sensitivity-us.md)).
- **Adding Minervini's earnings and sales tests did not help** over 2022–2026
  either (the research log, [momentum-trend-research.md](momentum-trend-research.md)).
- **Context helped more than shape:** in the earlier, looser Minervini
  version (since retired), skipping stocks in weak industry groups improved results
  in both markets.

What this does *not* show: that discretionary VCP trading cannot work.
Minervini's own results come with judgement the rules cannot capture —
reading the market, the stock's story, and when not to trade. What it does
show is that **the shape alone, mechanically, is not an edge**. Treat the VCP
as a way to time a low-risk entry in a stock you already have reasons to own,
with a tight stop that tells you quickly when you are wrong.

## 10. Checklist

- [ ] Stage 2, RS 70+ (80+ better), healthy group, market in an uptrend
- [ ] Prior advance of 30%+
- [ ] 2–6 contractions, each clearly smaller than the last
- [ ] First contraction ≤ ~35%; final ≤ ~10%, ideally under 5–6%
- [ ] Volume fading through the base, quietest in the tight area
- [ ] Tight area near the top of the base (pivot within ~10% of the high)
- [ ] Stop just under the tight low, no more than ~8% below the pivot
- [ ] Breakout on volume 40–50%+ above average; buy within ~5% of the pivot
- [ ] Early-stage base; no earnings due within a couple of weeks
- [ ] Write the footprint: weeks, max/final depth, number of contractions

## Further reading

- Mark Minervini, *Trade Like a Stock Market Wizard* and *Think & Trade Like a
  Champion* — the VCP, the footprint, pivots, cheat entries and risk control.
- [minervini-backtest-spec.md](minervini-backtest-spec.md) — every rule above
  as testable conditions.
- [learn-chart-patterns.md](learn-chart-patterns.md) — the named bases, with
  drawings.
