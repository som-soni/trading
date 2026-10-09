"""Sub-industries: a third level under Yahoo's industry groups, for groups that mix businesses.

    sector (11)  ->  industry group (~145, Yahoo)  ->  sub-industry

Only groups that mix businesses are split (research/sector-taxonomy.md); a coherent group (Restaurants,
Homebuilding) has no sub-industry. A stock in a split group gets its label from the first of these that
names it — and each label records its source, which the review page (Library → Sub-industries) shows:

  you          your edits in the portal (table `sub_industry_map`, source 'you'); always win
  curated      data/sub_industries.csv: market, industry, sub_industry, symbol (in git; `--export` writes
               your portal edits into it)
  rule         where a list is impractical: US regional banks by size and ADR status; US asset management
               split into managers / BDCs / crypto-treasury companies
  suggested    data/sub_industries_suggested.csv: proposed labels awaiting review (same columns)
  code         data/sub_industry_codes.csv: an official code → sub-industry, per group (market, industry,
               code, sub_industry; industry "*" = any group). Codes: marketdata/classcodes.py — BSE's
               industry for India, Nasdaq's (SIC-based) industry for the US
  bse          India: BSE's industry itself, in groups whose members span several BSE industries
  other        a stock in a split group that nothing names

A label applies only while Yahoo still files the stock under that industry (a reclassified stock falls
back rather than keeping a stale label).

This module also identifies US closed-end funds and income trusts (`us_funds`): the Nasdaq listing does not
flag them as ETFs, Yahoo files them under Asset Management, and as funds rather than companies they
distort that group, breadth and the movers lists. The `classify` job stores them in `symbol_kind`
(kind FUND), and `analytics.breadth.eligible` leaves them out everywhere.
"""

import csv
import re

from .. import paths
from . import db, industries, names

CSV_PATH = paths.DATA_DIR / "sub_industries.csv"
SUGGESTED_PATH = paths.DATA_DIR / "sub_industries_suggested.csv"
CODES_PATH = paths.DATA_DIR / "sub_industry_codes.csv"
BSE_MIXED_MIN, BSE_MIXED_TOP = 8, 0.8    # India: a group is split by BSE industry when it has 8+ coded members
                                          # and no single BSE industry holds 80% of them
SCHEMA = """
CREATE TABLE IF NOT EXISTS sub_industry_map (
    market VARCHAR(16) NOT NULL, symbol TEXT NOT NULL,
    industry TEXT NOT NULL,                 -- the Yahoo industry group the label was given under
    sub_industry TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'you',
    note TEXT, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol)
);
"""
BANK_LARGE, BANK_MID = 20e9, 2e9          # US regional banks: market cap tiers
FUND_MAX_CAP = 5e9                        # funds and trusts are small; real managers named "...Trust" are not
# a fund whatever its size
_FUND_STRONG = re.compile(r"\b(Fund|Fd|Municipal|Muni|Closed[- ]End|Term Trust|Income Trust|Opportunities Trust)\b", re.I)
# a fund only when small (a $25B "Northern Trust" is a bank, a $1B "... Trust" is a fund)
_FUND = re.compile(r"\b(Premium|Dividend|Portfolio|Trust|Investors|Securities Corp(oration)?|Total Return|"
                   r"Precious Metals Limited|Global Utility|Resources)\b|^(Nuveen|Eaton Vance|Gabelli|abrdn|PIMCO|Pimco|Calamos|"
                   r"Virtus|Western Asset|Templeton|John Hancock|Kayne|Tortoise|Cohen & Steers|Tri[- ]Continental|Clough|Allspring|"
                   r"MFS|Putnam|Neuberger|First Trust|DoubleLine|Guggenheim|Saba|Liberty All|Royce|Adams|Highland|BlackRock|Blackrock|"
                   r"Oxford Lane|Eagle Point)\b", re.I)
