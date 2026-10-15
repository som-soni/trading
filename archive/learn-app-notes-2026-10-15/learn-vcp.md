# App notes moved out of learn-vcp

## Intro

Learning material: Mark Minervini's volatility contraction pattern — what it
is, why it works when it does, how to read one on a chart step by step, where
to buy and where the stop goes, the usual mistakes, and how this app detects
it.

**Where this shows up in the app.** The VCP is the entry pattern of the
`minervini` strategy (Strategies → Minervini). It is detected by the code in
`scripts/swing_screener/core/vcp_spec.py`. Every threshold below is a named
setting there and is shown on the Strategies page. The exact rules are in
[minervini-backtest-spec.md](minervini-backtest-spec.md) §5–6.

## §3 Rules of thumb — "In this app (defaults)" column

| Rule | Typical value | In this app (defaults) |
|---|---|---|
| Stage 2 uptrend | Trend Template passes | Conditions M1–M8, plus RS rating ≥ 70 in the backtest |
| Prior advance into the base | 30%+ | ≥ 30% above the prior 126-session low |
| Base length | 3–65 weeks | 15–325 sessions |
| Number of contractions | 2–6 (usually 2–4) | 2–6 |
| First contraction | ≤ ~35% (up to ~50% in a bear market) | ≤ 35% |
| Each contraction vs the previous | Roughly half | ≤ 0.8 × the previous |
| Final contraction | ≤ ~10%, ideally under 5–6% | Tight area and last contraction ≤ 10% |
| Pivot location | Near the top of the base | Pivot ≥ 0.9 × base high |
| Volume in the tight area | Well below average | ≤ 0.7 × the 50-day average |

## §4 step 3

(In this app, a reversal must be at least ~1.5 ATRs to count.)

## §5 Where to buy — setup codes

This app tests two ways of doing it:

| Setup | Entry | Trade-off |
|---|---|---|
| **MV-01 — confirmed breakout** | The day closes above the pivot on 1.4× volume, in the upper half of its range; buy at the next morning's open | Fewer false starts; worse price; very few signals |
| **MV-02 — buy-stop** | An order placed just above the pivot, which buys automatically once the price reaches it; it fills only on a session that closes at or above it | Better price; more failed breakouts |

- **Cheat ("3C"), MV-04** — a shelf in the middle third of the base ...
- **Low cheat, MV-03** — the same, in the lower third. It is riskier, and off by default here.

## §6 Stops

- **Initial stop:** just below the tight low (0.5% under it here).

The `minervini` strategy's exit rules (EX-01 to EX-07) implement exactly these;
see its Strategies page.

## §8 How this app detects a VCP

The app's VCP check (`core/vcp_spec.py`) tests the rules in order. It records
the first one that fails (in the `vcp_fail` column), so you can see *why* a
stock is not a VCP:

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

Two details are worth knowing, because they are where a computer and a human
reading the same chart differ: (zig-zag with shrinking threshold, never below ~1.5 ATRs; swing high known 5 sessions
later; breakout judged against the pivot as it stood the day before). — kept in the guide in general words.

## §9 Evidence — the project's own backtests (removed; work in progress)

The VCP is one of the best-known setups in trading, and this project tested it
hard. Here is the honest summary. It was measured on the spec's original
rules, before the strategy had version numbers. Later versions changed some
rules; their results are on its Strategies page under Backtests.

- **Strictly defined, complete VCPs are rare** on daily data. Confirmed
  breakouts (MV-01) gave only 9 trades in India and 26 in the US over 16 years.
- **The buy-stop version produced no edge** from 2010. It was about
  break-even per trade in India and slightly negative in the US, and far
  behind both indexes. Most trades ended as failed breakouts — small losses
  that added up.
- **Changing the thresholds did not rescue it.** No setting at either end of
  any parameter's range held up both before and after 2020
  ([India](minervini-spec-sensitivity-india.md), [US](minervini-spec-sensitivity-us.md)).
- **Adding Minervini's earnings and sales tests did not help** over 2022–2026
  either (see the research log, [momentum-trend-research.md](momentum-trend-research.md)).
- **Context helped more than shape.** In the earlier, looser Minervini
  version (since retired), skipping stocks in weak industry groups improved
  results in both markets.

## Further reading

- [minervini-backtest-spec.md](minervini-backtest-spec.md) — every rule above
  as testable conditions.
