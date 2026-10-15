# App notes moved out of learn-macro-currencies

## Intro — "Where this shows in the app" (verbatim)

**Where this shows in the app.** Markets → Breadth carries a macro strip: a row
of small tiles for key market series (defined in
`scripts/swing_screener/marketdata/macro.py`, `STRIP`). The US strip shows the
**Dollar index** beside yields, oil, gold, copper and credit. India's strip shows
**USD/INR**, Brent, the US 10-year, the **Dollar index** and gold. The US series
are there on purpose, because they drive foreign money into and out of India. Each tile shows the last close,
the 1-day and 1-month change, and a 3-month sparkline (a tiny line chart). Hover over a tile to see why it matters. The Fundamentals page
(Chart → Fundamentals) shows how much of each Indian company is held by FIIs and DIIs, taken from its
quarterly shareholding filings.

## §3.2 What weakens the rupee
- "That is why Brent (the main global oil price) is on the India strip."

## §4.1 Two big buyers
- "The NSE publishes provisional FII/DII figures for cash-market (ordinary share) buying and selling after each session. They are not stored in this app."

## §4.2 2022
- "A stock's FII share on the Fundamentals page tells you how exposed it is."

## §4.4 The rupee can fall while the DXY falls
- "Watch both tiles on the India strip."

## §5 Who wins and who loses
- "Check the sector's relative strength on Markets → Sectors first."

## §6 For US traders
- "**Trader's read:** if the dollar is breaking down, look at materials (XLB), energy (XLE), gold miners and non-US stocks on the Sectors page."

## §7 What a trader does with it
- "1. **Check the strip weekly** (Markets → Breadth). Look at the 1-month change and the sparkline's direction, not the single day's move."
- "4. ... (The screener already halves risk per trade when the VIX or India VIX is above its threshold.)"

## §9 Checklist
- "[ ] Brent and the US 10-year on the India strip — both rising is the rupee's worst mix"
- "[ ] India positions: FII share of holdings (Fundamentals page) — high means outflow-exposed"
- "[ ] Sector leadership on Markets → Sectors: are exporters (IT, pharma) or commodities actually outperforming, or is it only a story?"
