# Event trades with options — results, RBI policy, the Budget and elections

**In short**

- Before a scheduled event, options price in an expected move. The at-the-money straddle for the first expiry after the event is the market's estimate of it.
- After the event, implied volatility drops sharply whatever happens: the volatility crush. An option buyer needs a move *bigger than the straddle*, not just a move.
- India VIX fell from the day before to the day after in 9 of 10 Budgets since 2017 and in all three general-election results since 2014. Big index moves on those days were still rare.
- Compare the implied move with the stock's own history of event moves. Buy when the market prices in clearly less than usual; sell, with capped risk, when it prices in clearly more.
- Close event positions on the first session after the event. The trade is about the event, not about what follows.

## 1. The idea

### Reliance before its results, 15 October 2026

Reliance Industries was due to report September-quarter results on 16 October 2026. At 10:15 the day before, the stock was at 1,200.90. For the 27 October expiry, the 1,200 call traded at 23.25. The 1,200 put traded at 20.20.

```series
title: Reliance Industries and its results days, July 2025 – October 2026
from: 2025-07-01
to: 2026-10-14
tf: D
line: india:RELIANCE.NS | Reliance
line: india:RELIANCE.NS@vol | Volume | pane2 bars
mark: 2025-10-17 | results
mark: 2026-01-16 | results
mark: 2026-04-24 | results
mark: 2026-07-17 | results
caption: Over the two sessions around each results date, Reliance moved +4.9% (October 2025), −3.1% (January 2026), +1.7% (April 2026) and +2.0% (July 2026). It closed at 1,175 on 14 October 2026.
```

The straddle costs 43.45 rupees per share. That is 3.6% of the price, and ₹21,725 for one lot of 500 shares. It covers the results and eight sessions to expiry. So the market expected Reliance to end about 3.6% away from 1,200 on 27 October, in one direction or the other.

```payoff
title: Long straddle on Reliance into results — 1,200 strike, 27 Oct 2026
underlying: 1200.9
lot: 500
range: 1100 1300
leg: buy call 1200 @ 23.25
leg: buy put 1200 @ 20.2
before: 8d 22%
caption: Prices at 10:15 on 15 October 2026 (intraday; they moved during the day). Breakevens at expiry are about 1,157 and 1,243. The blue line is the value just after the results, with 8 days left, if implied volatility drops to 22%: with no move, the buyer is already behind.
```

### The question every event trade asks

Is the market's estimate too small or too big? The stock's own history gives a first answer. The table shows what Reliance did over the eight sessions starting just before each of its last 20 results.

| Reliance, results since mid-2021 | Value |
|---|---|
| Results events measured | 20 |
| Median absolute move over 8 sessions | 4.1% |
| Windows that moved more than 3.6% | 13 of 20 |
| Median absolute move over the 2 sessions around results | 3.0% |
| Largest 2-session move | 5.4% (July 2024, down) |

*Method: close of the session before the results date to the close 8 sessions later; and to the close of the first session after the results date. Prices are split-adjusted daily closes.*

On this history the straddle looked a little cheap: Reliance's past results windows usually moved more than 3.6%. But 20 events is a small sample. Twenty quarters ago Reliance was a different mix of businesses.

### Who is on the other side, and the crush

Before results, nobody knows the numbers. Option sellers demand more for that uncertainty, so implied volatility rises into the event. Once results are out, the uncertainty is gone, and implied volatility falls back to normal within minutes of the next open. That fall is the **volatility crush**.

The buyer of a straddle is paying for the event *and* for the uncertainty premium that will vanish. The seller is collecting both. The seller wins when the move is smaller than the straddle; the buyer wins when it is bigger.

### Is there an event premium in the price?

An event shows up as a *term-structure* bump. **Term structure** is implied volatility across expiries. If results were expected to cause a big jump, the 27 October options would carry higher implied volatility than the 23 November options. In the snapshot they did not.