# real (operating) asset managers whose names would otherwise trip the fund rule
_MANAGERS = {"BLK", "BX", "KKR", "APO", "ARES", "OWL", "TROW", "BEN", "IVZ", "AMG", "CNS", "APAM", "FHI", "SEIC", "VCTR", "WT",
             "HNNA", "GROW", "BSIG", "NTRS", "STT", "AMP", "CG", "TPG", "BAM", "BN", "HLNE", "STEP", "GCMG", "PX", "VRTS", "DHIL",
             "SAMG", "WHG", "PZN", "CRBG", "EQH", "PFG", "RJF", "JHG", "MAIN", "BUR", "SII", "TPVG", "ALTI", "AAMI"}
_BDC = re.compile(r"\b(BDC|Capital Corp(oration)?|Investment Corp(oration)?|Specialty (Lending|Finance)|Secured Lending|"
                  r"Credit Company|Income Company|Finance Corp(oration)?|Lending Corp(oration)?|Capital Southwest|Main Street)\b", re.I)
_CRYPTO = re.compile(r"\b(Bitcoin|Crypto|Treasury Corp(oration)?|DeFi|Ether(eum)?|Solana|Stablecoin|Digital Asset|Strive)\b", re.I)


def _csv(market: str, path=CSV_PATH) -> dict:
    out = {}
    if path.exists():
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                if r["market"] == market:
                    out[r["symbol"].strip()] = (r["industry"].strip(), r["sub_industry"].strip())
    return out


def _adrs(market: str) -> set:
    if market != "us":
        return set()
    try:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT symbol FROM symbol_names WHERE market='us' AND is_adr")
            return {r[0] for r in cur.fetchall()}
    except Exception:  # noqa: BLE001 - column not there until the names job has run
        return set()


def us_funds(ind: dict | None = None, nm: dict | None = None) -> set:
    """US closed-end funds / income trusts filed by Yahoo as Asset Management (or with no industry)."""
    ind = ind if ind is not None else industries.load("us")
    nm = nm if nm is not None else names.load("us")
    from . import universe
    out = set()
    for s in universe.load_universe("us"):
        sec = ind.get(s)
        if s in _MANAGERS or (sec and sec[1] != "Asset Management"):
            continue
        name, cap = nm.get(s) or "", (sec[2] if sec else None) or 0
        if _CRYPTO.search(name) or (_BDC.search(name) and not _FUND_STRONG.search(name.replace("Lending Fund", ""))):
            continue
        if _FUND_STRONG.search(name) or (_FUND.search(name) and cap < FUND_MAX_CAP):
            out.add(s)
    return out


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _yours(market: str) -> dict:
    try:
        init_schema()
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT symbol, industry, sub_industry FROM sub_industry_map WHERE market=%s AND source='you'", (market,))
            return {s: (i, sub) for s, i, sub in cur.fetchall()}
    except Exception:  # noqa: BLE001 - no database: the files still apply
        return {}


def _code_map(market: str) -> dict:
    """(industry, code) -> sub-industry; industry '*' applies in any group."""
    out = {}
    if CODES_PATH.exists():
        with open(CODES_PATH, newline="") as f:
            for r in csv.DictReader(f):
                if r["market"] == market:
                    out[(r["industry"].strip(), r["code"].strip())] = r["sub_industry"].strip()
    return out


def _bse_mixed(ind: dict, codes: dict) -> set:
    """India groups whose members span several BSE industries (so BSE's industry is a useful sub-level)."""
    import collections
    by = collections.defaultdict(collections.Counter)
    for s, (sec, indus, cap) in ind.items():
        c = (codes.get(s) or {}).get("code")
        if c:
            by[indus][c] += 1
    return {g for g, c in by.items() if sum(c.values()) >= BSE_MIXED_MIN and c.most_common(1)[0][1] / sum(c.values()) < BSE_MIXED_TOP}


