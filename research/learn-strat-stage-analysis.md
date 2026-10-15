# Stage analysis — buy the Stage 2 breakout, hold above the 30-week line

**In short**
- Stan Weinstein's method sorts every stock into four stages using one line: the 30-week moving average.
- Buy when a stock breaks out of a sideways base (Stage 1) into an uptrend (Stage 2): above resistance, above a rising 30-week line, on heavy volume.
- Hold while the weekly close stays above the 30-week line. Sell when the stock starts topping (Stage 3) or falling (Stage 4).
- It is a weekly, position-trading method: few decisions, holds of months to years, wide stops and small size.
- Check the market and the stock's sector first. Weinstein called it looking at the forest before the trees.

## 1. The idea

In June 2023 the drug maker Lupin had spent a year going sideways. Its 30-week average had stopped falling and turned up. In the week to 23 June, the stock closed at ₹858.2, above every weekly high of the previous six months. That week's volume was 2.4 times its recent weekly average.

The stage method said buy. The stock then stayed above its 30-week line for 19 months and closed that period near ₹2,080.

```series
title: Lupin, 2022–2025 — base, Stage 2 breakout, a long advance
from: 2022-06-01
to: 2025-03-31
tf: D
line: india:LUPIN.NS | Lupin | log
line: india:LUPIN.NS@sma150 | 150-day average (≈ 30-week line)
line: india:LUPIN.NS@vol | Volume | pane2 bars
mark: 2023-06-23 | breakout week ends
mark: 2025-01-31 | first weekly close below the line
caption: The 30-week line flattened in late 2022, turned up in early 2023 and rose until 2025.
```

Weinstein, an American market analyst, described the method in his 1988 book. He saw the same four phases in most stocks. The idea of the stages is covered in detail in [stages in a stock](learn-price-stages.md). Briefly:

| Stage | Price | 30-week line | What to do |
|---|---|---|---|
| 1 — Base | Sideways after a decline | Flattens | Watch; do not buy yet |
| 2 — Advance | Higher highs and higher lows | Rising | Buy the breakout; hold |
| 3 — Top | Sideways after an advance, wider swings | Flattens | Tighten stops or sell |
| 4 — Decline | Lower highs and lower lows | Falling | Own nothing; short only with derivatives |

Why can it work? The stages reflect slow money. A large fund that decides to own a stock buys for months, and that steady demand lifts the price above a rising average. When the fund leaves, it sells for months. A breakout from a long base also means the sellers who bought at the old highs have mostly given up.

Who is on the other side? In Stage 1 it is the tired holder who sells at break-even after a long wait. At the breakout it is the trader who sells "because it is up 10% this month". In Stage 3 it is the late buyer who arrives after the story is in the newspapers. The method aims to buy from the first, and to sell to the third.

## 2. When it works and when it doesn't

It works best at the start of a new bull market, when many stocks leave Stage 1 bases at once. Examples are India in mid-2020 and spring 2023, and the US in early 2023. It works for stocks whose business is turning: a new product cycle, a recovery in margins, a sector coming back into favour.

It works badly in a falling or sideways market. Weinstein's own rule was to check the market's stage first. A Stage 2 breakout in a Stage 4 market fails far more often. Many breakouts in January and February 2020 failed with the market in March 2020.

It also fails on news-driven stocks, where one announcement can move the price through any weekly line. Example 2 in §6 shows one.

A quick way to combine the three readings before any trade:

| Market stage | Sector stage | Stock signal | Action |
|---|---|---|---|
| 2 | 1 or 2 | Stage 2 breakout | Take the trade at full size |
| 2 | 3 or 4 | Stage 2 breakout | Skip, or half size |
| 1 or 3 | 2 | Stage 2 breakout | Half size, tighter stop |
| 4 | Any | Stage 2 breakout | Skip; wait for the market |
| Any | Any | Weekly close below a falling line | Sell; consider shorts only through derivatives |

The table is a starting point, not a tested rule. Test it as part of the market filter in §9.