| Reliance, 15 Oct 2026, 1,200 strike | 27 Oct expiry | 23 Nov expiry |
|---|---|---|
| Call / put last price | 23.25 / 20.20 | 43.30 / 35.50 |
| Straddle, % of price | 3.6% | 6.6% |
| Implied volatility, call / put | 26.6% / 23.5% | 25.0% / 26.0% |
| Average implied volatility | about 25.0% | about 25.5% |

Both expiries priced Reliance at about 25% annual volatility. At this moment the market was not charging a visible premium for the results.

## 2. When it works and when it doesn't

The idea works when the market misjudges the size of the move. That happens in a few recurring ways:

- **A company whose events have changed.** A business that used to react little can start moving more, after a new segment or a change in sentiment. Implied moves lag that change.
- **Crowded selling.** In India, many traders sell options around events. When everyone sells, premiums can fall below the event's real risk.
- **Binary political events.** Election results have two very different outcomes. The market can underprice the less likely one, as on 4 June 2024.

It fails when the market has priced the event fairly. Then the buyer pays the crush and the seller earns a premium that just covers the risk. After costs, both lose a little.

### Macro events in India: what India VIX did

The table covers the scheduled events with the largest market interest. VIX columns are closes; "one-day VIX move" is India VIX on the day before divided by √252, the one-day move a 30-day volatility implies.

| Event | Date | VIX day before | VIX on the day | VIX day after | Nifty on the day | One-day VIX move |
|---|---|---|---|---|---|---|
| Election results | 16 May 2014 | 36.8 | 24.3 | 20.6 | +1.1% | 2.3% |
| Election results | 23 May 2019 | 27.6 | 19.4 | 16.5 | −0.7% | 1.7% |
| Election results | 4 Jun 2024 | 20.9 | 26.8 | 18.9 | −5.9% | 1.3% |
| Budget | 1 Feb 2017 | 16.8 | 14.0 | 13.5 | +1.8% | 1.1% |
| Budget | 1 Feb 2018 | 15.9 | 14.1 | 15.3 | −0.1% | 1.0% |
| Interim Budget | 1 Feb 2019 | 17.1 | 15.7 | 15.7 | +0.6% | 1.1% |
| Budget | 5 Jul 2019 | 13.5 | 13.1 | 13.9 | −1.1% | 0.9% |
| Budget | 1 Feb 2021 | 25.3 | 23.3 | 23.4 | +4.7% | 1.6% |
| Budget | 1 Feb 2022 | 22.0 | 20.0 | 18.7 | +1.4% | 1.4% |
| Budget | 1 Feb 2023 | 16.9 | 16.8 | 15.7 | −0.3% | 1.1% |
| Interim Budget | 1 Feb 2024 | 16.1 | 14.5 | 14.7 | −0.1% | 1.0% |
| Budget | 23 Jul 2024 | 15.4 | 12.8 | 11.8 | −0.1% | 1.0% |
| Budget (Saturday session) | 1 Feb 2025 | 16.3 | — | 14.4 | −0.1% | 1.0% |
| RBI emergency cut | 27 Mar 2020 | 71.5 | 70.4 | 71.9 | +0.2% | 4.5% |
| RBI off-cycle hike | 4 May 2022 | 20.3 | 21.9 | 20.3 | −2.3% | 1.3% |
| RBI rate cut | 7 Feb 2025 | 14.2 | 13.7 | 14.5 | −0.2% | 0.9% |
| RBI cut of 0.5 point | 6 Jun 2025 | 15.1 | 14.6 | 14.7 | +1.0% | 1.0% |

*Method: Nifty 50 and India VIX daily closes. "Day after" is the next trading session. No VIX close is stored for the Saturday session of 1 February 2025.*

