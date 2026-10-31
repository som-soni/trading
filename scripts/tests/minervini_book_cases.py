"""Minervini's own chart examples: the permanent eval set for the `minervini` strategy.

Each case is one figure from his books, pinned to dates on stored prices. Run it with
`PYTHONPATH=. .venv/bin/python -m tests.test_vcp_book_examples`.

Books (`book`):
- "TLSMW": *Trade Like a Stock Market Wizard* (2013), chapter 10 — the original seven pinned VCPs.
- "TTLC": *Think & Trade Like a Champion* (2017), from the owner's screenshots — figure numbers as printed.

Kinds (`kind`):
- "buy": the book marks (or, `source="implied"`, clearly shows) a buy point. The strategy should give
  a buy setup (`setups`) on some session in `window`.
- "no_buy": the book shows a setup to avoid (a faulty or late-stage base). The strategy should give
  no buy setup in `window`.
- "sell": a climax or exhaustion top. Recorded for the exit rules; not scored yet.

`pinned=True` cases are asserted: a miss fails the test. The rest are scored and printed, so a change
that catches one shows as an improvement; pin a case once it is caught on purpose. `why` records why
the current rules miss a case, once that is known.

A case whose symbol has no stored prices is listed, never scored (delisted names the data does not
carry yet). Dates are read off the book's chart and then matched to the stored bars; prices in the
store are split-adjusted, so they differ from the book's axis.

Notes are in our own words: what the figure shows, never the book's text.
"""

BUY = ("S1", "S3", "S4", "S5", "S6", "S7")   # a buy: breakout, low cheat, cheat/3-C, power play, flat base, near miss

