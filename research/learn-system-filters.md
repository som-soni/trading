# The filter stack — six questions between a universe and a trade

Learning material: how thousands of stocks become one trade. Every systematic
system narrows its universe in stages, and each stage answers a *different*
question. Mixing those questions together is the most common way a working
system becomes an untestable one.

For the strategies themselves, see [the strategies map](learn-strat-overview.md);
for turning one into rules, [writing your own strategy specification](learn-strat-spec.md).

**Where this shows up in the app.** The stages below are real code, not a
metaphor: the universe floor and the screens live in
`scripts/swing_screener/screens/`, a strategy's gates and flags in
`scripts/swing_screener/strategies/`, and the portfolio limits in
`scripts/swing_screener/config/`. The **Screening** page shows the funnel for
a run, stage by stage, with the count surviving each one.

---

## 1. Why stages, and why they must stay separate

A filter answers one question. Stack them in the wrong order, or let one
stage answer two questions, and three things break:

- **You cannot tell what rejected a stock.** "It didn't appear" is not a
  diagnosis.
- **You cannot tune one thing at a time.** Changing a liquidity floor silently
  changes the trend test, because fewer names reach it.
- **You cannot reuse anything.** A trend test buried inside one strategy
  cannot feed another.

The stages below go from the cheapest and most permanent to the most
specific and most frequently changed.

## 2. Tier 1 — can this instrument be traded at all?

The permanent floor. Nothing below it is worth computing anything for.

In this app it is price, liquidity and history:

| | US | India |
|---|---|---|
| minimum price | $10 | no floor |
| minimum liquidity (20-day average of price × volume) | $10,000,000 | ₹50,00,00,000 |
| history | enough bars for the longest average the rules need |

These are deliberately crude. Their job is to remove what you could not trade
at size even if you wanted to — not to express any view.

## 3. Tier 2 — should I be trading this market at all?

A regime filter asks about the *market*, not the stock, and it gates whole
families at once. The usual form: stand aside when the index is below a
long-term average, or when breadth has collapsed.

This is the stage most often skipped, and in this app's own testing it is the
only change that ever improved both return and drawdown at the same time:
applying a market filter to one strategy moved its US expectancy from +0.04R
to +0.06R and its maximum drawdown from -43.5% to -28.6%, by blocking 163 of
1,325 signals.

That is worth sitting with. The rule that helped was not about which stock to
buy.

## 4. Tier 3 — is this stock in the right condition?

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

## 5. Tier 4 — is there a setup right now?

The first stage that is specific to one strategy. These are the hard gates:
fail one and the answer is no, with a reason.

What belongs here is a *trade* rule rather than a qualification rule: the
pattern is complete, the stop is not absurdly wide, earnings are not inside
ten days, volatility is sane, price has not already run away from the trigger.

A useful discipline: a gate must be able to say which rule rejected the stock,
and that reason must be readable by someone who did not write it. In this app
every rejected row carries its first failing gate code, which is why the
**Screening** page can show you *why* the universe collapsed on a given day
rather than just that it did.

## 6. Tier 5 — is there a reason to be careful?

Not every warning deserves a veto. A pattern can be real, the trend intact,
and something still off — the breakout came on thin volume, the stock is
extended far above its average, momentum is overbought, a topping structure is
forming on the same chart.

Treating these as hard rejections throws away good trades; ignoring them
treats a weak signal as a strong one. The middle path is a flag that **caps
the confidence** rather than removing the row: the trade is still listed, but
it is downgraded from "take this" to "wait for confirmation".

This also keeps the information visible. A row that disappears teaches you
nothing; a row that says *"through the trigger on 0.6× volume"* teaches you
what to look for next time.

## 7. Tier 6 — can this trade actually be placed?

The last stage is arithmetic, and it is where most beginners' systems quietly
fail. A perfect signal in a stock you cannot size, or one that would put a
quarter of the account into a single name, is not a trade.

In this app: 1% of equity risked per trade (0.5% when volatility is high), a
25% cap on any one position, at most 10 open at once, and modelled costs of
5 basis points per side in the US and 10 in India.

The position cap matters more than it sounds. In one backtest here, 942
signals produced 253 trades: 85 were refused because all ten slots were full
and 132 for want of cash. When that happens, the portfolio limits are picking
your trades, not your rules.

## 8. What the evidence says

- **The regime stage has paid; the setup stage mostly has not.** The single
  measured improvement in both return and drawdown came from a market filter.
- **A stage that rejects nothing is not free** — it costs you the ability to
  interpret the ones that do.
- **Watch for the cap taking over.** If a large share of signals are refused
  for want of slots or cash, the system is not expressing your rules, and the
  fix is fewer signals rather than more capital.
- **Order matters for cost, not for results.** Cheap, permanent filters first;
  expensive, specific ones last.

## 9. Checklist

1. Can I name the single question each of my filters answers?
2. Does any filter answer two questions? Split it.
3. Is the same question asked in two places with different numbers? Pick one.
4. When a stock is rejected, can I see which rule did it?
5. Do I have a regime stage at all, or does my system always trade?
6. What share of my signals die at the portfolio limits?

## Further reading

- Robert Carver, *Systematic Trading* — staged filtering and why position
  sizing belongs at the end, not the beginning.
- Perry Kaufman, *Trading Systems and Methods* — regime filters, and how a
  system's results change when one is added.
