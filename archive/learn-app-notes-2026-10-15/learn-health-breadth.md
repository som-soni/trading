# App notes moved from learn-health-breadth (rewrite, 2026-10-15)

## Intro (phrase)

> It covers the measures this app stores, and what divergences, washouts and breadth thrusts looked like in the stored data

## Where this shows in the app

**Where this shows in the app.** Markets → **Breadth** ("How healthy is the
market — risk, not direction"). The page is built from the app's daily breadth
table, `breadth_daily` (computed by `scripts/swing_screener/analytics/breadth.py`
and served by `/api/breadth` in `web/server.py`). Every reading is ranked
against all trading days since 2015. Breadth also supplies three of the six
**market tone** signals on Markets → Post-market (`analytics/postmarket.py`):
*more stocks rose than fell*, *more new 52-week highs than lows*, *half or more
of stocks above their 50-day average*.

## §1 (phrase)

> The page's framing is the right one: breadth *"helps judge how risky the market is, **not** which way it will go."*

## §2 How this app builds breadth (whole section; its general content is kept in the guide as a data note, without code names)

## 2. How this app builds breadth

Every trading day since **2015**, the app takes the **1,000 most-traded
stocks** in each market (`analytics/breadth.py`). They are ranked by 20-day
average turnover (the money value traded per day). So the set changes over
time as trading shifts between stocks. For those stocks it counts:

| Field | Definition in the code |
|---|---|
| Rising / falling (`adv`, `dec`) | close above / below the previous close |
| Up / down 4%+ (`up4`, `dn4`) | the day's big movers |
| 52-week highs / lows | today's high (low) is the extreme of the last 252 bars; needs ~200 bars of history |
| Above the 5 / 50 DMA | close above its 5- / 50-day simple average |
| Month ±25% (`up25m`, `dn25m`) | up / down 25%+ over the last 21 bars (±50% is stored too) |

**Only common stocks count.** The US list of stocks already excludes ETFs.
Closed-end funds (funds that trade like a stock) are also dropped when the
app's classification job flags them (`classify`). India's symbols are
classified as equity or fund, and funds are left out. Two consequences:

- **The two "1,000s" differ.** In the US the 1,000 most-traded are mostly
  large and mid-sized companies. In India the same count reaches well into
  small companies. So India's breadth is closer to a gauge of small and
  mid-sized stocks (§8).
- **The symbol list is today's** (a fixed ticker file). Stocks delisted since
  2015 are probably missing. Missing them likely leaves out some losers, so
  old readings may lean slightly strong.

## §3 The Breadth page, card by card (whole section)

## 3. The Breadth page, card by card

Each card shows today's value. A gauge ranks it against every day since 2015
("Only N in 100 days since 2015 were…"). A table compares it with one week, one
month and three months ago, because *"slow changes matter most: markets rarely
turn in a day."*

| Card (its real title) | What it shows | How to read it |
|---|---|---|
| **S&P 500 against its 50 DMA?** (Nifty 50 for India) | The index's % distance from its 50-day | The index's own short-term trend — the context |
| **Stocks at a 52w high or low?** | New highs and lows, and the typical day over two weeks | Leadership against damage; ranked on the 10-day average of highs − lows |
| **Stocks above their 5 & 50 DMA?** | % above the 5- and 50-day averages | 50-day: the average stock's trend; 5-day: short-term stretch |
| **Stocks rising or falling?** | Advancers and decliners, and the two-week typical day | Participation; ranked on the 10-day average of rising − falling |
| **Leading sectors, last 3 months?** | Best and worst sector against the average stock; sectors with most stocks above the 50-day | Where the strength is, and how widely shared |
| **Options: expected vs actual?** | VIX / India VIX against the index's realised volatility | See [the volatility guide](learn-health-volatility.md) |

Below the cards come:

- **What changed in the last 5 sessions**: 30% / 70% crossings, 90-day
  extremes, the index crossing its 50-day.
- Four **Charts**. The 50-day one has lines at **30% washout, 70% strong**.
- **Sectors: where the strength is?**
- **The last 30 days**, shaded where a reading is in its strongest or weakest
  fifth since 2015.

## §4.1 table labels

> | Days below 30% (the page's "washout") | 11% | 19% |
> | Days above 70% (the page's "strong") | 23% | 27% |

## §4.2 (phrase)

> Read the **net** (highs minus lows) and its 10-day average, as the page does.

## §4.3 (sentence)

> The app's version has no thinly traded micro caps or bond funds in it.

## §6 (sentence)

> The page calls **below 30%** a washout.

## §7 (sentences)

> The app does not compute one. A simple version, built from the stored counts of rising and falling stocks (`adv`, `dec`) with a 10-day exponential average, fired **11** times in the US since 2015.

## §9 What the app's strategies do with breadth

**What the app's strategies do with breadth.** The screener's market-regime
check (`core/regime.py`) computes the share of its stocks above the 20- and
50-day. But **no decision uses it**. The downgrade looks only at whether the
first two broad indices (SPY and QQQ; Nifty 50 and Nifty 500) are below their
50-day. Risk is halved only on the volatility index. Breadth is **your**
filter.

## §10 (phrase)

> Compare a reading with its own history, as the page's ranks do.

## §11 Checklist item

> - [ ] "What changed in the last 5 sessions": any 30% / 70% crossing?
