# Start here — the vocabulary everything else assumes

**In short**

- A share is a slice of a company. An index is a basket of shares, and an index fund or ETF lets you buy the basket.
- A chart shows four prices per bar (open, high, low, close) and the volume traded.
- Every trade costs something: the spread, slippage, taxes and fees. Tax is often the largest of them.
- Losses and the gains that undo them are not symmetrical: a 50% loss needs a 100% gain to recover.
- Risk comes first: set the stop, size the position from it, and measure results in R.

This page covers what a share, an index and a chart are. It also covers how a trade happens, what it costs, and the arithmetic every other guide uses. If a sentence in another guide lost you, the missing piece is probably here.

**Nothing here is a strategy.** This is the floor the other guides stand on. For example, [the interest-rates guide](learn-macro-rates.md) opens with a central bank setting the price of overnight money. That sentence is hard to use until you know what overnight money is.

> **Words with a dotted underline** have a short definition. Hover over them, or tap on a phone. The same word is marked in every guide, so it does not matter which one you read first.

---

## 1. A share is a slice of a company

Say a company has issued 100 million shares and you own one. You then own one hundred-millionth of its future profits and of whatever it owns. A **share** is that unit of ownership.

Two numbers follow from that:

```
market cap = share price × number of shares     ← what the whole company is worth
EPS        = annual profit ÷ number of shares   ← profit belonging to one share
P/E        = share price ÷ EPS                  ← years of current profit you are paying
```

Take a company earning ₹200 crore a year with 20 crore shares. Its EPS is ₹10. At ₹250 a share its market cap is ₹5,000 crore and its P/E is 25. You are paying ₹25 for each ₹1 of annual profit.

**Where the price comes from.** Not from the company. A share price is the last price at which a buyer and a seller agreed. It changes when the balance of people wanting to buy and wanting to sell changes. Most of what moves it is a change in what people expect the company to earn in *future*.

That is why a company can report a record quarter and its share can fall. The record was already expected; the outlook for the next quarters was not.

**Dividends.** Some companies pay out part of their profit as cash, usually every quarter or every year. A price chart normally ignores dividends, so it understates what holding the share returned. On the S&P 500 the gap has been about 1.9% a year since 1990. On the Nifty it is about 0.8% a year. Returns that include dividends are called **total return**.

## 2. An index is a basket, and a fund lets you buy the basket

The Nifty 50 holds 50 large Indian companies. The S&P 500 holds 500 large US ones. An **index** like these tracks a group of shares as one number, so you can talk about a whole market. Most indices are weighted by market cap, so the biggest companies move the index most. That is why an index can rise while most of its members fall, the subject of [the breadth guide](learn-health-breadth.md).

You cannot buy an index directly. You buy a fund that holds it:

| | what it is | how you buy it |
|---|---|---|
| **Index fund** | holds every share in the index, in the index's proportions | from the fund house, priced once a day |
| **ETF** | the same, but the fund itself trades on the exchange | from the market, priced continuously |

Both charge an **expense ratio**: a yearly fee, as a percent of what you hold. It is taken out of the fund's value daily rather than billed to you. 0.20% on ₹1,00,000 is ₹200 a year.

That sounds trivial, but it compounds. Over 30 years, a fund charging 1.00% instead of 0.20% leaves you about a fifth less money at the end. (That assumes the investments earn 10% a year before fees.)

## 3. What a chart shows

Each bar is one period, one day on most charts in these guides. A **candle** carries four prices from that period:

```pattern
anatomy
```

The body spans the open to the close. The thin lines above and below, the **wicks**, mark the highest and lowest prices reached. The price touched those levels but did not stay there. Green (or hollow) means the close was above the open; red means it was below.

**Volume**, the bars usually drawn beneath the price, is how many shares changed hands. It measures how many people took part, not which way they pushed. A 4% rise on twice the normal volume is a different event from a 4% rise on half the normal volume. The first one took much more money to produce.

A **moving average** is the mean of the last N closing prices, recalculated each day. It smooths out the daily noise. The 50-day and 200-day averages are the two everyone watches. In these guides, "above its 200-day" is shorthand for "in an uptrend".

## 4. How a trade actually happens, and what it costs

You do not deal with the exchange. You hold an account with a **broker** and send orders through it.

- A **market order** executes immediately at whatever price is available. It is certain to fill, but the price is uncertain.
- A **limit order** executes only at your price or better. The price is certain, but it may not fill.

At any moment there is a highest price someone will pay (the **bid**) and a lowest price someone will accept (the **ask**). You buy at the ask and sell at the bid. The distance between them, the **bid-ask spread**, is a cost you pay twice: once going in and once coming out. **Slippage** is the broader version: the difference between the price you expected and the one you got.

Some costs are easy to forget and large when added up:

| | US | India |
|---|---|---|
| Brokerage | often zero | small, per order |
| Spread + slippage | ~2bps a side on a liquid share | ~10bps a side |
| Transaction tax | — | STT, on the value of each trade |
| Tax on gains | 15% long / 24% short (typical taxable account) | 12.5% LTCG above ₹1.25L / 20% STCG |

The last row is the one that decides things. A trader who sells every few months pays short-term tax on every gain, every year. Someone who holds for years pays tax only at the end, at the lower long-term rate. Meanwhile the untaxed gain keeps compounding.