Three patterns stand out:
1. **The crush is reliable for Budgets and elections.** India VIX was lower the day after than the day before in 9 of 10 Budgets and 3 of 3 election results.
2. **Most Budget days are quiet for the index.** Nifty moved less than the one-day VIX move in 7 of the 10 Budgets. The exceptions (2017, July 2019 and 2021) were moves of 1% to 5%.
3. **RBI days are smaller events for the index.** VIX did not fall reliably after them. Banks, lenders and rate-sensitive sectors react more than Nifty does.

India VIX measures 30-day volatility, so it understates the move expected on the event day itself. The weekly options that expire just after an event carry much more of the event premium.

### Company results in India

Results move single stocks far more than macro events move the index.

| Results study, India, Nov 2020 – Oct 2026 | All stocks | Most-traded fifth |
|---|---|---|
| Results events | 6,425 | 1,285 |
| Stocks | 379 | 161 |
| Median absolute 2-session move around results | 3.1% | 2.7% |
| Median absolute 2-session move on normal days | 1.8% | 1.5% |
| Median ratio, results move to normal move | 1.7× | 1.7× |
| Results moves more than twice the normal move | 44% | 44% |
| Results moves above 5% | 30% | 25% |
| Results moves above 10% | 7% | 4% |

*Method: stored results dates of Indian companies. The move runs from the close before the results date to the close of the first session after it. "Normal" is the stock's median 2-session move over the previous 250 sessions. "Most-traded fifth" is the top 20% by median daily turnover. The stock list is today's, so delisted companies are missing (survivorship bias).*

A results window moves a typical stock about 1.7 times as much as an ordinary two days. About one result in four moves the stock by more than 5%.

### India specifics

- **Timing.** Indian companies may announce during market hours or after the close. The Budget speech starts at 11:00 and the RBI announces at 10:00, both during trading. Election counting starts early in the morning and runs through the day.
- **Lot sizes and contract value.** Stock option lots are large: Reliance's is 500 shares. One at-the-money straddle cost over ₹21,000.
- **Physical settlement.** Stock options left in the money at expiry become delivery. Close them first.
- **Margin.** Option sellers need margin; near expiry, exchanges add more. An event on expiry day is the costliest case for a seller.
- **Shorting.** You cannot hold a short stock position overnight in the cash market. A put or a bear put spread is the way to bet on a fall after results.

**In the US.** US stock options trade with many weekly expiries, so traders can buy the expiry that ends right after results. Brokers and data vendors publish the implied earnings move for each stock. Earnings are almost always released before the open or after the close, never during trading. FOMC days and CPI releases play the role of the RBI and the Budget.

## 3. The rules

Two playbooks. **Playbook B** buys the event move when it looks cheap. **Playbook S** sells it, with capped risk, when it looks expensive.

### Universe and filters

1. A scheduled event with a confirmed date before the expiry you will trade.
2. For stocks: listed options, and at least **8** past events of the same kind with price history.
3. The at-the-money bid–ask spread is at most **2%** of the mid price, on the expiry you will trade.
4. Open interest of at least **500 contracts** at each strike you trade.

### Setup

Compute two numbers at the last close before entry:

- **Implied move (IM):** the at-the-money straddle price for the first expiry after the event, divided by the underlying price.
- **Historical move (HM):** the median absolute move over the same number of sessions, starting the session before each of the last **8–12** events.

Then:

- **Playbook B:** IM ≤ **0.85 × HM**.
- **Playbook S:** IM ≥ **1.2 × HM**, and the front-expiry implied volatility is at least **3 points** above the next expiry's.
- Otherwise, no trade.

For Reliance on 15 October 2026, IM was 3.6% and HM (8 sessions) was 4.1%. The ratio was 0.88. That is close to Playbook B's line, but not over it: no trade under the strict rule.

### Entry

- **Playbook B:** buy the at-the-money straddle, or a strangle with strikes about **0.5 × IM** from the price. Enter **1–3 sessions** before the event, since implied volatility tends to rise into it.
- **Playbook S:** sell the at-the-money straddle and buy wings about **1 × IM** away on each side (an **iron fly**). Enter in the last session before the event, near the close.
- Use limit orders at the mid price, stepping at most **3 ticks** toward the worse side.