**India notes.** Weekly rules suit Indian investors who cannot watch screens all day. Wide stops mean small positions, which matters with STT on every delivery sale. Many breakouts in India happen on result days, so the volume spike and the gap come together. Holds of more than 12 months move gains from short-term to long-term capital-gains tax, which is lower. Stage 4 shorting needs stock futures or options (see the Futures & options section).

**US notes.** Weinstein developed the method on US stocks and used a relative-strength line against the S&P 500. US stocks can also be shorted in Stage 4 through a margin account. That is covered in [Stage 4 shorts](learn-strat-stage4-shorts.md).

## 3. The rules

All rules use weekly bars: a week's high, low, close (Friday's close) and total volume.

### Universe and filters

- Median daily turnover of at least ₹10 crore in India or $10 million in the US, and price at least ₹50 or $5.
- At least 60 weeks of history, so the 30-week line and a 52-week range exist.
- **Market filter:** the main index (Nifty 500 or S&P 500) is itself above a 30-week line that is not falling. See [regime filters](learn-strat-regime-filters.md).
- **Sector filter:** the stock's sector or industry index is in Stage 1 or Stage 2, not Stage 4. See [sectors and groups](learn-sectors-groups.md).
- Avoid stocks with heavy **overhead supply**: a band of prices just above the breakout where many buyers from the last decline are still holding at a loss.

### Setup (the Stage 1 base)

1. The stock has moved sideways for at least 12 weeks.
2. The 30-week average has stopped falling: it is within ±1% of its value 4 weeks ago, or rising.
3. Define **resistance** as the highest weekly high of the previous 26 weeks.
4. Relative strength against the index is improving: the stock has done at least as well as the index over the last 13 weeks.

### Entry

- **Breakout week:** the weekly close is above resistance, above the 30-week average, and the 30-week average is higher than 4 weeks ago.
- **Volume:** that week's volume is at least 2 times the average weekly volume of the previous 10 weeks.
- **Order:** buy at the next session's open. Traders who watch daily can buy on the day the price clears resistance, with a buy stop just above it.
- **Investor alternative:** buy half at the breakout and half on the first pullback towards the breakout level, if it holds above the 30-week line.

### Initial stop

- A sell stop just below the higher of: the 30-week average at entry, and the last significant low within the base.
- If that is more than 15% below the entry, either skip the trade or cut the size so the loss is still your normal risk.
- Weinstein placed actual stop orders, not mental stops. Decide which you use before the test (see Example 2).

### Exits

- **Main exit:** a weekly close below the 30-week average. Sell at the next open.
- **Trailing stop:** after each correction in Stage 2, raise the stop to just below the correction's low. Never lower it.
- **Stage 3 warning:** when the 30-week line flattens (within ±1% of its value 4 weeks ago) after a long advance, move the stop up close to the price, or sell half.
- **No profit target.** The trend, not a number, ends the trade.

### Position size

- Risk 0.5% to 1% of the account per trade: shares = risk amount ÷ (entry − stop). See [position sizing](learn-risk-sizing.md).
- With stops 10% to 15% away, positions are naturally smaller. Cap each at 15% to 20% of the account.
- Hold 6 to 12 positions, spread across sectors.

### Managing the trade

