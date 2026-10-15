# Writing your own strategy specification — from an idea to rules you can test

**In short**

- A strategy specification is a written set of rules, precise enough that two people applying it to the same data would make the same trades.
- It has seven parts: universe, setup, entry, stop, exits, position size and filters. Each rule is a condition that is either true or false on a given day.
- Every number in it is a named parameter with a range. You write down the value you will test first, and why.
- Decide what "works" means before you test: the benchmark, the minimum number of trades, the measures and the hurdle. Otherwise any result can be read as a success.
- This guide builds one example spec step by step and ends with a template to fill in.

## 1. The idea

Here is a trading idea as most people first state it: *"Buy strong stocks when they break out, and get out when the trend ends."* It sounds clear. It is not testable. Which stocks are "strong"? What is a breakout? When has a trend "ended"?

Here is the same idea as a specification:

> **Universe:** Nifty 500 stocks with a median daily traded value of at least ₹10 crore over the last 50 sessions.
> **Setup:** the close is at or above the highest close of the prior 50 sessions; the close is above the 200-day average; the 200-day average is higher than it was 20 sessions ago; volume is at least 1.5 times its 50-day average.
> **Entry:** buy at the next session's open.
> **Stop:** entry minus 2 times the 14-day ATR on the signal day.
> **Exit:** sell at the next open after the first close below the 50-day average. If the trade is not up at least 1R after 20 sessions, sell.
> **Size:** risk 1% of the account per trade; at most 8 positions.

On 2 May 2023 that rule fired on Trent, the retailer.

```series
title: Trent — one signal of the example specification, May 2023
from: 2023-01-01
to: 2023-12-29
tf: D
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma50 | 50-day average
line: india:TRENT.NS@sma200 | 200-day average
mark: 2023-05-02 | signal: 50-day closing high
mark: 2023-10-20 | first close below the 50-day
caption: The signal fired on 2 May. The exit rule fired on 20 October. Both were decided by the rules, not by judgement on the day.
```

The second version can be wrong, and that is its value. You can run it over ten years of data and count what it did. You can change one number and see what changes. You can follow it in real time without asking yourself, every morning, what "strong" means today.

A specification also protects you from yourself. A trader with no written rules changes them after each loss. [The trading plan guide](learn-process-plan.md) covers the routine around the rules; this guide covers the rules themselves.

## 2. When a specification helps and when it doesn't

**It helps whenever you want to know if an idea works.** Without written rules, a backtest tests whatever you decided while looking at the chart. That includes hindsight.

**It helps when you trade under pressure.** A rule written on a calm weekend is easier to follow on a falling morning than a judgement made in the moment.

**It does not make a bad idea good.** A precise rule can be precisely useless. The specification only makes the idea testable.

**It does not replace judgement entirely.** Some traders use a spec for the mechanical parts (universe, stop, size) and keep judgement for the setup. That is fine if you write down which parts are judgement, and track them separately.

**India and US.** Write the market-specific rules into the spec, not into your head. For India: circuit limits, T+1 settlement, no overnight shorts in cash (swing shorts need futures or options; see the Futures & options section), and the higher cost of delivery trades. For the US: the pattern-day-trader rule for small margin accounts, borrow for shorts, and pre-market gaps.

## 3. The rules — how to write each part

For each part, the guide gives the question it answers, how to make it testable, and the example.

### Universe and filters

*The question:* which instruments can this strategy ever trade?

*Make it testable:* name the list (an index, an exchange, a sector), the minimum liquidity, the minimum price, and what is excluded. Say when the list is fixed: membership must be as of each test date, not today.

*Example:* Nifty 500 members on each date. Median daily traded value of at least ₹10 crore over 50 sessions. Price at least ₹50. No stocks in a trade-for-trade or surveillance segment.

**Filters** are conditions on the market or the stock that switch the strategy on or off. Keep them separate from the setup, so you can test with and without each one. [The filter stack guide](learn-system-filters.md) sorts them into tiers.

*Example market filter:* the Nifty 500 closes above its 200-day average. (We will test with and without it.)

### Setup

*The question:* what must be true about the stock before you consider a trade?

