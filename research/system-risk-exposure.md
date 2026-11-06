# Risk and exposure (draft)

Part of [my trading system](system-overview.md). How much to risk per trade, in total, and when to change it. The
numbers marked **to decide** are mine to set; the reference points beside them are what this repository's strategies use
and what the creators said they do.

**In short**

- Three **risk tiers** — normal, reduced, probe — chosen each day by the [daily market review](system-daily-market-review.md).
  A probe is a real trade at a tiny fraction of normal risk: being early costs almost nothing.
- **Progressive exposure**: open small, earn the right to full size with closed winners, drop back to pilot size after
  losses. It is the one sizing rule tested here, and it cut drawdown.
- Four overrides only ever reduce risk: index **stretch**, **events**, poor **recent results**, and a **hot streak**.
- Stops are set before entry, on the instrument actually traded, and **never moved against the trade**.

---

## 1. Risk tiers

| Tier | Risk per trade | When | Reference points |
|---|---|---|---|
| **Normal** | R = **to decide** | The daily-review row allows the trade and no override applies | Minervini spec strategy: 1% of equity (SL-04); [Stage 4 shorts](learn-strat-stage4-shorts.md): 0.5% per short |
| **Reduced** | ½ R | One override applies, or the "uptrend, narrowing" row | The repository's progressive-exposure pilot is ½ of the risk budget (PE-02) |
| **Probe** | ≤ 0.1 R | A setup I like on a day I don't trust — or the first trades after a correction | Luk: 0.02–0.1% of the account per attempt on a poor day for shorts |

**Why a probe tier (Luk; Minervini):** it lets me act on the setup without letting a bad tape set my loss. Luk's two stopped
probes cost about 0.05% in all; "if it worked, then that's the killer trade". Minervini's "toes in the water" after a low is
the same idea, scaled up as the first trades work.

## 2. Exposure limits

| Limit | Value | Reference points |
|---|---|---|
| Total open risk (all positions to their stops) | **to decide** | Minervini spec: under 6% of equity (PF-04) |
| Total open short risk | **to decide** | [Stage 4 shorts](learn-strat-stage4-shorts.md): about 3% |
| Maximum positions | **to decide** | Minervini spec: 8 (PF-02) |
| Position size cap | **to decide** | Minervini spec: 25% of equity (SL-05); Luk on 3 Nov 2026: each new short under 20% |
| Per group | **to decide** | Not yet in any strategy here |

## 3. Progressive exposure — size by results

**The rule as implemented here** (PE-01 to PE-04 in the Minervini spec strategy): look at the last 10 closed trades.
Trade at *pilot* size (half risk) while they are not net positive, after two losses in a row, and for the first five trades;
full risk otherwise. The state is read from trades closed *before* today — it is sizing, not prediction.

**Minervini's version (talk, 2022):** buy a few; if they work, buy more; if three of five lose and distribution appears
after a follow-through day, go back toward cash and wait.

**What it did here:** on its own it cut the US drawdown of the Minervini strategy from −43.5% to −34.6%. The market filter
did better on both return and drawdown, and the two overlap rather than add up (together: −27.6% drawdown, but a lower
return). *Status: tested.* Adopting both is a choice of smoother equity over return.

## 4. Overrides

| Override | Trigger | Effect | Source | Status |
|---|---|---|---|---|
| Stretch | The index is stretched in the trade's direction | No adds that way today | Luk | Untested |
| Event | A scheduled event can gap the next session | No full-size entries; cut into a weak close | Luk | Untested |
| Feedback | Last 10 trades net negative, or two losses in a row | Pilot size | Minervini; PE rules | Tested (above) |
| Hot streak | A strong month just ended | Raise size more slowly than equity grows | Luk ("prevent oversizing after a good period") | Untested |

Overrides combine by taking the **smallest** tier; none can raise one.

## 5. Stops

- **Set before entry; never moved against the trade.** "I'm afraid that could become a bad habit" (Luk).
- **On the instrument traded.** For a leveraged ETF, the stop is on the ETF even when the underlying would not have hit
  its own; accept the occasional mismatch (Luk).
- **The trigger timeframe sets the stop's width.** A 1- to 5-minute trigger gives a very tight stop and more stop-outs; a
  15-minute trigger gives roughly a 3–4% stop and fewer (Luk). Choose by the risk tier, not by the signal.
- **A hard ceiling on width**: skip a long whose stop is more than 8% away (Minervini spec, SL-03); skip a short whose stop
  is more than 15% away ([Stage 4 shorts](learn-strat-stage4-shorts.md)).
- **Tighter on a doubtful day** — Luk put a stop under the daily VWAP rather than above it "to limit my loss as much as
  possible" when the tape was poor.

## 6. Leverage and lifestyle

- Margin and heavy exposure overnight carry a cost beyond money: Luk stays awake for the US close (4–5 a.m. in Hong Kong) only
  when volatility is high and he carries heavy exposure, and expects to trade some performance for health with age.
- *Rule (proposed):* if I can't be there for the close — the US close is 1:30 a.m. in India in the US summer, 2:30 a.m. in
  the US winter — I size so that I don't need to be.

## 7. Decisions for me to make

1. My base risk R per trade, for longs and for shorts.
2. Total open risk and short risk caps.
3. Whether to adopt both the market filter and progressive exposure (smoother equity, lower return) or the filter alone.
4. Which session I trade with full attention — India by day, the US by night — and the size cap for the other.