- Review once a week, at the weekend. That is the method's main advantage.
- In the first weeks, a pullback towards the breakout level is normal. Act only on the stop or a weekly close below the line.
- If the stock is far above its 30-week line (say 50% or more), expect a pause. Weinstein's traders tightened stops there; investors held.
- Re-entry: after an exit, buy again only on a new Stage 2 breakout from a fresh base, or a pullback that holds the rising line.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Moving average | 30 weeks; range 20–40 (150 days on daily charts) | The stage line | Shorter lines give earlier exits and more whipsaws |
| Slope lookback | 4 weeks; range 2–8 | Whether the line counts as rising | Short lookbacks flip often near a top |
| Flat band | ±1% over 4 weeks | Stage 1 and Stage 3 detection | A judgement call; test 0.5% to 2% |
| Base length | at least 12 weeks; range 8–52 | How mature the base is | Longer bases mean fewer, stronger signals |
| Resistance window | 26 weeks; range 13–52 | Which high must be cleared | 52 weeks means a 52-week-high breakout |
| Volume multiple | 2× the 10-week average; range 1.5–3 | Breakout confirmation | Weakly predictive in the event study (§8) |
| Volume average length | 10 weeks; range 4–13 | The volume baseline | Low sensitivity |
| Relative-strength window | 13 weeks; range 13–52 | Leadership filter | Weinstein used a long-term ratio line against the index |
| Maximum stop distance | 15%; range 8%–20% | Trades skipped for being too wide | Lower values skip many good bases |
| Risk per trade | 0.5%–1% of the account | Drawdown | — |
| Position cap | 15%–20% | Gap damage | — |
| Number of positions | 6–12 | Diversification | Fewer means more single-stock risk |

## 5. Variations

- **Investor versus trader (Weinstein).** The investor buys on the first pullback after the breakout and uses a looser stop below the 30-week line. The trader buys the breakout and trails stops more tightly. Both appear in his book.
- **Mansfield relative strength.** The stock's price divided by the index, compared with its own 52-week average. Above zero and rising is the filter many Weinstein followers use. See [relative strength](learn-price-rs.md).
- **Daily version.** Use the 150-day average in place of the 30-week line and a daily close for the exit. It reacts faster but whipsaws more.
- **Minervini's Trend Template.** Mark Minervini made the Stage 2 conditions into a checklist of moving averages and distance from highs, then added tight entry patterns. See [VCP and SEPA](learn-strat-vcp-sepa.md).
- **O'Neil's base breakouts.** William O'Neil's CANSLIM buys the breakout from named base patterns with volume. It is close to a Stage 1 to Stage 2 breakout with earnings filters added. See [CANSLIM breakouts](learn-strat-canslim-breakout.md).
- **Index and sector use.** Many traders apply only the stage reading to the index and sectors, as a filter, and pick stocks by other rules.

## 6. Worked examples

Weekly figures below use the 30-week average of weekly closes. Prices are adjusted for splits and bonuses; costs are not included.

### Example 1 — Lupin, 2023–2025 (India, success)

| Step | Week ending | Detail |
|---|---|---|
| Base | Jun 2022 – May 2023 | The 30-week line fell about 5% every four weeks in mid-2022, then flattened from late 2022 |
| First move above the base | 2 Jun 2023 | Close 817.0 above the 26-week high of 800.0, but volume only 1.1 times average: no signal |
| Breakout week | 23 Jun 2023 | Close 858.2 above resistance 843.7; volume 2.4 times average; 30-week line 729.8 and rising |
| Entry | 26 Jun 2023 | Next open, about 858 |
| Initial stop | — | Just below the 30-week line, about 725: a risk of about 133 per share (15.5%) |
| Highest weekly close | 3 Jan 2025 | 2,368.9 |
| Exit signal | 31 Jan 2025 | Weekly close 2,080.4, below the 30-week line at 2,116.0 |

The trade gained about 142%, or about 9R. The stock did not close a week below the line for 19 months. The wide stop meant a smaller position: at 1% risk, the position was only about 6.5% of the account.

The first move above the base came three weeks before the signal, on ordinary volume. A trader who required volume entered about 5% higher. That is the usual price of waiting for confirmation.

### Example 2 — Adani Enterprises, 2024 (India, failure)

```series
title: Adani Enterprises, 2024 — a breakout that failed
from: 2023-11-01
to: 2025-02-28
tf: D
line: india:ADANIENT.NS | Adani Enterprises
line: india:ADANIENT.NS@sma150 | 150-day average (≈ 30-week line)
line: india:ADANIENT.NS@vol | Volume | pane2 bars
mark: 2024-05-24 | breakout week ends
mark: 2024-06-04 | election result day
mark: 2024-07-12 | weekly close below the line
caption: The breakout looked textbook. The election-day swing and a slow fade below the line ended it.
```