### Initial stop

- Both playbooks are defined-risk. The stop is the structure itself: the premium paid (B) or the wing width minus the credit (S).
- No price stop inside the event window. Gaps jump over them.

### Exits

- **Time exit (both):** close everything by the end of the **first session** after the event.
- **Early profit (B):** if the move reaches **1.5 × IM** at any point in that session, close at least half.
- **Early profit (S):** if the iron fly can be bought back for **50%** or less of the credit, close it.
- **Invalidation:** the event is postponed. Close the trade; its reason has gone.

### Position size

- Maximum loss per event trade: **0.5–1%** of the account.
- Total maximum loss across all trades on the same event day: **2%**.
- Results of companies in one sector on the same day count as one event.

### Managing the trade

There is little to manage: place the trade, let the event happen, close it. Do not roll a losing event trade into the next expiry; that turns an event trade into a different, unplanned position.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Past events for HM | 8–12 | Stability of the history | Fewer is noisy; more reaches back to a different company |
| HM window | Sessions to expiry | Like-for-like comparison | Use 2 sessions if the expiry is right after the event |
| Buy threshold | IM ≤ 0.85 × HM (0.75–0.9) | How cheap the move must be | Lower = fewer, better trades |
| Sell threshold | IM ≥ 1.2 × HM (1.1–1.4) | How rich the move must be | |
| Term-structure check | Front IV ≥ next IV + 3 points | Proof that an event premium exists | Without it there is no crush to sell |
| Buyer entry | 1–3 sessions before | Captures the rise in IV into the event | Earlier entry pays more theta |
| Strangle distance | 0.5 × IM | Cost against needed move | |
| Iron fly wing distance | 1 × IM (0.75–1.5) | Seller's maximum loss | Closer wings: smaller credit and smaller loss |
| Time exit | End of first session after | Exposure to post-event drift | The edge is in the event, not after |
| Early profit, buyer | 1.5 × IM | Locking in a big move | Prices often retrace after a gap |
| Early profit, seller | 50% of credit | Time in the trade | |
| Risk per event | 0.5–1% of account | Survival | |
| Risk per event day | 2% | Clustering of events | |
| Spread filter | ≤ 2% of mid | Costs | Stock options away from the money fail this often |
| Open interest | ≥ 500 contracts | Exit liquidity | |

## 5. Variations

Each structure below asks the same question in a different shape, with real premiums from the 15 October 2026 snapshot.

**Long strangle.** Cheaper than a straddle, but it needs a bigger move.

```payoff
title: Long strangle on Reliance — buy 1,180 put and 1,220 call, 27 Oct 2026
underlying: 1200.9
lot: 500
range: 1100 1300
leg: buy put 1180 @ 11.65
leg: buy call 1220 @ 14.9
caption: Debit 26.55 per share, ₹13,275 per lot of 500. Breakevens at expiry are about 1,153 and 1,247, slightly wider than the straddle's, for 60% of the cost.
```

**Short iron fly.** The seller's version, with a cap on the loss.

```payoff
title: Short iron fly on Reliance — 1,160 / 1,200 / 1,240, 27 Oct 2026
underlying: 1200.9
lot: 500
range: 1100 1300
leg: sell call 1200 @ 23.25
leg: sell put 1200 @ 20.2
leg: buy call 1240 @ 9.9
leg: buy put 1160 @ 6.3
caption: Credit 27.25 per share. Maximum profit ₹13,625 per lot if Reliance settles at 1,200; maximum loss ₹6,375 beyond either wing. Breakevens are about 1,173 and 1,227.
```

**Index event iron fly.** For a Budget or policy day, the weekly Nifty expiry just after the event is the natural choice. This one uses the 19 October weekly.

