# The filter stack — six questions between a universe and a trade

**In short**

- A systematic trader narrows thousands of stocks to a few trades in stages. Each stage should answer one question.
- The six questions: can it be traded, should I trade this market now, is the stock in the right condition, is there a setup, is there a reason for caution, and can the trade actually be placed?
- Keep the stages separate. Then you can see what rejected a stock, tune one thing at a time and reuse each stage.
- On index data, a market (regime) filter acts mainly on risk: it lowers volatility and drawdowns more than it raises returns.
- Signals arrive in bunches. When your position limits refuse many of them, the limits are choosing your trades, not your rules.

Take a US trader with a list of 5,000 stocks. In a made-up but typical day, a liquidity floor leaves 1,500 and a trend screen leaves 300. A setup rule leaves 12, and the account has room for 3.

Each cut answered a different question. Mixing those questions together is the most common way a working system becomes one you cannot test.

For the strategies themselves, see [the strategies map](learn-strat-overview.md). For turning one into rules, see [writing your own strategy specification](learn-strat-spec.md).

---

## 1. Why stages, and why they must stay separate

A filter answers one question. Stack filters in the wrong order, or let one stage answer two questions, and three things break:

- **You cannot tell what rejected a stock.** "It didn't appear" is not a diagnosis.
- **You cannot tune one thing at a time.** Changing a liquidity floor silently changes the trend test, because fewer names reach it.
- **You cannot reuse anything.** A trend test buried inside one strategy cannot feed another.

The stages below go from the cheapest and most permanent to the most specific and most often changed.

## 2. Tier 1 — can this instrument be traded at all?

This is the permanent floor. Nothing below it is worth computing anything for. A typical floor uses price, liquidity and history:

| | US example | India example |
|---|---|---|
| minimum price | $10 | often none |
| minimum liquidity (20-day average of price × volume) | $10 million a day | ₹50 crore a day |
| history | enough bars for the longest average the rules need | same |

These are deliberately crude. Their job is to remove what you could not trade at size even if you wanted to. They express no view.

One trap: price data is usually adjusted for later splits, so a minimum *price* applied to old data can wrongly exclude a stock. Traded value (price × volume) is not changed by splits. The [backtesting guide](learn-test-backtesting.md) shows an example.

## 3. Tier 2 — should I be trading this market at all?

In February 2020 the Nifty 50 closed just below its 200-day average. Over the next four weeks it fell about 35%. A trader whose system stopped buying when the index lost its 200-day average was out for the whole fall. That rule is a **regime filter**.

A regime filter asks about the *market*, not the stock, and it gates whole families of trades at once. The usual form: stand aside when the index is below a long-term average, or when breadth has collapsed.

What it does is mainly about risk. On index data, days with the index below its 200-day average were about twice as volatile as days above it. Most of the worst days happened there — but so did most of the best days, because big rebounds come in falling markets.

| Index, period | Volatility above the 200-day | Volatility below |
|---|---|---|
| S&P 500, 1929–2026 | 14.7% | 25.7% |
| Nifty 50, 2008–2026 | 15.3% | 27.3% |

Published work agrees. Faber (2007) and Zakamulin (2017) found that index trend filters mostly reduce volatility and drawdowns, with returns similar to holding. The full treatment, with the costs of whipsaw, is in [regime filters](learn-strat-regime-filters.md).

This is the stage most often skipped. It is worth sitting with: a rule that is not about which stock to buy can change a system's risk more than any stock rule.

## 4. Tier 3 — is this stock in the right condition?

This stage is qualification: does this stock belong in the pool a strategy draws from? It is a **screen**. Common screens for long trades, from strict to loose:

| Screen | Asks | Typical number of conditions |
|---|---|---|
| **Stage 2 — Trend Template** | is this a confirmed long-term uptrend, stronger than most of the market? | 8 |
| **Established uptrend** | is the weekly and daily structure in order, near highs, not fading? | about 8 |
| **Near highs, rising 200-day** | is price above a rising long-term average and close to its high? | 3 |
| **Above the 200-day** | the long-term filter alone | 1 |