| Step | Date | Detail |
|---|---|---|
| Breakout week | 24 May 2024 | Close 3,384.9 above the 26-week high of 3,350.0; volume 2.4 times average; 30-week line 2,941.8 and rising |
| Initial stop | — | Just below the 30-week line, about 2,900: a risk of about 485 (14%) |
| Exit poll day | 3 Jun 2024 | Opened at 3,725.0 |
| Result day | 4 Jun 2024 | Fell from 3,520.0 to an intraday low of 2,733.9; closed 2,941.3 |
| Weekly close below the line | 12 Jul 2024 | Close 3,065.4 against a line at 3,122.7 |

Two versions of the stop gave two outcomes. A resting stop order at 2,900 was hit on 4 June, a loss of about 1R or more after slippage on a crash day. A weekly-close rule survived that day and sold after the close of 12 July, a loss of about 9%. Either way the loss was limited.

What followed shows why the exit matters. By September 2024 the 30-week line had turned down. On 21 November 2024, after news of US charges against the group's chairman, the stock closed at 2,183.6. The rule had been out for four months.

### Example 3 — Nvidia, January 2023 (US: the volume rule would have missed it)

In January 2023 Nvidia rose from about $15 to $20 in three weeks. The 30-week line turned up in the week to 27 January. No week in January to March 2023 had volume of even 1.5 times its 10-week average.

A strict 2× volume rule never fired, and the stock was above $27 by the end of March. Weinstein treated volume as strong evidence, not as an absolute requirement. Decide before testing whether your rule is strict.

## 7. Common mistakes

- **Buying Stage 1.** A stock above a flat line, inside its base, is not yet Stage 2. Bases can last years.
- **Buying late Stage 2.** A stock 60% above its 30-week line is far from any sensible stop. Wait for a new base.
- **Ignoring the market.** Most stocks follow the index. A breakout in a falling market needs a much better reason.
- **Using daily closes with a weekly method.** A Wednesday close below the line is noise for a weekly system.
- **Holding into Stage 4 out of loyalty.** A weekly close below a line that has turned down is the method's clearest sell.
- **Concentrating in one sector.** When a sector turns, its stocks break their lines together.
- **Treating the stop as negotiable.** Example 2 is the reason.

- **Reading stages off a daily chart without a rule.** "It looks like Stage 2" is not testable. Write the slope and position tests down.
- **Buying the breakout on a result day without a plan.** If the results gap is 12%, the stop below the 30-week line may be 25% away. Skip or wait for a pullback.

## 8. What the evidence says

**Published research.** Weinstein's book is a practitioner's text with chart examples, not a statistical study. The broader evidence is indirect.

Moving-average and trend rules on indices reduce drawdowns (see [moving-average trend following](learn-strat-ma-trend.md)). Stocks near their 52-week highs tend to outperform (George and Hwang, 2004). Lo, Mamaysky and Wang (2000) found that some chart patterns carry modest information, with volume sometimes adding to it. No well-known study tests Weinstein's full rule set with its market and sector filters.

**Event study: crossing above the 30-week line.** Method: weekly bars for liquid stocks, using the floors in the rules section, from 2010 to early 2026. An event is a weekly close above the 30-week average after a close at or below it the week before. Events are split by the line's 4-week slope and by volume (2× the 10-week average or not). Outcomes are price changes 26 weeks later, compared with all liquid stock-weeks.

| Group | India: events | India: median 26-week change | India: share up | US: events | US: median 26-week change | US: share up |
|---|---|---|---|---|---|---|
| All liquid weeks (baseline) | 231,832 | +2.7% | 54% | 1,104,791 | +3.6% | 57% |
| Cross, line falling, normal volume | 3,791 | 0.0% | 50% | 26,243 | +3.1% | 56% |
| Cross, line falling, 2× volume | 895 | −2.1% | 47% | 1,504 | +0.7% | 51% |
| Cross, line rising, normal volume | 3,783 | +3.1% | 55% | 22,751 | +3.9% | 58% |
| Cross, line rising, 2× volume | 634 | +1.6% | 52% | 1,197 | +2.7% | 54% |
| Rising, 2× volume, within 15% of the 52-week high | 489 | +3.2% | 53% | 969 | +3.1% | 56% |

