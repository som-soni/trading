# Scope: F&O strategies (NSE futures and options)

*2026-10-15. Feasibility established by probing the sources. **Stage 1 (ingest and reconcile) is
built**; stages 2-4 are not. See "Stage 1 is built" for what the reconciliation caught.*

The ask is real F&O strategies — not an F&O-eligibility filter on stocks, which
`--top-dollar-volume` already approximates. That means a new asset class: contracts with
an expiry and a strike, positions with more than one leg, and a payoff that is decided by
where the underlying settles rather than by a stop being hit.

This says what is available, what the existing code cannot absorb, and the smallest first
thing worth building.

## The data is there, back to 2005

NSE publishes a daily derivatives bhavcopy covering every contract traded that day. Probed
directly rather than taken on trust:

| date | format | rows | zipped |
|---|---|---:|---:|
| 2005-06-15 | legacy | — | 94 KB |
| 2012-06-15 | legacy | 31,097 | 308 KB |
| 2020-06-15 | legacy | 38,324 | 465 KB |
| 2022-06-15 | legacy | 64,136 | 766 KB |
| 2024-06-14 | legacy **and** UDiFF | 47,702 | 691 KB / 1.4 MB |
| 2026-10-09 | UDiFF | 36,983 | 1.15 MB |

Two layouts, overlapping through 2024, so the switchover can be checked against itself
rather than assumed:

```
legacy  INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,
        SETTLE_PR,CONTRACTS,VAL_INLAKH,OPEN_INT,CHG_IN_OI,TIMESTAMP
UDiFF   TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,
        FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,…
```

`INSTRUMENT` separates `FUTIDX / FUTSTK / OPTIDX / OPTSTK`; `OPTION_TYP` is `CE / PE / XX`.
Settle prices and open interest are both present, which is what makes a backtest possible
at all — a close of 0.00 on an untraded strike is useless, the settle is not.

`marketdata/financials.py` already has `_NseSession`, which solves NSE's cookie/browser-session
requirement. That is the part that usually costs a day.

**What is NOT there.** Implied volatility and greeks are not published; they would be computed
from settle, spot, time to expiry and a rate. Intraday is not available from this source, so
everything is end-of-day. **US options history is not freely available at all** (OPRA is paid;
yfinance gives only the current chain), so this is an India-only capability unless that is
bought.

## Volume, and why it needs filtering

Roughly 40,000 rows a day × ~250 days × 20 years ≈ **200 million rows** if everything is kept.
That is storable but not free, and most of it is strikes nobody traded.

The data is mostly waste at the tails: a single day carries every listed strike of every
underlying, and liquidity concentrates in a handful of near-the-money strikes of the index
and the top names. A first pass should keep futures in full (small — ~200 underlyings × 3
expiries ≈ 600 rows/day) and options filtered to what has open interest, with the filter
recorded so it can be loosened later without re-deriving what was dropped.

## What the existing code cannot absorb

This is the real cost, not the download.

**The price model assumes one row per symbol per day.** `prices` is keyed `(market, symbol,
date)`. A contract needs `(underlying, expiry, strike, type)` as well. This is a new table,
not a column on the old one.