```payoff
title: Short iron fly on Nifty — 22,600 / 22,900 / 23,200, 19 Oct 2026
underlying: 22913.9
lot: 65
range: 22300 23500
leg: sell call 22900 @ 146.6
leg: sell put 22900 @ 127.25
leg: buy call 23200 @ 34.75
leg: buy put 22600 @ 43.25
caption: Credit 195.85 points. Maximum profit ₹12,730 per lot; maximum loss ₹6,770. The 22,900 straddle alone priced a move of about 1.2% over the two and a half sessions to this expiry.
```

**Directional after the event.** Some traders skip the event and trade the drift after it. A stock that gaps on strong results often keeps rising for weeks. A bull call spread on the next month limits the cost once the crush has happened.

```payoff
title: Bull call spread on Reliance — buy 1,200 call, sell 1,250 call, 23 Nov 2026
underlying: 1200.8
lot: 500
range: 1120 1300
leg: buy call 1200 @ 43.3
leg: sell call 1250 @ 22.9
caption: Snapshot prices, used to show the shape: in practice you would price it after the results. Debit 20.4 per share (₹10,200 per lot), maximum profit 29.6 per share (₹14,800) above 1,250.
```

Other variations:
- **Calendar spreads.** When the front expiry's implied volatility is far above the next one, sell the front and buy the next. The crush hits the short leg hardest. The [volatility strategies guide](learn-fno-vol-strategies.md) shows how a calendar's value depends on both legs.
- **Buying the run-up only.** Buy a straddle several days before the event and sell it *before* the announcement. It aims at the rise in implied volatility, not the move.

## 6. Worked examples

Option prices for past dates are not stored. For those dates, premiums are **estimates**: Black-Scholes values using India VIX as the implied volatility, today's Nifty lot of 65, and the weekly expiry that followed. India VIX is a 30-day measure, so it understates the event premium real weekly options carried. Treat the rupee figures as rough.

### Example 1 — the July 2024 Budget: selling the crush (success)

```series
title: Nifty and India VIX around the Budget of 23 July 2024
from: 2024-07-01
to: 2024-08-09
tf: D
line: india:NIFTY50 | NIFTY 50
line: india:INDIAVIX | India VIX | right
mark: 2024-07-23 | Budget
caption: India VIX fell from 15.44 to 12.75 on Budget day while Nifty closed almost flat.
```

1. **Setup.** Budget on Tuesday 23 July 2024. Nifty's weekly options expired on 25 July. VIX had risen into the Budget, a sign of event premium.
2. **Entry, 22 July close.** Nifty was at 24,509.25 and VIX at 15.44. Sell the 24,500 straddle, buy the 24,800 call and 24,200 put. Estimated credit: about 202 points, or ₹13,101 per lot. Maximum loss: about ₹6,400.
3. **The event.** The Budget raised taxes on capital gains and futures and options trading. Nifty swung during the speech, then closed at 24,479.05, down 0.1%. VIX closed at 12.75.
4. **Exit, 23 July close.** The iron fly could be bought back for about 163 points. Estimated profit: about ₹2,500 per lot.

The gain was small because this estimate understates the real weekly premium. The shape is the point: no move, a falling VIX, a profit for the seller.

### Example 2 — the February 2021 Budget: the same trade fails

```series
title: Nifty and India VIX around the Budget of 1 February 2021
from: 2021-01-11
to: 2021-02-19
tf: D
line: india:NIFTY50 | NIFTY 50
line: india:INDIAVIX | India VIX | right
mark: 2021-02-01 | Budget
caption: Nifty rose 4.7% on Budget day, its largest Budget-day gain in this sample. India VIX barely moved.
```

1. **Setup.** Budget on Monday 1 February 2021, weekly expiry on 4 February. VIX was high at 25.34.
2. **Entry, 29 January close.** Nifty at 13,634.60. Sell the 13,650 straddle, buy the 14,050 call and 13,250 put. Estimated credit: about 265 points, or ₹17,212 per lot. Maximum loss: about ₹8,800.
3. **The event.** The Budget announced a big rise in public spending and no new taxes on investors. Nifty closed at 14,281.20, up 4.7%. VIX only eased to 23.32: there was little crush to collect.
4. **Exit, 1 February close.** Buying back cost about 367 points. Estimated loss: about ₹6,600 per lot.