*Make it testable:* write each condition as a comparison of two numbers on a stated day. "The trend is up" becomes "the close is above the 200-day average, and the 200-day average is higher than 20 sessions ago". Avoid words like *strong*, *tight*, *near* and *clean* unless you define them with a number.

*Example:* on the signal day (day *t*):
1. close[t] ≥ the highest close of days t−50 to t−1;
2. close[t] > the 200-day average;
3. the 200-day average on day t > its value on day t−20;
4. volume[t] ≥ 1.5 × the average volume of days t−50 to t−1.

### Entry

*The question:* exactly when, and at what price, do you buy?

*Make it testable:* name the order type and the moment. With daily data, the honest choices are "the next open" or "a buy-stop above day t's high, valid for N sessions". A close entry on the signal day is only honest if you can act in the last minutes before the close.

*Example:* buy at the open of day t+1. If the open is more than 3% above the signal close, skip the trade.

### Initial stop

*The question:* where are you wrong, and what do you do about it?

*Make it testable:* a price set at entry, from a stated rule. Common forms: a multiple of ATR below the entry; below the low of the setup; a fixed percentage. Say how a gap through the stop is filled: at the open, not at the stop. [The stops and exits guide](learn-risk-stops-exits.md) compares the forms.

*Example:* stop = entry − 2 × ATR(14) on day t, where ATR is the 14-day simple average of the true range. Sell at the stop, or at the open if the stock opens below it.

### Exits

*The question:* how does a winning trade end, and how does a dead one end?

*Make it testable:* every trade must end by a rule. Use one or more of four kinds. A target is a price or an R-multiple. A trailing stop follows a moving average, a channel low or an ATR trail. A time stop ends trades that go nowhere, and an invalidation is an event that kills the reason for the trade.

*Example:* sell at the next open after the first close below the 50-day average. Time stop: if the trade is not up at least 1R after 20 sessions, sell at the next open.

### Position size

*The question:* how much do you buy?

*Make it testable:* a formula. The usual one is fixed-fractional: shares = (account × risk per trade) ÷ (entry − stop). Add caps: the most in one position, in one sector, and the total open risk. [The position sizing guide](learn-risk-sizing.md) and [the portfolio risk guide](learn-risk-portfolio.md) give the arithmetic.

*Example:* risk 1% of the account per trade. No position larger than 20% of the account. At most 8 open positions. If more signals fire than there are free slots, take those with the highest 63-session return first.

### Managing the trade

*The question:* what can change while the trade is open?

*Make it testable:* list every allowed action and its trigger. Can the stop move up? When? Do you sell before results? Do you add to winners? Anything not written here is not allowed.

*Example:* the stop never moves down. No adding. Hold through results. No other changes.

### What "works" means — decide before you test

This is the part most people skip. Write it down before you run anything:

| Question | Example answer |
|---|---|
| Benchmark | Buying the Nifty 500 and holding it; and the same stocks held for 20 sessions at random |
| Period | 2012–2021 to build; 2022 onward held back, tested once |
| Minimum sample | 200 trades in the building period |
| Main measure | Expectancy in R after costs |
| Hurdle | Expectancy above 0.2R after costs, positive in at least two-thirds of years |
| Risk measures | Maximum drawdown; longest losing run; worst year |
| What would make me drop it | Expectancy below 0.1R, or most of the profit from fewer than 10 trades |

### The fill-in template

```
STRATEGY NAME:                         VERSION / DATE:
IDEA (one sentence; who is on the other side?):

UNIVERSE: list ......  as of each date? Y/N   min traded value ......  min price ......
          exclusions ......
FILTERS (each switchable): market ......   stock ......   event (results, ex-dates) ......
SETUP (each a true/false condition on day t):
  1. ......
  2. ......
ENTRY: order type ......  timing ......  skip if ......
INITIAL STOP: rule ......  gap fill ......
EXITS: target ......  trailing ......  time ......  invalidation ......
SIZE: risk per trade ......  max position ......  max positions ......  ranking if too many signals ......
MANAGEMENT: allowed actions and triggers ......
PARAMETERS: name | first value | range to test | why this value
COSTS: brokerage ......  taxes ......  slippage per side ......
WHAT "WORKS" MEANS: benchmark ......  period (build / hold-out) ......  min trades ......
                    main measure and hurdle ......  drop it if ......
```