def load_detail(market: str) -> dict[str, tuple[str, str, str]]:
    """symbol -> (industry, sub-industry, source) for every stock in a split group (sources: module doc)."""
    from . import classcodes
    ind = industries.load(market)
    nm = names.load(market)
    yours, curated, suggested = _yours(market), _csv(market), _csv(market, SUGGESTED_PATH)
    cmap = _code_map(market)
    try:
        codes = classcodes.load(market)
    except Exception:  # noqa: BLE001 - no codes fetched yet
        codes = {}
    split = {i for i, _ in [*curated.values(), *suggested.values(), *yours.values()]} | {i for i, _ in cmap if i != "*"}
    bse_split = _bse_mixed(ind, codes) if market == "india" else set()
    split |= bse_split
    adrs = set()
    if market == "us":
        split |= {"Banks—Regional", "Asset Management"}
        adrs = _adrs(market)
    out = {}
    for s, (sec, indus, cap) in ind.items():
        if indus not in split:
            continue
        code = (codes.get(s) or {}).get("code")
        for src, table in (("you", yours), ("curated", curated)):
            hit = table.get(s)
            if hit and hit[0] == indus:
                out[s] = (indus, hit[1], src)
                break
        if s in out:
            continue
        if market == "us" and indus == "Banks—Regional":
            out[s] = (indus, "Non-US banks" if s in adrs else "Large regional banks" if (cap or 0) >= BANK_LARGE
                      else "Mid-size banks" if (cap or 0) >= BANK_MID else "Community banks", "rule")
        elif market == "us" and indus == "Asset Management" and s not in suggested:
            name = nm.get(s) or ""
            out[s] = (indus, "Crypto treasury companies" if _CRYPTO.search(name) and s not in _MANAGERS
                      else "BDCs & private credit" if _BDC.search(name) and s not in _MANAGERS else "Asset managers & alternatives", "rule")
        elif s in suggested and suggested[s][0] == indus:
            out[s] = (indus, suggested[s][1], "suggested")
        elif code and ((indus, code) in cmap or ("*", code) in cmap):
            out[s] = (indus, cmap.get((indus, code)) or cmap[("*", code)], "code")
        elif code and indus in bse_split:
            out[s] = (indus, code, "bse")
        else:
            out[s] = (indus, "other", "other")
    return out


def load(market: str) -> dict[str, tuple[str, str]]:
    """symbol -> (industry, sub-industry) for every stock in a split group."""
    return {s: (i, sub) for s, (i, sub, _src) in load_detail(market).items()}


def set_label(market: str, symbol: str, industry: str, sub: str | None) -> None:
    """Your label for a stock (None: remove yours, back to the automatic one)."""
    init_schema()
    with db.get_connection().cursor() as cur:
        if sub:
            cur.execute("""INSERT INTO sub_industry_map (market, symbol, industry, sub_industry, source) VALUES (%s,%s,%s,%s,'you')
                           ON CONFLICT (market, symbol) DO UPDATE SET industry=EXCLUDED.industry, sub_industry=EXCLUDED.sub_industry,
                           source='you', updated_at=now()""", (market, symbol, industry, sub.strip()))
        else:
            cur.execute("DELETE FROM sub_industry_map WHERE market=%s AND symbol=%s", (market, symbol))


def export() -> int:
    """Write your portal labels into data/sub_industries.csv (curated, in git) and clear them from the table."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT market, industry, sub_industry, symbol FROM sub_industry_map WHERE source='you'")
        mine = cur.fetchall()
    rows = {}
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="") as f:
            for r in csv.DictReader(f):
                rows[(r["market"], r["symbol"])] = (r["market"], r["industry"], r["sub_industry"], r["symbol"])
    for m, i, sub, s in mine:
        rows[(m, s)] = (m, i, sub, s)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["market", "industry", "sub_industry", "symbol"])
        w.writerows(sorted(rows.values()))
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM sub_industry_map WHERE source='you'")
    return len(mine)


def label(industry: str, sub: str) -> str:
    """Display / group key: 'Semiconductors › AI & compute'."""
    return f"{industry} › {sub}"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="sub-industries")
    ap.add_argument("--export", action="store_true", help="write your portal labels into data/sub_industries.csv")
    a = ap.parse_args()
    if a.export:
        print(f"{export()} labels written to {CSV_PATH}")