The wings did their job. A short straddle without them would have lost about 288 points, or ₹18,700 per lot, almost three times as much. In the table of Budgets above, 3 of 10 days moved Nifty more than its one-day VIX move. A seller should expect such days.

### Example 3 — the June 2024 election: the buyer must exit on the day

```series
title: Nifty and India VIX, election results week, June 2024
from: 2024-05-20
to: 2024-06-14
tf: D
line: india:NIFTY50 | NIFTY 50
line: india:INDIAVIX | India VIX | right
mark: 2024-06-03 | straddle bought
mark: 2024-06-04 | results
mark: 2024-06-06 | expiry
caption: Nifty rose to 23,263.90 after exit polls on 3 June, fell to 21,884.50 on results day, and recovered to 22,821.40 by the 6 June expiry. India VIX closed at 18.89 the day after results.
```

1. **Setup.** Results due on Tuesday 4 June 2024, weekly expiry on 6 June. Exit polls over the weekend projected a large majority, and Nifty rallied 3.3% on 3 June.
2. **Entry, 3 June close.** Nifty at 23,263.90, VIX at 20.94. Buy the 23,250 straddle. Estimated cost: about 353 points (1.5%), or ₹22,932 per lot.
3. **The event.** The ruling party fell short of a majority on its own. Nifty closed 5.9% lower at 21,884.50. The straddle was worth about 1,358 points.
4. **Exit, 4 June close (the time rule).** Estimated profit: about ₹65,300 per lot, nearly three times the cost.
5. **If held to expiry.** Nifty recovered to 22,821.40 by 6 June. The straddle was then worth about 429 points: a profit of only about ₹4,900.

The event rule exits on the day because the move often partly reverses once the news is absorbed.

## 7. Common mistakes

- **Buying options because "something big is coming".** The market knows it too, and the price says so. The question is whether the move will exceed the straddle.
- **Holding long options past the event.** The crush removes the event premium at the next open. Without a big move, the loss is immediate.
- **Selling naked straddles into binary events.** Election and policy surprises can move an index several times its one-day implied move. Always buy wings.
- **Trading illiquid stock options around results.** Spreads widen just when you need to exit. Check the bid–ask *before* the event.
- **Counting the same event twice.** Three banks reporting on one day, plus a bank-heavy index trade, is one bet, not four.

## 8. What the evidence says

- **Implied volatility rises before scheduled announcements and falls after.** Patell and Wolfson (1979) documented this for earnings in US call options. Beber and Brandt (2006) found that implied volatility in bond options falls after macroeconomic announcements.
- **Options price earnings risk explicitly.** Dubinsky, Johannes, Kaeck and Seeger (2019) estimated the extra volatility the market attaches to each US earnings date. They found it large and varying from firm to firm.
- **The run-up can be traded.** Gao, Xing and Zhang (2018) report positive average returns for straddles held in the days *before* US earnings announcements, as implied volatility rose into them.
- **Announcement days carry a premium in stocks too.** Savor and Wilson (2013) found that US stocks earned higher average returns on days of scheduled macro announcements.
- **Our India event studies.** India VIX fell after 9 of 10 Budgets and 3 of 3 general-election results. Company results moved a typical stock about 1.7 times its normal two-session move. One result in four moved a stock more than 5%.

What is unknown: whether the implied move in Indian stock options is, on average, too high or too low. That needs years of stored option prices around results, which this guide's data does not include. The large retail option selling in India may have changed the answer in recent years. SEBI's studies found that about 9 in 10 individual F&O traders lost money in the years they covered.

## 9. Building and testing it yourself

