# App notes moved from learn-health-distribution (rewrite, 2026-10-15)

## Intro (phrase)

> It covers how often they mislead, and what the app does and does not compute.

## Where this shows in the app

**Where this shows in the app.** The app does **not** count distribution days
or flag follow-through days for an index. No job, page or strategy computes
them, and the market-regime check (`core/regime.py`) does not use index volume.
Two related pieces exist:

- The charts in these guides can draw a running count of distribution days on
  any stored series that has volume (SPY, QQQ, IWM; `^NSEI` for India). The
  chart option is called `@dist25`.
- The **Trend pullback** strategy's demand/supply note
  (`core/demand_supply.py`) counts accumulation and distribution days over 25
  sessions for each *stock*. It uses the same ±0.2%-on-higher-volume rule.
  From those counts it scores "Demand in control" / "Supply in control".

## §2 (sentences; the general point — ETF volume, no 5% rule — is kept in the guide)

> **The app's chart count and the numbers below use the volume of the ETFs that track those indices (SPY, QQQ). They also do not apply the 5% rule**: a day only drops off after 25 sessions.

## §2.2 (phrase)

> Spotting one is a judgement call, and the app does not count them.

## §6 (data notes)

> In the stored data, the Nifty 50 (`^NSEI`) has **no volume before 2013**, and a few gaps after (about a dozen zero-volume days in 2018). ... Nifty ETFs (such as NIFTYBEES) are not stored.