## 4. The parameters

Name every number. A number with no name is easy to change without noticing. Give each one a first value, a range and a reason. Here is the table for the example:

| Parameter | First value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Liquidity | ₹10 crore median daily value (₹5–25 crore) | What can be traded | Higher cuts small caps and signals |
| Minimum price | ₹50 | Avoids very low-priced stocks | Rarely matters |
| Breakout lookback | 50 sessions (20–100) | How big a high is needed | Shorter means more, weaker signals |
| Trend average | 200-day (150–250) | Long-term trend filter | Usually robust |
| Trend slope lookback | 20 sessions (10–40) | "Rising" average | Small effect |
| Volume multiple | 1.5× (1–2×) | Demand on the signal day | Higher cuts signals sharply |
| Gap skip | 3% above the signal close (2–5%) | Avoids chasing | Test with and without |
| Stop multiple | 2 × ATR(14) (1.5–3) | Risk per share | Key: changes position size and win rate together |
| Trailing average | 50-day (20–100) | How long winners are held | Key: shorter cuts winners early |
| Time stop | 20 sessions, unless up 1R (10–40) | Frees money from dead trades | Moderate |
| Risk per trade | 1% (0.5–2%) | Size, and so drawdown | Does not change the edge, only its scale |
| Maximum positions | 8 (5–15) | Diversification | Interacts with risk per trade |
| Ranking | 63-session return | Which signals to take | Matters only when slots are full |
| Market filter | Nifty 500 above its 200-day | On/off switch | Test both |

Mark the two or three parameters you expect to matter most ("Key" above). Those are the ones to vary first, and the ones where a narrow peak in results should worry you.

## 5. Variations — how others write specifications

**The Turtle rules.** The trading rules Richard Dennis and William Eckhardt gave their "Turtle" trainees in the 1980s, described by Curtis Faith in *Way of the Turtle* (2007), are a model of a complete spec. They cover markets, position size, entries, stops, exits and tactics, and every one is mechanical.

**Van Tharp's system parts.** In *Trade Your Way to Financial Freedom*, Van K. Tharp breaks a system into setup, entry trigger, stop, profit-taking exits and position sizing. He argues that sizing and exits matter more than entry.

**Pardo's evaluation process.** Robert Pardo, in *The Evaluation and Optimization of Trading Strategies* (2008), adds a formal process: specify, test, optimise within limits, then walk-forward test. His point is that the spec must come before the optimisation.

**Davey's build process.** Kevin Davey, in *Building Winning Algorithmic Trading Systems* (2014), adds a written goal and a stage of "incubation": trading the finished rules on paper or small size before real money.

**Discretionary checklists.** Many discretionary traders use a checklist instead of code. It can still be a spec, if each line is true or false and the trader records which lines they overrode.

**Screens and strategies.** Some traders split the spec in two: a screen that only qualifies stocks, and a strategy that adds the trade rules. [The screens and strategies guide](learn-system-screens-strategies.md) explains why that split helps.

## 6. Worked examples — the example spec on three Indian stocks

All trades use the example rules from §1 and §3. Prices are adjusted closes and opens from daily data. ATR is a simple 14-day average of the true range.

### Trent, May 2023 — a long winner

| Step | Date | Rule | Value |
|---|---|---|---|
| Signal | 2 May 2023 | 50-day closing high, above a rising 200-day, volume 2.7× | Close ₹1,406.50; 200-day ₹1,354 |
| Entry | 3 May 2023 | Next open | ₹1,409.45 |
| Stop | — | Entry − 2 × ATR (₹31.95) | ₹1,345.54; risk ₹63.91 |
| Time stop check | 20 sessions in | Up more than 1R? | Yes, keep |
| Exit signal | 20 Oct 2023 | First close below the 50-day | Close ₹2,036.15 |
| Exit | 23 Oct 2023 | Next open | ₹2,035.00 |
| Result | — | | +44%, about +9.8R |

### Hindustan Aeronautics, March 2023 — a stop hit by a gap (failure)