A worked example shows the size of the gap. Take ₹1 lakh growing at 12% a year before tax for 10 years, under Indian rates:

| | taxed every year at 20% | taxed once at the end at 12.5% |
|---|---|---|
| Value after 10 years | ₹2.50 lakh | ₹2.84 lakh |
| Return per year after tax | 9.6% | 11.0% |

Same gross return, and the difference is 1.4 percentage points a year. At 15% a year before tax it grows to about 1.9 points. That is larger than most of the edges traders hunt for. (The example ignores the ₹1.25 lakh exemption, which would favour the long-term holder slightly more.)

## 5. The arithmetic every other guide uses

**Percent of what.** A fall from 100 to 50 is −50%. Getting back from 50 to 100 is +100%. Losses and the gains that undo them are not symmetrical. This is the single most important piece of arithmetic in trading:

| drawdown | gain needed to recover |
|---|---|
| −10% | +11% |
| −25% | +33% |
| −50% | +100% |
| −75% | +300% |

**Percentage points vs percent.** A rate going from 6% to 7% has risen *one percentage point*, not one percent. Because that is easy to confuse, rates are quoted in **basis points**. One basis point is a hundredth of a percentage point, so 6% → 7% is 100bps.

**Annualised.** Returns over different lengths of time are compared by converting them to a yearly rate. Doubling your money over ten years is not 10% a year. It is 7.2%, because each year compounds on the last:

```
CAGR = (end ÷ start)^(1 ÷ years) − 1
     = (2 ÷ 1)^(1 ÷ 10) − 1 = 7.2%
```

CAGR stops working when money goes *in* over time, as with a monthly SIP. Adding more money in later years changes the CAGR even if the investment itself behaved the same. The right measure is then **XIRR**: the yearly rate that turns each dated deposit into the final value.

**Real vs nominal.** A **nominal** figure is the number as quoted. A **real** figure has inflation taken out. 7% interest with 6% inflation is a 1% real return, and real is what buys things.

## 6. Risk, in one page

Everything in the risk guides rests on three ideas.

**The stop comes first.** Before buying, you decide the price at which you will admit the trade is wrong and sell. That price is the **stop**. Deciding it in advance is the whole point. Deciding it while losing money is how small losses become large ones.

**Size is calculated, not chosen.** Fix what being wrong may cost, say 1% of the account. The distance to the stop then tells you how many shares to buy:

```
shares = risk amount ÷ (entry − stop)
       = ₹10,000 ÷ (₹520 − ₹500) = 500 shares
```

A tighter stop buys more shares for the same risk; a wider stop buys fewer. The position size is an output, not a choice.

**Results are measured in R.** The example above risks ₹10,000, so that is its **R**: what the trade risked. Making ₹20,000 is +2R, and being stopped out is −1R. Stating results in R makes trades of different sizes comparable. It also lets you judge a method by its **expectancy**, the average R per trade:

```
expectancy = (win rate × average win) − (loss rate × average loss)
           = (0.40 × 2R) − (0.60 × 1R) = +0.2R per trade
```

Look at what that means. A method that is wrong 60% of the time can make money. A method that is right 70% of the time loses money if its losses are large enough. **Win rate alone tells you nothing.**

## 7. What a backtest can and cannot tell you

A **backtest** applies a fixed set of rules to past prices and records what they would have done. It is how most of the methods in these guides are judged. A good one includes costs, limits how many positions can be held at once, and assumes fills slightly worse than the chart shows.

Two things to hold on to while reading any backtest result:

- **A backtest is not a promise.** It is one path through history. The rules were usually chosen after seeing some of that history, which flatters them. A careful study states its own biases; read that section before trusting a number.
- **Most methods do not beat the index.** S&P's SPIVA reports, published twice a year, find that most professionally run stock funds trail their benchmark index over 10 and 15 years, in both the US and India. A rule set built at home faces the same odds. That is why these guides spend more time on risk than on entries.

[The backtesting guide](learn-test-backtesting.md) covers how to test a rule honestly.

## 8. Where to go next

| if you want to know | read |
|---|---|
| whether the market as a whole is healthy | [Reading the market's trend](learn-health-trend.md), then [Breadth](learn-health-breadth.md) |
| why interest rates move share prices | [Interest rates and central banks](learn-macro-rates.md) |
| how much to buy, and where the stop goes | [Position sizing](learn-risk-sizing.md), [Stops and exits](learn-risk-stops-exits.md) |
| whether a method makes money at all | [Expectancy](learn-risk-expectancy.md) |
| what the shapes on a chart mean | [Candlestick patterns](learn-candlestick-patterns.md), [Chart patterns](learn-chart-patterns.md) |
| which trading strategies exist and how they compare | [Strategies](learn-strat-overview.md) |
| how futures and options work | [Futures & options](learn-fno-overview.md) |

## 9. Checklist

Before moving on, check that you can define each of these without looking. Share, index, ETF, expense ratio, market cap, P/E, bid-ask spread, slippage, moving average, volume, basis point, CAGR, drawdown, stop, R, expectancy.

If any of them is still vague, hover it above. Every one is defined in place.