Screens can overlap on purpose, because different strategies need different strictness. But ask each *question* in one place. If two screens test "how far below the 52-week high", write that test once and give each screen its own threshold. Otherwise tuning one screen silently moves another.

## 5. Tier 4 — is there a setup right now?

This is the first stage that is specific to one strategy. These are the hard gates: fail one and the answer is no, with a reason.

What belongs here is a *trade* rule rather than a qualification rule. Examples: the pattern is complete, the stop is not absurdly wide, and earnings are not due within ten days. Volatility is sane, and price has not already run away from the trigger.

A useful discipline: a gate must be able to say which rule rejected the stock. That reason must be readable by someone who did not write it. If each rejected stock carries its first failing rule, you can see *why* the list collapsed on a given day, not just that it did.

## 6. Tier 5 — is there a reason to be careful?

Not every warning deserves a veto. A pattern can be real and the trend intact, with something still off. The breakout came on thin volume. The stock is far above its average. Momentum is overbought, or a topping pattern is forming on the same chart.

Treating these as hard rejections throws away good trades. Ignoring them treats a weak signal as a strong one. The middle path is a flag that **caps the confidence** rather than removing the stock. The trade is still listed, but it is downgraded from "take this" to "wait for confirmation".

This also keeps the information visible. A stock that disappears teaches you nothing. A stock marked *"through the trigger on 0.6× volume"* teaches you what to look for next time.

## 7. Tier 6 — can this trade actually be placed?

The last stage is arithmetic, and it is where most beginners' systems quietly fail. A perfect signal in a stock you cannot size is not a trade. Neither is one that would put a quarter of the account into a single name.

A typical set of limits:

| Limit | Typical value |
|---|---|
| Risk per trade | 1% of equity (0.5% when volatility is high) |
| Largest single position | 25% of equity |
| Open positions | at most 10 |
| Costs to allow for | about 0.05% per side in the US, 0.1% in India, before taxes |

The position limit matters more than it sounds, because signals arrive in bunches. Take the 1,000 most-traded US stocks from 2015 to October 2026. On a typical day 46 of them made a new 52-week high. On the busiest tenth of days it was 112 or more, and on the quietest tenth 8 or fewer. India's figures were 31, 86 and 5.

A ten-slot account fills on the first busy day and then refuses most later signals. When that happens, the portfolio limits are picking your trades, not your rules. How a system breaks ties — by relative strength, by volume, or by the order of the ticker list — then decides much of the result.

## 8. What the evidence says

- **The regime stage acts mainly on risk.** On index data, the market below its 200-day average was about twice as volatile. Published tests find trend filters cut drawdowns more than they raise returns. Whether one helps a particular strategy has to be tested on that strategy's own signals.
- **A stage that rejects nothing is not free.** It costs you the ability to interpret the ones that do.
- **Watch for the limits taking over.** Signals cluster in strong markets. If many are refused for want of slots or cash, the system is not expressing your rules. The fix is fewer, better-ranked signals rather than more capital.
- **Order matters for cost, not for results.** Cheap, permanent filters first; expensive, specific ones last.
- **Limits:** the new-highs counts cover only the 1,000 most-traded stocks since 2015, from today's lists; the volatility figures are on indexes, not on any strategy.

## 9. Checklist

1. Can I name the single question each of my filters answers?
2. Does any filter answer two questions? Split it.
3. Is the same question asked in two places with different numbers? Pick one.
4. When a stock is rejected, can I see which rule did it?
5. Do I have a regime stage at all, or does my system always trade?
6. What share of my signals die at the portfolio limits? How do I break ties?

## Further reading

- Robert Carver, *Systematic Trading* — staged filtering and why position
  sizing belongs at the end, not the beginning.
- Perry Kaufman, *Trading Systems and Methods* — regime filters, and how a
  system's results change when one is added.
- Mebane T. Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management* (2007).