| Step | Date | Rule | Value |
|---|---|---|---|
| Signal | 1 Mar 2023 | All four setup conditions | Close ₹1,342.12 |
| Entry | 2 Mar 2023 | Next open | ₹1,355.50 |
| Stop | — | Entry − 2 × ATR (₹41.15) | ₹1,273.21 |
| Exit | 23 Mar 2023 | Opened below the stop; filled at the open | ₹1,246.50 |
| Result | — | | −1.32R |

The loss was larger than 1R because the stock opened below the stop. A test that fills every stop exactly at the stop price would have shown −1R. That is why the spec says how a gap is filled.

### Bharat Electronics, February 2024 — a small loss on the trend exit (failure)

```series
title: Bharat Electronics — a signal that failed, February–March 2024
from: 2023-12-01
to: 2024-04-30
tf: D
line: india:BEL.NS | Bharat Electronics | log
line: india:BEL.NS@sma50 | 50-day average
line: india:BEL.NS@vol | Volume | pane2 bars
mark: 2024-02-22 | signal
mark: 2024-03-13 | close below the 50-day
caption: The exit came before the stop. The stock then recovered and made new highs, which the rules did not catch again until a new signal fired.
```

| Step | Date | Rule | Value |
|---|---|---|---|
| Signal | 22 Feb 2024 | All four setup conditions | Close ₹194.75 |
| Entry | 23 Feb 2024 | Next open | ₹196.30 |
| Stop | — | Entry − 2 × ATR (₹5.93) | ₹184.44 |
| Exit signal | 13 Mar 2024 | First close below the 50-day | Close ₹190.30 |
| Exit | 14 Mar 2024 | Next open | ₹189.00 |
| Result | — | | −0.62R |

Three trades prove nothing about the rules. They show that the rules give one answer on each day, which is the point.

## 7. Common mistakes

- **Vague words.** "Strong", "tight", "near support". Replace each with a number.
- **Rules written after looking at the results.** Then the test measures your hindsight. Write the spec, then test.
- **Today's lists.** Using today's index members makes the past look better, because the losers have been removed.
- **Entering at a price you could not get.** The signal close, when the signal is only known after the close.
- **Stops filled at the stop price after a gap.** Use the open.
- **No exit for dead trades.** Money sits in a stock going nowhere.
- **No definition of "works".** Then every result looks promising.
- **Too many parameters.** Each one you tune is another chance to fit noise. Fewer than ten is a good rule.
- **Changing the spec without a new version.** Keep a version number and a dated note of each change, so you know which results belong to which rules.

## 8. What the evidence says

**Published research on testing many ideas.**
- **Data snooping.** Halbert White (2000) showed how testing many rules on the same data makes the best one look good by chance, and gave a test for it. Sullivan, Timmermann and White (1999) applied it to technical trading rules: much of the apparent profit of the best rules disappeared once the number of rules tried was accounted for.
- **Backtest over-fitting.** Bailey, Borwein, López de Prado and Zhu (2014) showed that after enough variations, a backtest with a high Sharpe ratio is almost certain to appear even when no rule has any edge.
- **Higher hurdles.** Harvey, Liu and Zhu (2016) argued that because so many factors have been tested, a new one should clear a t-statistic of about 3, not 2.

The practical lesson is the same in all of them: count how many variants you tried, and demand more of the winner the more you tried.

**Our event study — the base rate.** Before judging a signal, know what a random entry does. We measured the return of every liquid stock over the next 20 sessions, sampled every fifth session from 2012 to mid-2025.

Liquid means a median daily traded value of at least ₹10 crore or $10 million. The price had to be at least ₹50 or $5. We then did the same for days on which the first three setup conditions in §3 held. The volume condition was left out to keep the sample large.

| 20-session forward return | India, any day | India, setup days | US, any day | US, setup days |
|---|---|---|---|---|
| Observations | 179,276 | 11,795 | 906,078 | 62,594 |
| Share positive | 53.3% | 54.5% | 54.0% | 53.3% |
| Median | +0.74% | +0.98% | +0.77% | +0.50% |
| Share that lost 10% or more | 11.8% | 12.1% | 11.8% | 8.7% |

*What it shows.* On a fixed 20-session hold, the setup barely differed from a random day. Any edge the full specification has must come from the exits and the sizing: cutting losers at the stop and holding winners like Trent for months. This is why "define what works" must name a benchmark. Without one, a 54% win rate sounds good. Against a 53% base rate, it is nothing.