CASES = [
    # --- Trade Like a Stock Market Wizard, chapter 10 (pinned since 1.27–1.30) ---------------------------
    dict(id="tlsmw-10.31-nflx", book="TLSMW", fig="10.31", symbol="NFLX", kind="buy", source="marked",
         window=("2009-10-15", "2009-10-15"), setups=("S1",), pinned=True,
         note="out of a 27-week base, footprint 27W 27/7 3T; also TTLC 1-4, 6-7, 7-5"),
    dict(id="tlsmw-10.40-lulu", book="TLSMW", fig="10.40", symbol="LULU", kind="buy", source="marked",
         window=("2010-11-05", "2010-11-05"), setups=("S1",), pinned=True,
         note="bought as it emerged from a double bottom; also TTLC 1-5"),
    dict(id="tlsmw-10.34-crus", book="TLSMW", fig="10.34", symbol="CRUS", kind="buy", source="marked",
         window=("2010-03-29", "2010-03-29"), setups=("S2",), pinned=True,
         note="coiled the day before the 30 Mar 2010 buy at $8.09"),
    dict(id="tlsmw-10.62-bby", book="TLSMW", fig="10.62", symbol="BBY", kind="buy", source="marked",
         window=("1997-12-01", "1997-12-01"), setups=("S1",), pinned=True,
         note="lowest volume the day before the breakout"),
    dict(id="tlsmw-10.44-syk", book="TLSMW", fig="10.44", symbol="SYK", kind="buy", source="marked",
         window=("1995-01-05", "1995-01-05"), setups=("S1",), pinned=True,
         note="bought as it emerged from a VCP in January 1995"),
    dict(id="tlsmw-10.32-edu", book="TLSMW", fig="10.32", symbol="EDU", kind="buy", source="marked",
         window=("2007-04-16", "2007-04-16"), setups=("S1",), pinned=True,
         note="footprint 8W 22/2 3T, seven months after listing"),
    dict(id="tlsmw-10.64-dks", book="TLSMW", fig="10.64", symbol="DKS", kind="buy", source="marked",
         window=("2003-03-31", "2003-03-31"), setups=("S2",), pinned=True,
         note="coiled the day before the 1 Apr 2003 buy, six months after listing"),
    dict(id="tlsmw-10.15-mga", book="TLSMW", fig="10.15", symbol="MGA", kind="buy", source="marked",
         window=("2010-12-27", "2011-01-07"), setups=BUY, pinned=False,
         note="the 'correct buy point' after a compressed right side",
         why="VCP-06: the final contraction is 0.71x the one before (3.9% after 5.5%), over the 0.6 limit"),
    dict(id="tlsmw-10.29-amsc", book="TLSMW", fig="10.29", symbol="AMSC", kind="buy", source="marked",
         window=("2003-12-22", "2004-01-06"), setups=BUY, pinned=False,
         note="a classic VCP, up 60% in 17 days",
         why="the right side rallied 71% of the way back before its handle, under the 75% that starts a "
             "new contraction (t_recovery); counted, the handle is 15% deep, over VCP-08's 10%"),
    dict(id="tlsmw-10.60-axon", book="TLSMW", fig="10.60", symbol="AXON", kind="buy", source="marked",
         window=("2004-01-05", "2004-01-14"), setups=BUY, pinned=False,
         note="TASR's power play (the ticker is now AXON)",
         why="MV-05 is detected, but the breakout closed 5.6% above the pivot, over BUY_RANGE_PCT; he "
             "buys intraday as it crosses the pivot"),
    dict(id="tlsmw-10.28-meli", book="TLSMW", fig="10.28/10.55", symbol="MELI", kind="buy", source="marked",
         window=("2007-11-26", "2007-12-10"), setups=BUY, pinned=False,
         note="a base reset after the IPO; also TTLC 6-10 (bought just before +75% in 13 days)",
         why="the October 2007 primary base came under YOUNG_MIN_BARS sessions after listing; the "
             "December reset's final contraction is 0.72x the reference, over the 0.6 limit"),

    # --- Think & Trade Like a Champion: buy points --------------------------------------------------
    dict(id="ttlc-10.1-body", book="TTLC", fig="10-1", symbol="BODY", kind="buy", source="marked",
         window=("2010-12-01", "2010-12-31"), setups=BUY, pinned=False,
         note="first VCP after its October 2010 IPO, bought risking 5%; +40% in six days"),
    dict(id="ttlc-9.15-gra", book="TTLC", fig="9-15", symbol="GRA", kind="buy", source="marked",
         window=("2004-07-19", "2004-08-13"), setups=BUY, pinned=False,
         note="buy point out of a classic VCP in summer 2004; +147% in 55 days"),
    dict(id="ttlc-9.16-amgn", book="TTLC", fig="9-16", symbol="AMGN", kind="buy", source="marked",
         window=("1990-11-01", "1990-11-30"), setups=BUY, pinned=False,
         note="classic VCP through Sep–Oct 1990 (the 1990 bear-market low), breakout over ~2.10 adj. on "
              "12–14 Nov on 1.0–1.6x volume; +360% in 26 months"),
    dict(id="ttlc-9.14-luv", book="TTLC", fig="9-14", symbol="LUV", kind="buy", source="implied",
         window=("2013-09-16", "2013-10-31"), setups=BUY, pinned=False,
         note="break-away move from an early-stage base (Mar–Sep 2013, ~12.6–14.5 adj.)"),
    dict(id="ttlc-9.1-deck-b1", book="TTLC", fig="9-1", symbol="DECK", kind="buy", source="implied",
         window=("2006-09-01", "2006-10-31"), setups=BUY, pinned=False,
         note="base 1 of four in the 2006–2007 stage 2 (Apr–Sep 2006)"),
    dict(id="ttlc-9.1-deck-b2", book="TTLC", fig="9-1", symbol="DECK", kind="buy", source="implied",
         window=("2007-02-01", "2007-02-28"), setups=BUY, pinned=False,
         note="base 2 (Dec 2006–Jan 2007)"),
    dict(id="ttlc-9.1-deck-b3", book="TTLC", fig="9-1", symbol="DECK", kind="buy", source="implied",
         window=("2007-04-15", "2007-05-31"), setups=BUY, pinned=False,
         note="base 3 (Mar–Apr 2007)"),
    dict(id="ttlc-9.1-deck-b4", book="TTLC", fig="9-1", symbol="DECK", kind="buy", source="implied",
         window=("2007-09-15", "2007-10-31"), setups=BUY, pinned=False,
         note="base 4 (Jul–Sep 2007)"),
    dict(id="ttlc-9.9-gmcr", book="TTLC", fig="9-9", symbol="GMCR", kind="buy", source="implied",
         window=("2006-12-01", "2007-07-31"), setups=BUY, pinned=False,
         note="bases 1–4 through its 2007 stage 2, before the August climax"),
    dict(id="ttlc-7.20-pcyc", book="TTLC", fig="7-20", symbol="PCYC", kind="buy", source="marked",
         window=("2010-02-01", "2010-02-12"), setups=BUY, pinned=False,
         note="bought 4 Feb 2010 out of a tight box, the day the Nasdaq made a new low; +90% in 48 sessions"),
    dict(id="ttlc-7.18-hd", book="TTLC", fig="7-18", symbol="HD", kind="buy", source="marked",
         window=("1990-12-01", "1991-01-31"), setups=BUY, pinned=False,
         note="cup with handle after the 1990 bear-market low; RS line led the price into new highs"),
    dict(id="ttlc-7.17-msft-3c", book="TTLC", fig="7-17", symbol="MSFT", kind="buy", source="marked",
         window=("1990-11-05", "1990-12-07"), setups=BUY, pinned=False,
         note="3-C buy point on the right side of the 1990 base"),
    dict(id="ttlc-7.17-msft-handle", book="TTLC", fig="7-17", symbol="MSFT", kind="buy", source="marked",
         window=("1991-01-02", "1991-01-25"), setups=BUY, pinned=False,
         note="handle buy point, January 1991 (Dec 1990 high ~1.07 adj., cleared on 1.6x volume)"),
    dict(id="ttlc-7.16-aapl", book="TTLC", fig="7-16", symbol="AAPL", kind="buy", source="marked",
         window=("2004-08-20", "2004-09-03"), setups=BUY, pinned=False,
         note="low cheat after a gap up on huge volume and a quiet pullback that filled the gap; "
              "cleared 24–26 Aug 2004 (2.3x on the 26th); the '3rd buy' of TTLC 7-9"),
    dict(id="ttlc-7.15-twtr", book="TTLC", fig="7-15", symbol="TWTR", kind="buy", source="marked",
         window=("2013-12-02", "2013-12-13"), setups=BUY, pinned=False,
         note="low cheat a month after the November 2013 IPO"),
    dict(id="ttlc-7.14-goog", book="TTLC", fig="7-14", symbol="GOOG", kind="buy", source="marked",
         window=("2004-09-07", "2004-09-15"), setups=BUY, pinned=False,
         note="low cheat three weeks after the August 2004 IPO, no handle; cleared 10 Sep; also TTLC 1-8"),
    dict(id="ttlc-7.13-maxy", book="TTLC", fig="7-13", symbol="MAXY", kind="buy", source="marked",
         window=("2000-02-07", "2000-02-25"), setups=BUY, pinned=False,
         note="3-C two months after the December 1999 IPO; +100% in 14 days"),

    dict(id="ttlc-7.12-jblu", book="TTLC", fig="7-12", symbol="JBLU", kind="buy", source="marked",
         window=("2014-10-27", "2014-11-14"), setups=BUY, pinned=False,
         note="3-C (point D) after an A-B-C pullback to the 200-day; +130% in 11 months"),
    dict(id="ttlc-7.11-crus", book="TTLC", fig="7-11", symbol="CRUS", kind="buy", source="marked",
         window=("2010-03-01", "2010-03-12"), setups=BUY, pinned=False,
         note="classic 3-C: a tight shelf (C) in the cup's right side, cleared at D in early March 2010"),
    dict(id="ttlc-7.10-hum", book="TTLC", fig="7-10", symbol="HUM", kind="buy", source="marked",
         window=("1978-03-15", "1978-04-30"), setups=BUY, pinned=False,
         note="3-C days after the Dow's 1978 bear-market low, above a rising 200-day while the market was "
              "below a falling one"),
    dict(id="ttlc-7.9-aapl-1", book="TTLC", fig="7-9", symbol="AAPL", kind="buy", source="marked",
         window=("2004-03-01", "2004-03-12"), setups=BUY, pinned=False,
         note="first buy, out of the base from Oct 2003, while the Nasdaq was topping"),
    dict(id="ttlc-7.9-aapl-2", book="TTLC", fig="7-9", symbol="AAPL", kind="buy", source="marked",
         window=("2004-06-01", "2004-06-18"), setups=BUY, pinned=False,
         note="follow-up buy out of the April–May 2004 pullback"),
    dict(id="ttlc-7.8-wmt-1", book="TTLC", fig="7-8", symbol="WMT", kind="buy", source="marked",
         window=("1981-09-21", "1981-10-16"), setups=BUY, pinned=False,
         note="buy point during the 1981–82 bear market, above a rising 200-day"),
    dict(id="ttlc-7.8-wmt-2", book="TTLC", fig="7-8", symbol="WMT", kind="buy", source="marked",
         window=("1982-03-22", "1982-04-16"), setups=BUY, pinned=False,
         note="second buy point, before the August 1982 market bottom"),
    dict(id="ttlc-7.4-ebay", book="TTLC", fig="7-4", symbol="EBAY", kind="buy", source="marked",
         window=("2003-01-02", "2003-01-24"), setups=BUY, pinned=False,
         note="emerged from a 7-week base after the 2002 market low; RS line rising"),
    dict(id="ttlc-7.3-amzn", book="TTLC", fig="7-3", symbol="AMZN", kind="buy", source="marked",
         window=("2002-10-08", "2002-10-18"), setups=BUY, pinned=False,
         note="3-C out of a 22-week base on 10 Oct 2002, the day the market bottomed"),
    dict(id="ttlc-6.8-vivo", book="TTLC", fig="6-8", symbol="VIVO", kind="buy", source="marked",
         window=("2007-01-02", "2007-01-26"), setups=BUY, pinned=False,
         note="textbook 4T VCP, 31/17/8/3 (Meridian Bioscience; stored VIVO history starts 2015)"),
    dict(id="ttlc-6.5-bita", book="TTLC", fig="6-5/1-7", symbol="BITA", kind="buy", source="marked",
         window=("2013-09-23", "2013-10-04"), setups=BUY, pinned=False,
         note="classic VCP 28/16/6, then up 4 of 5 days"),
    dict(id="ttlc-5.8-imgn", book="TTLC", fig="5-8", symbol="IMGN", kind="buy", source="marked",
         window=("2015-06-22", "2015-07-10"), setups=BUY, pinned=False,
         note="buy point after a gap; +30% then fully retraced (an exit lesson)"),
    dict(id="ttlc-3.4-gpre", book="TTLC", fig="3-4/1-3", symbol="GPRE", kind="buy", source="marked",
         window=("2013-12-16", "2013-12-27"), setups=BUY, pinned=False,
         note="emerged from a base in Dec 2013, a 9-day natural reaction, then new highs on volume"),
    dict(id="ttlc-3.3-ions", book="TTLC", fig="3-3", symbol="IONS", kind="buy", source="marked",
         window=("2013-12-16", "2014-01-10"), setups=BUY, pinned=False,
         note="ISIS (now IONS): buy point, then a 6.1% pullback that a 6% stop would not survive"),
    dict(id="ttlc-2.1-mdvn", book="TTLC", fig="2-1", symbol="MDVN", kind="buy", source="marked",
         window=("2012-01-17", "2012-02-03"), setups=BUY, pinned=False,
         note="broke out of a tight range, pulled back near the breakout, bought on the way back up"),
    dict(id="ttlc-1.13-mu", book="TTLC", fig="1-13", symbol="MU", kind="buy", source="marked",
         window=("2013-11-11", "2013-11-22"), setups=BUY, pinned=False,
         note="3-C breakout that squatted, then a 2-day reversal recovery"),
    dict(id="ttlc-1.12-bdsi", book="TTLC", fig="1-12", symbol="BDSI", kind="buy", source="marked",
         window=("2014-06-02", "2014-06-20"), setups=BUY, pinned=False,
         note="cup with handle; the breakout day squatted, then a 2-day reversal recovery"),
    dict(id="ttlc-1.6-zg", book="TTLC", fig="1-6", symbol="ZG", kind="buy", source="marked",
         window=("2013-07-01", "2013-07-19"), setups=BUY, pinned=False,
         note="Zillow (then Z, stored as ZG) broke out of a base, up 7 of 8 days"),
    dict(id="ttlc-1.2-yelp", book="TTLC", fig="1-2", symbol="YELP", kind="buy", source="marked",
         window=("2013-08-30", "2013-09-10"), setups=BUY, pinned=False,
         note="emerged from a 5-week base with several days of follow-through on rising volume"),

    # --- Think & Trade Like a Champion: setups to avoid ---------------------------------------------
    dict(id="ttlc-9.12-ll", book="TTLC", fig="9-12", symbol="LL", kind="no_buy", source="marked",
         window=("2013-11-01", "2013-12-13"), setups=BUY, pinned=False,
         note="faulty late-stage base; a low-volume breakout attempt in Nov 2013, then the largest drop on heavy "
              "volume through the 20- and 50-day (also TTLC 1-11)"),
    dict(id="ttlc-9.1-deck-b5", book="TTLC", fig="9-1", symbol="DECK", kind="no_buy", source="implied",
         window=("2008-01-01", "2008-07-31"), setups=BUY, pinned=False,
         note="base 5 is a stage-3 top before the 2008 stage-4 decline"),

    dict(id="ttlc-7.1-gpro", book="TTLC", fig="7-1", symbol="GPRO", kind="no_buy", source="marked",
         window=("2015-07-01", "2015-09-15"), setups=BUY, pinned=False,
         note="faulty base in a decline that was never a stage 2 (from above 98 to under 9)"),
    dict(id="ttlc-6.4-kors", book="TTLC", fig="6-4", symbol="CPRI", kind="no_buy", source="marked",
         window=("2014-08-01", "2015-07-31"), setups=BUY, pinned=False,
         note="KORS (now CPRI) in stage 4 under its 200-day, a serial gapper from 85 to under 35"),
    dict(id="ttlc-6.3-vrx", book="TTLC", fig="6-3", symbol="BHC", kind="no_buy", source="marked",
         window=("2015-10-01", "2016-12-30"), setups=BUY, pinned=False,
         note="VRX (now BHC) below its 200-day, down more than 90%"),
    dict(id="ttlc-1.10-outr", book="TTLC", fig="1-10", symbol="OUTR", kind="no_buy", source="marked",
         window=("2014-02-24", "2014-03-14"), setups=BUY, pinned=False,
         note="low volume out, high volume back in: a breakout that failed at once"),
    dict(id="ttlc-1.9-wage", book="TTLC", fig="1-9", symbol="WAGE", kind="no_buy", source="marked",
         window=("2014-02-24", "2014-03-14"), setups=BUY, pinned=False,
         note="low-volume breakout, then three lower lows on rising volume and a close under the 20-day"),

    # --- Think & Trade Like a Champion: climax and exhaustion tops (exit rules; not scored yet) -----
    dict(id="ttlc-9.14-luv-top", book="TTLC", fig="9-14", symbol="LUV", kind="sell", source="marked",
         window=("2014-09-01", "2014-10-31"), note="exhaustion move from a late-stage (fifth) base"),
    dict(id="ttlc-9.11-drys", book="TTLC", fig="9-11", symbol="DRYS", kind="sell", source="marked",
         window=("2007-10-01", "2007-11-21"), note="classic climax signals, then a 99.8% decline"),
    dict(id="ttlc-9.10-biib", book="TTLC", fig="9-10", symbol="BIIB", kind="sell", source="marked",
         window=("2011-04-25", "2011-05-13"), note="+50% in 9 days on gaps, reversal on the largest volume"),
    dict(id="ttlc-9.9-gmcr-top", book="TTLC", fig="9-9", symbol="GMCR", kind="sell", source="marked",
         window=("2007-07-30", "2007-08-13"), note="+60% in 4 days out of base 4, largest up day, widest spread"),
    dict(id="ttlc-9.8-mnst", book="TTLC", fig="9-8", symbol="MNST", kind="sell", source="marked",
         window=("2006-04-24", "2006-05-12"), note="up 10 of 11 days, then gaps; +58% in 8 days"),
    dict(id="ttlc-9.7-tsla", book="TTLC", fig="9-7", symbol="TSLA", kind="sell", source="marked",
         window=("2014-02-10", "2014-03-05"), note="doubled in 30 days, +51% in the last 14 on three gaps"),
    dict(id="ttlc-9.6-amzn", book="TTLC", fig="9-6", symbol="AMZN", kind="sell", source="marked",
         window=("1999-01-04", "1999-01-12"), note="+97% in six days, 6 of 6 up, then a 95% decline"),
    dict(id="ttlc-9.5-qcom", book="TTLC", fig="9-5", symbol="QCOM", kind="sell", source="marked",
         window=("1999-12-20", "1999-12-31"), note="climax top: +73% in six days after +80% in nine"),
]
