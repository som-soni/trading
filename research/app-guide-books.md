# Using the app — your books: the trade ledger, open positions, paper books, and the monthly and daily routines

**In short**

- A **book** is the money you run under one strategy in one market. Its holdings are not typed in: they are
  derived from its **trade ledger** — an opening balance and every trade since.
- **Monthly** (portfolio strategies: momentum, dual momentum, the combination): on the month's last session,
  compare the book with Kite, read the orders, **Confirm rebalance**, place the orders by hand, record the fills.
- **Daily** (signal strategies): after the close routine, read **Today → Open positions**; move a raised stop,
  sell at the open what says so; **Take a setup…** when you buy one.
- **Paper books** trade each strategy forward without money, by the same rules, so every strategy builds a
  record no earlier decision could have seen.
- The app never places an order. Kite is read-only; you trade on Kite's own screens.

## 1. Books and the ledger

A book is named for its strategy (`momentum_baseline`, `darvas`) and lives in one market. Each change to it
is a row of the ledger (`book_trades`, `backtesting/ledger.py`):

| Row | What it records | Effect on the book |
|---|---|---|
| OPEN | A position the book started with (the account as saved before the ledger) | Shares added; cash unchanged; cost unknown |
| BUY | Shares bought at a price, with costs | Shares added; cash down by price × shares + costs |
| SELL | Shares sold at a price, with costs | Shares removed; cash up by price × shares − costs |
| CASH | Money in or out, or a reconciliation | Cash moved by the amount |

The holdings, average cost, cash and realised P&L are computed from these rows every time they are read
(`ledger.holdings`). A sale of more shares than the book holds is refused, and the whole save with it.

Each row says where it came from: **manual** (the account form, a confirmed rebalance, a taken setup),
**kite** (fills confirmed from a Kite comparison) or **paper** (the paper job). A mistaken row can be removed
from the **Ledger** list under *Your account* (click it); the rest must still add up.

The account form is still there, on each portfolio strategy's **Candidates** (Holdings) tab. It no longer
overwrites anything: **Review changes…** shows the difference from the ledger as proposed trades at the latest
stored close, plus one CASH row that brings the cash to what you entered. Correct each price to your real fill,
untick what was not a trade, then **Record ticked trades**.

## 2. The monthly routine — portfolio strategies

Momentum baseline, volatility-scaled momentum, dual momentum and the momentum + dual momentum combination
trade only at the close of the **last session of each month**. The tab says so: "This is November's last
session: these are the rebalance orders", or "Not a rebalance day".

| # | Where | What to do |
|---|---|---|
| 1 | Strategies → the strategy → Candidates | Choose the market. Wait for the ranking (up to a minute on the first load) |
| 2 | *Your account* → **Compare with Kite…** | Your Kite holdings against the ledger, as proposed fills at Kite's last price. A stock this book has never held starts unticked. Record only what belongs to this book |
| 3 | *Rebalance orders* | SELL ALL / TRIM / BUY / ADD / HOLD per stock, sized in whole shares as the backtest sizes them, with the costs at the strategy's own rate |
| 4 | *Drift from the model book* | Where your holdings and the model differ (§2.1) |
| 5 | **Confirm rebalance…** | Stores the targets and orders as computed now (`book_rebalances`) and offers the fills, each carrying the rebalance's number |
| 6 | Kite | Place the orders by hand. Sells first: they free the cash |
| 7 | Back on the tab | Correct each fill's price and cost from the contract note; **Record ticked trades** |

The backtest trades at the next session's open after the month-end close. Placing the orders before the
next open matches it; a fill later in the day is a different price, and the ledger records what you paid.

### 2.1 Orders start from what you hold

A strategy with a rank buffer (`hold_rank`) keeps a held stock while it still ranks inside the band, so the
decision depends on what is held. The orders are computed from **your** holdings, not from the model's. The
model book — the strategy replayed over 36 month-ends from an empty book — is shown beside them, in the
*model* column and the drift note:

- "The model holds, you don't" — a stock the rules would have bought earlier and you never did.
- "You hold, the model doesn't" — a stock you bought that the model would have rotated out of, or that the
  buffer keeps for you but not for the model.

Neither is an error. The drift says how far your book is from the measured one, and why.

### 2.2 The combination and dual momentum

The combination's tab sizes both sleeves on its book's value, when the book has one; type an account size to
override it. The momentum sleeve's stocks show *held* and *change*. The dual sleeve holds one asset through a
fund you choose (its tab names the instrument, such as MON100 for the Nasdaq 100 in rupees), so its order is an
amount: record the fund's trade with the account form. Dual momentum's own Candidates tab shows its pick and
its book.