*Caveats.* Today's stock lists leave out delisted companies. Observations overlap and cluster in time, so they are far from independent. This is a description of returns after a condition, not a test of the strategy, which is yours to run.

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume, adjusted for splits and bonuses. Index membership on each date. Results dates and corporate actions. Delisted stocks, if you can get them.

**Look-ahead traps.**
- Every indicator on day t uses data up to day t only.
- A signal known at the close is traded at the next open.
- Index membership, sector labels and fundamentals must be as they were known on each date. Quarterly results are known on their release date, not the quarter end.

**Survivorship.** Today's index members are the survivors. A test on them alone overstates returns, often a lot for small caps. [The backtesting guide](learn-test-backtesting.md) shows how much.

**Costs and slippage (approximate).**
- India, delivery trades: brokerage from zero to ₹20 per order; STT about 0.1% on each side; stamp duty about 0.015% on the buy side; exchange fees, SEBI fees and GST on top. Roughly 0.25–0.3% for a round trip before slippage.
- India, intraday: STT about 0.025% on the sell side; stamp duty about 0.003% on the buy side.
- US: commissions near zero; the cost is the spread and slippage.
- Slippage: 0.1% per side for large stocks; more for small ones and at the open.

**Avoiding over-fitting.**
1. Fix the spec and the definition of "works" before the first test.
2. Split the data: build on the earlier years, hold back the last few and test them once.
3. Vary each key parameter across its range. Look for a broad plateau of decent results, not a single best value.
4. Count and record every variant you test.
5. Check results by year, by market regime and with costs doubled.
6. Paper-trade or trade small for a few months before trading full size.

**What a good test reports.**

- Number of trades, win rate, and the average win and loss in R.
- Expectancy in R after costs, and the profit factor.
- Maximum drawdown and the longest losing run.
- Results by year, and with and without each filter.
- The share of profit from the best 10 trades.
- How many variants were tried.

```
for each day t, for each stock s in universe(t):
    if setup(s, t) and market_filter(t):
        candidates.append(s)
rank candidates by return_63(s, t); take up to free_slots
for each chosen s:
    entry = open[s, t+1]; skip if entry > 1.03 * close[s, t]
    stop  = entry - 2 * atr14[s, t]
    shares = floor(account * 0.01 / (entry - stop))
each day for each open trade:
    if low <= stop:              exit at min(open, stop)
    elif close < sma50:          exit at next open
    elif days_held == 20 and close < entry + (entry - stop): exit at next open
record every trade with its R, costs and the spec version
```

## 10. Checklist

- [ ] The idea fits in one sentence, and I know who is on the other side.
- [ ] Universe, filters, setup, entry, stop, exits, size and management are all written down.
- [ ] Every rule is true or false on a given day; no vague words remain.
- [ ] Every number is a named parameter with a first value, a range and a reason.
- [ ] Gaps through the stop are filled at the open.
- [ ] Costs and slippage for my market are in the spec.
- [ ] "Works" is defined: benchmark, period, minimum trades, measure, hurdle, and what would make me drop it.
- [ ] The spec has a version number and a date.

## Further reading

- Robert Pardo, *The Evaluation and Optimization of Trading Strategies* (2nd ed., 2008).
- Kevin J. Davey, *Building Winning Algorithmic Trading Systems* (2014).
- Van K. Tharp, *Trade Your Way to Financial Freedom* (2nd ed., 2007).
- Curtis M. Faith, *Way of the Turtle* (2007).
- David Aronson, *Evidence-Based Technical Analysis* (2006).
- Ernest P. Chan, *Quantitative Trading* (2008).
- Halbert White, "A Reality Check for Data Snooping", *Econometrica* 68 (2000).
- Ryan Sullivan, Allan Timmermann and Halbert White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", *Journal of Finance* 54 (1999).
- David H. Bailey, Jonathan M. Borwein, Marcos López de Prado and Qiji Jim Zhu, "Pseudo-Mathematics and Financial Charlatanism", *Notices of the American Mathematical Society* 61 (2014).
- Campbell R. Harvey, Yan Liu and Heqing Zhu, "… and the Cross-Section of Expected Returns", *Review of Financial Studies* 29 (2016).
