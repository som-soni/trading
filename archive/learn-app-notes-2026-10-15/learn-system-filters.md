# App notes moved out of learn-system-filters

## Intro — Where this shows up in the app

**Where this shows up in the app.** The stages below are real code, not a
metaphor: the universe floor and the screens live in
`scripts/swing_screener/screens/`, a strategy's gates and flags in
`scripts/swing_screener/strategies/`, and the portfolio limits in
`scripts/swing_screener/config/`. The **Screening** page shows the funnel for
a run, stage by stage, with the count surviving each one.

## §2 Tier 1 — the app's floor

In this app it is price, liquidity and history:

| | US | India |
|---|---|---|
| minimum price | $10 | no floor |
| minimum liquidity (20-day average of price × volume) | $10,000,000 | ₹50,00,00,000 |
| history | enough bars for the longest average the rules need |

## §3 Tier 2 — app backtest evidence (must not be cited in Learn)

This is the stage most often skipped, and in this app's own testing it is the
only change that ever improved both return and drawdown at the same time:
applying a market filter to one strategy moved its US expectancy from +0.04R
to +0.06R and its maximum drawdown from -43.5% to -28.6%, by blocking 163 of
1,325 signals.

That is worth sitting with. The rule that helped was not about which stock to
buy.

## §4 Tier 3 — the app's four screens

Qualification: does this stock belong in the pool a strategy draws from. In
this app this stage *is* the screen, and there are four:

| screen | asks | criteria |
|---|---|---|
| **Stage 2 — Trend Template** | is this a confirmed long-term uptrend, stronger than most of the market | 8 |
| **Established uptrend** | is the weekly and daily structure in order, near highs, not fading | 8 |
| **Near highs, rising 200-day** | is price above a rising long-term average and close to its high | 3 |
| **Above the 200-day** | the long-term filter alone | 1 |

They overlap on purpose, because different strategies need different
strictness — but each *question* is asked in exactly one place in the code,
and a screen that wants a different threshold gets its own named constant.
Otherwise tuning one screen silently moves another.

## §5 Tier 4 — gate codes on the Screening page

A useful discipline: a gate must be able to say which rule rejected the stock,
and that reason must be readable by someone who did not write it. In this app
every rejected row carries its first failing gate code, which is why the
**Screening** page can show you *why* the universe collapsed on a given day
rather than just that it did.

## §7 Tier 6 — app's portfolio limits and backtest example

In this app: 1% of equity risked per trade (0.5% when volatility is high), a
25% cap on any one position, at most 10 open at once, and modelled costs of
5 basis points per side in the US and 10 in India.

The position cap matters more than it sounds. In one backtest here, 942
signals produced 253 trades: 85 were refused because all ten slots were full
and 132 for want of cash. When that happens, the portfolio limits are picking
your trades, not your rules.

## §8 Evidence (app backtest based)

## 8. What the evidence says

- **The regime stage has paid; the setup stage mostly has not.** The single
  measured improvement in both return and drawdown came from a market filter.
- **A stage that rejects nothing is not free** — it costs you the ability to
  interpret the ones that do.
- **Watch for the cap taking over.** If a large share of signals are refused
  for want of slots or cash, the system is not expressing your rules, and the
  fix is fewer signals rather than more capital.
