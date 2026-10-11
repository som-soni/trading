"""The day-to-day screener: the loose pre-filter, the single-market
pipeline, the both-markets daily wrapper, report columns, run history and the
single-stock inspector.

Retired here: `trend_template.py` (removed 2026-10-11, recoverable from git).
It ran Minervini's eight-criterion Stage 2 qualifier over a whole market, which
is now the `stage2` screen (`screens/__init__.py`, criteria C1-C8). The two were
measured to qualify identical sets — 497 US and 290 India stocks on the stored
snapshot — so it was a second implementation of one filter, with its own copies
of the thresholds and, worse, the same C1-C8 code names for different rules (its
C1 was "above the 150- and 200-day" where the screen's is "above the 50-day"; its
C3 was "the 200-day is rising" where the screen's is "close above the 200-day"),
so a criterion code alone did not say which rule had failed. It also downloaded
prices from inside `screening/`, which belongs to `marketdata/`.

Its reason for existing no longer held. Criterion 8 is a cross-sectional ranking,
which a per-symbol strategy cannot see and must approximate, so a market-wide
screener computed it properly; the daily snapshot now carries a true 1-99
`rs_rank` and the `stage2` screen compares against it directly.

One thing went with it and has no replacement: `sma200_rising_4_5mo`, Minervini's
"4-5 months preferred" flag on criterion 3 (the screen's C5 only requires the
21-session minimum). Add it as a snapshot field if it is wanted back.
"""
