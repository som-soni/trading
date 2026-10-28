# TODO

Ideas and follow-ups to come back to. Edit this file directly, or add an item
from the web app (Research › TODO), which appends to **Inbox**. Tick an item
with `[x]` when done; move it under **Done** when you like.

## Inbox

- [x] Add the indicator for Supply and Demand zones _(added 2026-10-18)_
- [x] Screener to find business demonstrating growth (EPS, Sales) QoQ or Recovery. (Check Minervini's book) _(added 2026-10-19)_
- [x] Strategy: Implement following strategy "Buy when price closes above the 20- or 55-day high. Sell short below the low. Size so you risk ~1% of account (use ATR for stops at 2 ATR). Exit on opposite 10- or 20-day extreme. It has decades of positive expectancy across futures including NQ, ES and gold. Win rate sits around 45%. Most of the money comes from a few big trends. Long flat periods and drawdowns are normal. The hard part is sticking to the rules when it feels wrong." _(added 2026-10-22)_
- [ ] Add stock guidance around earnings both from company and analysts (Trend) as that may indicate how the results may turn out to be. _(added 2026-10-23)_
- [x] Add a section in the learning module about analysing quarterly earnings incorporating details from the books I am reading (e.g. Minervini) _(added 2026-10-23)_
- [x] Earning analysis: We need a template to do the analysis which goes beyond basic analysis of top-line numbers but look into next level details (e.g. Minervini looks at inventory and compare it with growth) _(added 2026-10-23)_
- [x] Need similar dashboard - https://x.com/Ravindra_PE/status/2113466002159919322 _(added 2026-10-23)_
- [x] Minervini: Identify stocks which have been resilient or grown / leaders during India's bear market as they may become the leader during the bull run _(added 2026-10-23)_
- [x] Strategy (Implement): Honest answer: classic trend following via breakouts. Buy when price closes above the 20- or 55-day high. Sell short below the low. Size so you risk ~1% of account (use ATR for stops at 2 ATR). Exit on opposite 10- or 20-day extreme. It has decades of positive expectancy across futures including NQ, ES and gold. Win rate sits around 45%. Most of the money comes from a few big trends. Long flat periods and drawdowns are normal. _(added 2026-10-24)_
- [x] Add this dashboard - https://x.com/MrBsCoffee30/status/2113694563911315862 _(added 2026-10-24)_
- [ ] Identify (Coloir coded) strategies based on the edge -- Same should be there on each page where strategies is shown .. E g Today's Module _(added 2026-10-28)_

## Data

- [ ] **Data source register** — for every dataset we store, record where it
      comes from so it can be reviewed: provider and URL/API, which fields, how
      often it is refreshed and by which job, the table it lands in, and known
      caveats (e.g. Yahoo prices are not adjusted for spin-offs; NSE holidays
      appear as stray rows; Yahoo industry classification is current, not
      point-in-time). Show it on the Data status page next to each dataset's
      freshness.

## Sectors & themes

- [x] **Review the sub-industry labels** — done 25 Oct 2026: all 311 US
      suggestions accepted into data/sub_industries.csv, your 56 portal edits
      exported there, and the last 5 unassigned tradable stocks labelled. Every
      tradable stock in a split group now has a label, in both markets.
- [x] **Split the remaining large US groups** — Biotechnology is split by
      trailing revenue (rule: commercial / early commercial / clinical stage,
      `BIOTECH_*` in marketdata/subindustries.py; collaboration revenue counts, so
      check e.g. BEAM); `financials` now fetches every tradable biotech, so the
      unassigned ones fill in as it runs. Software—Application and Medical Devices
      were already split — their labels are among the suggestions above.

- [x] **Themes** — built: Sectors → Themes (5 starter drafts to review and
      write a thesis for). Named, editable baskets of stocks that share an investment
      story across industry groups (e.g. AI infrastructure; India power & grid
      capex; India railways; India defence; India capital markets). Track each
      like a group: equal-weight index, RS rating, rotation point, breadth,
      leaders; link each to a thesis (playbook §3.2). See
      `research/sector-taxonomy.md` §5 and the playbook's Phase 6.

## Done