## 3. The daily routine — signal strategies

The signal strategies (Darvas box, Donchian channel, Supertrend, Stage analysis, RS leaders, EMA pullback …)
manage an open trade with an exit that depends on every bar since the entry: a trailing stop, a close below an
average, a Darvas box, the 30-week line. The **positions** job runs in the close routine after the strategies.
It replays each open trade's stored bars through the backtest's own exit code (`portfolio_sim.manage_exit`,
under the strategy's `backtest_args`) and stores where it stands (`position_status`, `backtesting/tracker.py`).

| # | Where | What to do |
|---|---|---|
| 1 | Today → Data health | No action on a stale day |
| 2 | Today → **Open positions** | Read each status (below). The *needs action* count is beside the title |
| 3 | Kite | Move each raised stop; place a sell at the open for each exit |
| 4 | Today → Today's setups | Choose the setups you will buy. Size from your own equity |
| 5 | Kite, then Today → **Take a setup…** | After the fill: the setup, shares, fill price, costs and date. The setup's stop is the initial stop |
| 6 | The next morning | Record exits and stop fills as SELLs on the strategy's book (the Ledger, or the account form) |

| Status | Meaning | What to do |
|---|---|---|
| Hold | Nothing fired; the stop is unchanged | Nothing |
| Stop raised — move your stop order | The trailing rule lifted the stop on the latest session | Move the stop order on Kite to the new stop |
| Sell part at the next open | The exit ladder sold part of the position (Minervini) | Sell that part |
| Closed below the line — rest a sell-stop at today's low for the next session | The `ma_low` exit (100-day EMA trend) is armed: the session closed below its line, so the next one sells if it trades under that session's low | Place a sell-stop at the shown stop for one session. A close back above the line cancels it |
| Exit triggered — sell at the next open | A close-based exit fired (a close below the line, a turned Supertrend, a failed breakout) | Sell at the next open. The backtest sold at that close; you sell at the next open |
| Stop reached — sell at the open unless your stop order filled | The low reached the stop | If your stop order rested, it filled: record the SELL. If not, sell at the open |

*To stop* is how far the latest close is above the stop, in percent. *R now* is the open gain in units of the
risk you entered with: (close − entry) ÷ (entry − initial stop).

A taken setup is listed as *Not yet tracked* until the next positions run; taking one asks the queue for that
run. The Darvas box's levels come with the setup, so its trailing boxes start from the box you bought. Setups
whose exit reads levels the stored run does not carry fall back to the strategy's defaults.

## 4. Paper books

**Strategies → Paper books** lists each paper book and starts new ones (a strategy and its paper capital,
the market's configured account by default). A paper book is named `<strategy>@paper` and its ledger is the
**paper** job's alone (`backtesting/paper.py`; close routine, after positions):

| Strategy kind | Decided on | Filled at |
|---|---|---|
| Momentum, volatility-scaled momentum | The month's last close, from what the paper book holds | The next open: sell what left, then each target at its weight of the account valued at that open, whole shares |
| Dual momentum | The month's last close: the pick | The next session's level of the pick's series — the asset its backtest prices, not a fund |
| The combination | The month's last close, both sleeves | As above, each sleeve at its own cost |
| Signal strategies | Each run's tradeable setups | The next open, sized on the setup's stop at the market's risk per trade, up to the market's position limit. Exits follow the tracker: at the stop, or the next open |

Every fill pays the strategy's own cost per side. A decision waits under *Waiting for the next open* until that
session is stored, so a late job run fills at the right price, not at the day it ran. A month-end the job
missed is decided on the first close after it.

A book's page shows its value each session against the benchmark rebased to the same capital, the deepest
fall, holdings and every trade.

What a paper fill is not: a stock that gaps or trades thinly fills worse in reality, and a Minervini partial
sale is not paper-traded (the position exits whole). Read a paper book as the rules' forward record, not as
the result you would have had.

## 5. What is stored where

| Table | What it holds |
|---|---|
| `book_trades` | Every ledger row, with source, rebalance id, setup, initial stop, target and the signal's levels |
| `book_rebalances` | Each confirmed (or paper) rebalance: the close it was computed on, the strategy's spec id, targets and orders |
| `book_positions`, `book_cash` | The ledger's holdings, kept in step: a snapshot for anything that reads it |
| `position_status` | Each open signal trade's stop, status, R and distance to the stop after the latest close |
| `books`, `paper_orders` | Paper books, and their decisions waiting for the next open |

Related: [the pages](app-guide-pages.md), [reading backtests](app-guide-backtests.md),
[how the app computes its numbers](app-guide-how-it-computes.md).