**The simulator assumes a long position in shares with a stop.** `portfolio_sim` holds one
`PortfolioTrade` per symbol with `shares`, `stop`, `target`, and exits on price touching a
level. An option position needs: more than one leg priced together, a position that expires
whether or not anything is hit, assignment at expiry, and margin that is not simply
`shares × price` (a short option's requirement moves with the underlying). None of that is a
small edit to the existing loop — it is a second simulator that shares the reporting.

**The strategy contract assumes a per-symbol daily evaluation.** `Strategy.evaluate(ctx)`
answers "is this stock a buy today" from one symbol's bars. An options strategy decides a
*structure* — which expiry, which strikes, how many lots — from a volatility surface. The
registry already distinguishes per-symbol strategies from PORTFOLIO strategies
(`portfolio_strategies()`), so there is precedent for a third kind rather than forcing this
into the first.

**Costs and frictions are different.** STT on options is charged on the premium for sales and
on intrinsic value at exercise — the exercise case has bankrupted more backtests than any
slippage assumption. Lot sizes change over time and must be point-in-time. Expiry day moved
from Thursday to other weekdays more than once, and weekly expiries only exist from 2019.

## Staged plan

**1. Ingest and verify (the only stage that is clearly worth doing now).**
A `marketdata/derivatives.py` plus an `fno_bhav` job, both layouts, into a new table. The
verification is the point: the 2024 overlap lets legacy and UDiFF be reconciled row for row,
and futures settle should track the underlying's close within carry. Until that reconciles,
nothing built on top is trustworthy.

**2. A futures continuous series.** Rolling near-month into a continuous series with a
documented roll rule, so the existing equity strategies can be run on leverage without any
new strategy logic. This is the cheapest thing that produces a result, and it tests the
ingest under a real use.

**3. The options simulator.** Multi-leg positions, expiry, assignment, margin. Separate from
`portfolio_sim`, sharing its reporting and funnel.

**4. Strategies.** Covered calls on existing holdings; cash-secured puts as entries for the
Minervini screen (sell a put at the pivot instead of buying the breakout); long calls as a
leveraged expression of the same signal. Each is a question the equity backtests already set
up, which is why they are last rather than first.

## Stage 1 is built

`marketdata/derivatives.py` plus the `fno_bhav` job (data layer, daily, India only, index
derivatives unless `--all-instruments`). Both layouts normalise to one row shape; `reconcile()`
reads a day from each and compares.

The reconciliation earned itself twice before anything was built on top.

**Index futures were being dropped silently.** A futures row leaves `OptnTp` empty, pandas
reads it as NaN, and NaN is *truthy* — so `x or "XX"` kept the NaN and `str()` made it the
literal `"nan"`, which matched no instrument. Every index future from mid-2024 on vanished:
exactly the series stage 2 needs. The overlap day showed 15 rows in legacy and 0 in UDiFF.
After the fix: 7,422 contracts in both, zero differences in membership, settle or open interest,
across five days spanning the overlap.

**`close` is worse than useless on most of the book.** I had assumed an untraded strike closes
at 0.00. It does not: 5,246 of 7,407 index options on 2024-06-14 did not trade, their
open/high/low come through as 0.00, and `close` carries a STALE last-traded price. A deep
in-the-money BANKNIFTY 39500CE showed close 8,462.85 against settle 10,540.30 when intrinsic
alone was ~10,400. A backtest pricing off `close` would use old marks on 70% of contracts and
nothing would look wrong. `settle` is the exchange's daily mark; `contracts` says whether a
price is live.

The archives cross over narrowly — legacy stops between 2024-07-05 and 2024-07-08 — so the
ingest prefers UDiFF from 2024-07-01 and falls back.

`tests/test_derivatives.py` holds both findings: it fails if either layout loses its futures,
if the layouts disagree on an overlap day, or if settle and close stop differing on untraded
strikes (which would mean one column is not being read). Checked against both breakages
reintroduced deliberately.

## What I would not do

Build stages 3 and 4 before stage 1 reconciles. An options backtest that silently prices off
a stale settle, a wrong lot size or a missed expiry change will produce a confident number
and there is no equity-style sanity check to catch it — the whole point of options is that
the payoff is non-linear, so a small data error does not look like a small error in the result.

## Open questions

- **India only?** US options history is paid. Is this an India capability, or is buying US
  data in scope?
- **How much history?** 2005 is available; 2012 onward matches the equity backtests and
  halves the ingest. Weekly expiries only exist from 2019, which may matter more than depth.
- **Index only to start?** NIFTY and BANKNIFTY options are the liquid ones; stock options
  are thin outside the top names, and a backtest on thin strikes will flatter itself.
