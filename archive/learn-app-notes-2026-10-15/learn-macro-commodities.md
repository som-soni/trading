# App notes moved out of learn-macro-commodities

## Intro — "Where this shows in the app" (verbatim)

**Where this shows in the app.** The macro strip (a row of market tiles) on **Markets → Breadth**
(`scripts/swing_screener/marketdata/macro.py`) shows WTI crude, gold and
copper for the US, and Brent crude, USD/INR and gold for India. Each tile has its
1-day and 1-month change and a one-line note on *why* it matters. Sector strength — energy,
materials, metals, oil marketers — is on **Markets → Sectors**. The charts
below are drawn from the same stored price data.

## §1 Context, not signals
- "Instead, you notice that oil has trended up for months, that energy is the strongest sector on the Sectors page, and that your screens keep turning up oil stocks."

## §3 Energy stocks versus oil
- "**The reading:** decide based on the *sector's own trend* (Sectors page, the XLE chart), and use oil as the explanation."

## §5 Gold
- "The app does not store real (TIPS) yields, so it uses the ordinary 10-year yield as a stand-in." (the chart in §5 uses the nominal 10-year for this reason)
- "and the stored series peaked near **$5,300 in late January 2026**" / "The stored Indian gold series rose about 13%." (now worded without "stored")

## §6 Copper
- "For metals, use the industry groups on the Sectors page."

## §7 What a trader does
- "The Sectors page and the stocks' own charts still pick the trades."

## §8 Measurement
- "**Measurement:** the stored oil, gold and copper prices are front-month futures (the contract nearest expiry). The series switches to the next contract at each expiry and can behave oddly near expiry." (kept in general words)

## §9 Checklist
- "Oil: ... Do the energy groups on the Sectors page agree?"
