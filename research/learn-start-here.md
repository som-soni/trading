# Start here — the vocabulary everything else assumes

Learning material: what a share, an index and a chart actually are, how a
trade happens and what it costs, the arithmetic every other guide uses
(percent, annualised, basis points, R), and a one-page version of risk. If a
sentence in another guide lost you, the missing piece is probably on this
page.

**Nothing here is a strategy.** This is the floor the other guides stand on.
Read it once and the rest become readable; skip it and [learn-macro-rates.md](learn-macro-rates.md)
opens with "a central bank sets the price of overnight money", which is not a
sentence you can act on without knowing what overnight money is.

> **Words with a dotted underline** have a short definition — hover them, or
> tap on a phone. You never have to leave the page to look something up, and
> the same word is marked in every guide, so it does not matter which one you
> read first.

---

## 1. A share is a slice of a company

A **share** is a unit of ownership. If a company has issued 100 million shares
and you own one, you own one hundred-millionth of its future profits and of
whatever it owns.

Two numbers follow from that:

```
market cap = share price × number of shares     ← what the whole company is worth
EPS        = annual profit ÷ number of shares   ← profit belonging to one share
P/E        = share price ÷ EPS                  ← years of current profit you are paying
```

A company earning ₹200 crore a year with 20 crore shares has an EPS of ₹10. At
₹250 a share it has a market cap of ₹5,000 crore and a P/E of 25 — you are
paying ₹25 for each ₹1 of annual profit.

**Where the price comes from.** Not from the company. A share price is just the
last price at which a buyer and a seller agreed, and it changes when the
balance of people wanting in and wanting out changes. Most of what moves it is
a change in expectations about *future* profit, which is why a company can
report a record quarter and the share can fall: the record was already
expected, and the outlook was not.

**Dividends.** Some companies pay out part of their profit as cash, usually
quarterly or yearly. A price chart normally ignores dividends, so it
understates what holding the share actually returned — by roughly 1.9% a year
on the S&P 500 and 0.8% a year on the Nifty, measured over the windows this
project uses. Returns that include them are called **total return**.

## 2. An index is a basket, and a fund lets you buy the basket

An **index** tracks a group of shares as one number so you can talk about a
whole market. The Nifty 50 is 50 large Indian companies; the S&P 500 is 500
large US ones. Most are weighted by market cap, so the biggest companies move
the index most — which is why an index can rise while most of its members fall,
the subject of the breadth guide.

You cannot buy an index directly. You buy a fund that holds it:

| | what it is | how you buy it |
|---|---|---|
| **Index fund** | holds every share in the index, in the index's proportions | from the fund house, priced once a day |
| **ETF** | the same, but the fund itself trades on the exchange | from the market, priced continuously |

Both charge an **expense ratio** — an annual fee as a percent of what you hold,
taken out of the fund's value daily rather than billed to you. 0.20% on
₹1,00,000 is ₹200 a year. It sounds trivial and compounds to real money:
0.20% against 1.00% over 30 years is roughly a quarter of the final pot.

## 3. What a chart shows

Each bar is one period — one day, on most charts here. A **candle** carries
four prices from that period:

```pattern
anatomy
```

The body spans the open to the close; the thin **wicks** mark the extremes the
price reached and did not hold. Green (or hollow) means the close was above the
open, red means below.

**Volume**, the histogram usually drawn beneath, is how many shares changed
hands. It measures participation, not direction: a 4% rise on volume twice the
normal is a different event from a 4% rise on half the normal, because the
first one took real money to produce.

A **moving average** is the mean of the last N closing prices, redrawn each
day. It is a smoothing device — the 50-day and 200-day are the two everyone
watches, and "above its 200-day" is shorthand for "in an uptrend" throughout
these guides.

## 4. How a trade actually happens, and what it costs

You do not deal with the exchange. You hold an account with a **broker** and
send orders through it.

- A **market order** executes immediately at whatever price is available —
  certain to fill, uncertain in price.
- A **limit order** executes only at your price or better — certain in price,
  uncertain to fill.

At any moment there is a highest price someone will pay (the **bid**) and a
lowest price someone will accept (the **ask**). You buy at the ask and sell at
the bid, so the distance between them — the **bid-ask spread** — is a cost you pay
twice, once going in and once coming out. **Slippage** is the broader version:
the difference between the price you expected and the one you got.

Costs that are easy to forget and large in aggregate:

| | US | India |
|---|---|---|
| Brokerage | often zero | small, per order |
| Spread + slippage | ~2bps a side on a liquid share | ~10bps a side |
| Transaction tax | — | STT, on the value of each trade |
| Tax on gains | 15% long / 24% short (typical taxable account) | 12.5% LTCG above ₹1.25L / 20% STCG |

