# App-specific material moved out of learn-macro-rates

## Intro — Where this shows in the app

**Where this shows in the app.** Markets → Breadth has a strip of macro tiles
for each market (built by `scripts/swing_screener/marketdata/macro.py`). The
US strip shows the 10-year and 5-year Treasury yields and the dollar. India's
shows USD/INR and Brent crude, plus the US 10-year and the dollar, because
those two drive foreign money into and out of India. Hover a tile to see *why*
it matters. Markets → Sectors is where rotations caused by rates show up first.

## §2 Policy rate vs market yields — storage name

The market rate closest to the policy rate is the **3-month Treasury bill** — a
three-month loan to the US government. Because it is so short, it simply tracks
the Fed's rate: when the Fed's rate is 5%, a 3-month bill pays about 5%. It is,
in effect, what you earn on cash, which is why the app stores it as
`CASH_YIELD` and the charts here call it the cash yield.

## §4 Growth vs value — sector rotation

**For a momentum trader:** a change in the rate trend changes *which* stocks
lead. Markets → Sectors shows the rotation. The macro picture tells you *why*,
and how long it may last.

## §7 Reading a central-bank meeting

ask: *what does the market expect?* (CME FedWatch shows it). After it, ask:
*was it more hawkish or dovish than that?* The 5-year on the macro strip gives
a quick answer. On meeting days and the session after, prices swing more

## §8 How US rates reach India

That is why the India macro strip shows the US 10-year and the dollar; see
[the currencies guide](learn-macro-currencies.md).

## §9 / §11 — sector check

- **Check that the leading sectors agree** (Markets → Sectors). If they don't,
  go with what prices are doing.
- [ ] Leadership consistent with the rate trend (Markets → Sectors)?