**Data.** You need, for each event, the event date and time, and the option chain at the close before it and after it. Exchange bhavcopies give daily closes by strike and expiry. Results dates come from exchange filings; the Budget, RBI and election dates are public.

**Traps.**

- **Event timing.** A result announced at 14:00 moves the stock *that* day; one announced at 18:00 moves it the next. Use the timestamp of the filing, not just the date.
- **Moved dates.** Board meetings are rescheduled. Use the date known *before* the event, not the final one.
- **Stale prices.** Thin strikes show old last prices. Use the bid–ask mid, and require trades that day.
- **Lot sizes and expiry days changed.** India changed lot sizes and expiry weekdays several times between 2019 and 2026. Rebuild both for each date.
- **Survivorship.** Use the list of stocks with options on each date, including those later dropped.

**Costs (approximate, as of 2026).** About ₹20 per order with a discount broker, STT on the sell side of option premium, plus exchange charges, GST and stamp duty. Around results, spreads on stock options can be several times their usual width. Model the spread at the moment you would trade, not on a quiet day.

**What to test.** The thresholds for buying and selling, the number of past events in HM, and the exit time. Report trades, win rate, average win and loss, the worst trade, and results split by event type. Keep a few recent years aside and test them once at the end.

```
for each scheduled event e with date d:
    exp = first expiry after d
    im  = atm_straddle(exp, close before entry) / price
    hm  = median(|move over same sessions| for last 10 events of this kind)
    if im <= 0.85 * hm:
        buy straddle at mid of session before d          # Playbook B
    elif im >= 1.2 * hm and iv(exp) >= iv(next expiry) + 3:
        sell iron fly, wings at +/- im * price           # Playbook S
    size so that max loss <= 0.75% of equity
    close all at the close of the first session after the announcement
```

## 10. Checklist

- [ ] Is the event date and time confirmed? Before or after the market opens?
- [ ] Which expiry is the first one after the event? What is its straddle as a % of price (IM)?
- [ ] What is the median move over the same sessions for the last 8–12 events (HM)? IM ÷ HM = ?
- [ ] Does the front expiry carry a visible event premium over the next one?
- [ ] Is the bid–ask under 2% of the mid at every strike I will trade?
- [ ] Is the maximum loss within 0.5–1% of the account? Are other trades exposed to the same event?
- [ ] Do I have wings on every short option?
- [ ] Is the exit set for the first session after the event?
- [ ] For stock options: will I close before expiry to avoid delivery?

## Further reading

- James Patell and Mark Wolfson, "Anticipated Information Releases Reflected in Call Option Prices", *Journal of Accounting and Economics* (1979).
- Andrew Dubinsky, Michael Johannes, Andreas Kaeck and Norman Seeger, "Option Pricing of Earnings Announcement Risks", *Review of Financial Studies* (2019).
- Chao Gao, Yuhang Xing and Xiaoyan Zhang, "Anticipating Uncertainty: Straddles around Earnings Announcements", *Journal of Financial and Quantitative Analysis* (2018).
- Alessandro Beber and Michael Brandt, "The Effect of Macroeconomic News on Beliefs and Preferences: Evidence from the Options Market", *Journal of Monetary Economics* (2006).
- Pavel Savor and Mungo Wilson, "How Much Do Investors Care About Macroeconomic Risk? Evidence from Scheduled Economic Announcements", *Journal of Financial and Quantitative Analysis* (2013).
- Sheldon Natenberg, *Option Volatility and Pricing* (2nd edition, 2015).
- SEBI, studies on the profit and loss of individual traders in equity F&O (January 2023 and September 2024).
- Related guides: [index and news events](learn-strat-index-news-events.md), [implied and realised volatility](learn-fno-volatility.md), [directional option trades](learn-fno-directional.md), [the macro event calendar](learn-macro-calendar.md), [volatility and sentiment](learn-health-volatility.md), [volatility strategies](learn-fno-vol-strategies.md), [position sizing](learn-risk-sizing.md).