What it shows:

1. **The slope matters.** In both markets, crosses above a rising line did better than crosses above a falling one. In India the gap was about 3 percentage points of median return.
2. **Volume alone did not help** on these simple definitions. Heavy-volume crosses had a lower median than normal-volume ones. In India their average was higher (+7.8% against +6.0%), which suggests a few big winners among them.
3. **No group beat the baseline by much.** The cross is a filter that removes the worst setups, not a predictor. The method's results depend on the exits and on the market and sector filters.

Caveats: today's stock lists (survivorship bias), overlapping 26-week windows, no costs, and no base or sector filters. Resistance breakouts were not tested separately here.

## 9. Building and testing it yourself

**Data.** Daily prices and volume aggregated to weekly bars (Friday close, weekly high and low, summed volume), adjusted for splits and bonuses. Include delisted stocks. Add a sector or industry label and index series for the market filter.

**Look-ahead traps.**

- A weekly signal is known only after Friday's close. Fill at Monday's open.
- Resistance must use weeks before the breakout week.
- The 30-week line and its slope must be computed from closes up to that week.
- Indian holiday weeks have fewer sessions; sum volume per week, do not average days.

**Costs.** India: STT of 0.1% on each side, stamp duty on the buy, exchange charges and slippage, roughly 0.3%–0.6% per round trip. Few trades make costs less important than for daily systems, but gaps on result days matter more.

**Parameters to test.**

- The line length: 20, 30 and 40 weeks.
- The slope test and the flat band.
- The volume multiple: none, 1.5× and 2×.
- The stop type: a resting order or a weekly close.
- The market filter on or off.

 Keep the stage definitions fixed while you vary one thing.

**Over-fitting.** Stage definitions involve judgement. Write them as code before looking at results, and do not adjust them after seeing which stocks they catch. See [backtesting honestly](learn-test-backtesting.md).

**What a good test reports.** Trades, win rate, average win and loss in R, and average holding time. The largest drawdown and the share of profit from the top 10 trades. Results with and without the market filter.

```
each Friday, after the close, for each stock:
    sma30 = mean(weekly_close[-30:]); rising = sma30 > sma30[-4]
    resistance = max(weekly_high[-27:-1]); vol_avg = mean(weekly_volume[-11:-1])
    if flat and market_ok and close > resistance and close > sma30 and rising
            and volume >= 2 * vol_avg:
        buy at Monday open; stop = min(sma30, base_low) * 0.99
    if long:
        if close < sma30: sell at Monday open
        else: stop = max(stop, last_correction_low * 0.99)
```

## 10. Checklist

- [ ] The market index is above a 30-week line that is not falling.
- [ ] The stock's sector is in Stage 1 or Stage 2.
- [ ] The stock has based for at least 12 weeks, and its 30-week line has stopped falling.
- [ ] The weekly close is above the 26-week high and above a rising 30-week line.
- [ ] Volume in the breakout week is at least twice the 10-week average (or I have decided not to require it).
- [ ] Relative strength against the index has improved over 13 weeks.
- [ ] No heavy overhead supply sits just above the breakout.
- [ ] The stop is below the 30-week line and the base low, no more than 15% away, and the size comes from it.
- [ ] I will review weekly and sell on a weekly close below the 30-week line.

## Further reading

- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* (McGraw-Hill, 1988).
- William J. O'Neil, *How to Make Money in Stocks* (McGraw-Hill; first edition 1988).
- Mark Minervini, *Trade Like a Stock Market Wizard* (McGraw-Hill, 2013).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Andrew Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis", *Journal of Finance* (2000).
- Related guides: [stages in a stock](learn-price-stages.md), [price and volume](learn-price-volume.md), [bases](learn-bases.md), [the index trend](learn-health-trend.md).
