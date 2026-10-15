# App-specific material moved out of learn-macro-yield-curve

## Intro — Where this shows in the app

**Where this shows in the app.** The macro strip on Markets → Breadth (built
by `scripts/swing_screener/marketdata/macro.py`) shows the US 10-year and
5-year yields. Each tile shows the change over 1 day and over 1 month, in basis
points. The India strip shows the US 10-year too. The charts below use the
yields stored in the app. "The curve" in this guide means the **10-year yield
minus the 3-month T-bill yield**.

## §2 The curve and its shape — stored series

- **The short end follows the policy rate.** A 3-month bill is a bet on where
  the Fed's rate will be over the next three months. It moves when the Fed
  moves, or when the market becomes sure the Fed will. The 2-year (not stored
  in the app) is the market's best single guess at Fed policy over the next
  two years. The **5-year**, which the app does store, looks a little further
  out.
In the history stored in the app, the 10-year peaked near 15.8% in September
1981. Its low was near 0.5% in March 2020.

## §4 Inversion — source of the record table

The record, using month-end values of the 10-year minus 3-month spread stored
in the app (approximate):

## §6 Real yields — not stored

(TIPS — bonds whose payments rise with inflation). FRED, the St. Louis Fed's
free data site, publishes it. **It is not stored in this app.** Read it on
FRED, or estimate it from the 10-year and the inflation expectations discussed
in [the inflation guide](learn-macro-inflation.md).

## §7

When it moves a full point, the price of everything set from it changes. That
is why it sits on both markets' macro strips.

## §8 rule of thumb

A working rule of thumb, not a tested rule: **a 10-year rise of half a point
or more in a month** (50bp or more on the macro strip's 1M change) is a cue to
tighten stops on high-P/E stocks.

## §9 India G-sec — not stored

India's benchmark is the **10-year government security (G-sec)**. It is not
stored in this app, so these points are text only:
The app stores no Indian yield curve. So the practical stand-in here is the
**US 10-year and USD/INR on the India macro strip**. When both are rising
fast, foreign selling in India is likely ([the currencies guide](learn-macro-currencies.md)).

## §12 Checklist

- [ ] US 10-year: level and 1-month change (macro strip) — fast or slow?