The last row is the one that decides things. A strategy trading monthly pays
short-term rates on everything it makes; one that holds for years defers tax
entirely. In the index-investing work in this repo that difference was worth
1–3 percentage points a year — larger than most of the effects being tested.

## 5. The arithmetic every other guide uses

**Percent of what.** A fall from 100 to 50 is −50%; getting back from 50 to 100
is +100%. Losses and the gains that undo them are not symmetrical, which is the
single most important piece of arithmetic in trading:

| drawdown | gain needed to recover |
|---|---|
| −10% | +11% |
| −25% | +33% |
| −50% | +100% |
| −75% | +300% |

**Percentage points vs percent.** A rate going from 6% to 7% has risen *one
percentage point*, not one percent. Because that is ambiguous, rates are quoted
in **basis points**: one basis point is a hundredth of a percentage point, so
6% → 7% is 100bps.

**Annualised.** Returns over different lengths are compared by converting them
to a yearly rate. Doubling your money over ten years is not 10% a year — it is
7.2%, because each year compounds on the last:

```
CAGR = (end ÷ start)^(1 ÷ years) − 1
     = (2 ÷ 1)^(1 ÷ 10) − 1 = 7.2%
```

When money is going *in* over time — a monthly SIP — CAGR no longer answers the
question, because contributing more in later years changes it without anything
about the strategy changing. The right measure is **XIRR**, the annual rate that
makes dated deposits add up to the final value.

**Real vs nominal.** A **nominal** figure is the number as quoted; a **real**
one has inflation taken out. 7% interest with 6% inflation is a 1% real return,
and real is what buys things.

## 6. Risk, in one page

Everything in the risk guides rests on three ideas.

**The stop comes first.** Before buying, you decide the price at which you will
admit the trade is wrong and sell — the **stop**. Deciding it in advance is the
whole point; deciding it while losing money is how small losses become large
ones.

**Size is calculated, not chosen.** Fix what being wrong may cost — say 1% of
the account — and the distance to the stop tells you how many shares to buy:

```
shares = risk amount ÷ (entry − stop)
       = ₹10,000 ÷ (₹520 − ₹500) = 500 shares
```

A tighter stop buys more shares for the same risk, a wider stop fewer. The
position size is an output.

**Results are measured in R.** One **R** is what the trade risked. The example
above risks ₹10,000, so making ₹20,000 is +2R and being stopped out is −1R.
Stating results in R makes trades of different sizes comparable, and lets a
strategy be judged on **expectancy** — the average R per trade:

```
expectancy = (win rate × average win) − (loss rate × average loss)
           = (0.40 × 2R) − (0.60 × 1R) = +0.2R per trade
```

Note what that means: a strategy that is wrong 60% of the time makes money,
and a strategy that is right 70% of the time loses money if its losses are
large enough. **Win rate alone tells you nothing.**

## 7. What this app is, and what it is not

It screens and backtests; it does not trade. Nothing here places an order or
connects to a broker. The screener produces a list of candidates each day from
stored price data, and the backtester measures whether a set of rules would
have made money in the past — with costs, with a cap on how many positions can
be held at once, and with deliberately pessimistic fills.

Two things to hold on to while reading any result in this project:

- **A backtest is not a promise.** It is one path through history, with the
  rules chosen after seeing some of that history. The research logs state
  their own biases; read those sections before trusting a number.
- **Most of what is tested here did not work.** The honest summary of
  [momentum-trend-research.md](momentum-trend-research.md) is that no hand-built strategy in this repo has
  beaten simply holding the index in both markets. That is a normal result,
  and a reason the guides spend more time on risk than on entries.

## 8. Where to go next

| if you want to know | read |
|---|---|
| whether the market as a whole is healthy | [learn-health-trend.md](learn-health-trend.md), then [learn-health-breadth.md](learn-health-breadth.md) |
| why interest rates move share prices | [learn-macro-rates.md](learn-macro-rates.md) |
| how much to buy, and where the stop goes | [learn-risk-sizing.md](learn-risk-sizing.md), [learn-risk-stops-exits.md](learn-risk-stops-exits.md) |
| whether a strategy makes money at all | [learn-risk-expectancy.md](learn-risk-expectancy.md) |
| what the shapes on a chart mean | [learn-candlestick-patterns.md](learn-candlestick-patterns.md), [learn-chart-patterns.md](learn-chart-patterns.md) |
| when to put money into an index | [index-investing-research.md](index-investing-research.md) |

## 9. Checklist

Before moving on, you should be able to say what each of these is without
looking: share, index, ETF, expense ratio, market cap, P/E, bid-ask spread,
slippage, moving average, volume, basis point, CAGR, drawdown, stop, R,
expectancy.

If any of them is still vague, hover it above — every one is defined in place.
