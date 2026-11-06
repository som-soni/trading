"""Company guidance from US earnings press releases (the 8-K's exhibit 99, filed with item 2.02).

What a company says it expects for the coming quarter and year is the other half of the earnings
picture next to the analysts' consensus (marketdata/estimates.py): a report is judged against both,
and a company that raises its own outlook is telling you more than any analyst can.

No free source carries guidance as numbers, so it is read from the press release itself, by rules:

  1. the release: each 8-K filed with item 2.02 (results of operations), its EX-99 exhibit, found by the
     filing index's document type — not by file name, which every company spells differently;
  2. the outlook section: the first "Outlook" / "Guidance" heading whose next few hundred characters say
     what the company expects, up to the next section (conference call, forward-looking statements ...);
  3. the statements: the section split into bullets and sentences. A lead-in ("For the first quarter of
     fiscal 2027, the company expects:") sets the period for the bullets after it;
  4. the figures: per statement, the metric (revenue, EPS, gross / operating margin), its basis (GAAP,
     non-GAAP / adjusted), its period (a quarter or a fiscal year) and its value — a range ("$935 million
     to $939 million", "between $1.83 and $1.91"), a point with a tolerance ("$108.0 billion, plus or
     minus 2%", "$61.5 billion ± $1.5 billion"), a point ("approximately $34.8 billion"), or a growth range
     ("grow between 30% and 34%"). A statement with none of these (Nike's "decline high-single digits") is
     kept as text only.

The rules read most releases (bullets under an Outlook heading; Micron's table reads the same once
flattened), but not all: some companies give guidance only on the call (Microsoft), some none (Apple),
and wording outside these patterns is missed or, rarely, misread. So every statement is stored as written
and the page shows it beside the figures, with the link to the release.

Tables:
  guidance_releases   one row per results press release read: filing date, accession, exhibit URL, the
                      outlook section's text (empty when none was found), and what the parser made of it
  guidance_items      one row per statement in the outlook section: metric, basis, period, value, text

    PYTHONPATH=. python3 -m swing_screener.marketdata.guidance --market us --symbols CRM,NVDA
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import re
import time

import requests

from ..config import MARKETS
from . import db

logger = logging.getLogger("guidance")

RELEASES_BACK = 6        # results releases read per company on its first fetch (about eighteen months)
MAX_AGE_DAYS = 6         # a company checked more recently than this is skipped unless forced
SEC_PAUSE = 0.15         # SEC asks for at most 10 requests a second
SECTION_LOOKAHEAD = 400  # an Outlook heading counts when "expect" (or similar) follows within this many characters
SECTION_MAX = 5000       # characters read after the heading at most
QUARTER_MATCH_DAYS = 20  # a guided quarter and a reported / estimated quarter are the same within this many days
PARSER_VERSION = 3       # bump when the rules change: releases read by an older version are re-read

SCHEMA = """
CREATE TABLE IF NOT EXISTS guidance_releases (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    accession VARCHAR(32) NOT NULL,
    filed DATE NOT NULL,
    url TEXT,
    section TEXT,                           -- the outlook section as read ('' when none was found)
    items INT NOT NULL DEFAULT 0,           -- statements read, and how many carried a figure
    figures INT NOT NULL DEFAULT 0,
    parser INT NOT NULL DEFAULT 1,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, accession)
);
CREATE TABLE IF NOT EXISTS guidance_items (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    accession VARCHAR(32) NOT NULL,
    idx INT NOT NULL,                       -- order in the section
    metric VARCHAR(24),                     -- revenue | eps | gross_margin | operating_margin | operating_income | net_income |
                                            -- comparable_sales | NULL (a forward-looking statement with no figure read)
    metric_label TEXT,                      -- the phrase as written: "Total Cloud revenue", "non-GAAP net income per share"
    basis VARCHAR(12),                      -- gaap | non_gaap | both | NULL (not stated)
    period_kind VARCHAR(2),                 -- Q | FY | NULL
    fiscal_year INT,
    fiscal_quarter INT,
    period_label TEXT,                      -- as written: "first quarter of fiscal 2027"
    unit VARCHAR(12),                       -- money | pct (a margin) | growth (a % change) | NULL
    low DOUBLE PRECISION,
    high DOUBLE PRECISION,
    text TEXT NOT NULL,
    PRIMARY KEY (market, symbol, accession, idx)
);
CREATE TABLE IF NOT EXISTS guidance_status (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    note TEXT,
    PRIMARY KEY (market, symbol)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


# ------------------------------------------------------------------ parsing (pure: text in, statements out)

_KEY = re.compile(r"(?i)\b(outlook|guidance)(?:\b|(?=\d))")   # "Guidance3": a footnote mark glued on
_FORWARD = re.compile(r"(?i)\b(expects?|expected|expectations?|forecasts?|forecasted|anticipates?|anticipated|projects?|projected|"
                      r"guidance|outlook|providing|plans? to|will be|to be in|in (?:a|the) range|approximately|plus or minus|"
                      r"at least|now sees|sees)\b|±")
_STRONG_FWD = re.compile(r"(?i)\b(expects?|expected|forecasts?|forecasted|anticipat\w*|guidance|outlook|projected|plans? to|will be|sees)\b")
_PAST = re.compile(r"(?i)\b(was|were|grew|reported|delivered|generated|ended|included|expanded|contracted|rose|fell|"
                   r"compared (?:with|to) the prior|increased to|decreased to)\b")
_BOILERPLATE = re.compile(r"(?i)\((?:nyse|nasdaq)[^)]*\)|\bannual revenues? of\b|\bemployees\b|\b(?:net )?impact of\b|"
                          r"forward[- ]looking statements|webcast|conference call|replay|press release contains|"
                          r"\d(?:\.\d+)?\s+(?:percentage\s+)?(?:points?|pts)\b")   # an impact in points, not a figure
_STOP = re.compile(r"(?i)^(?:conference call|webcast|earnings (?:conference )?call|about [A-Z]|forward[- ]looking statements|"
                   r"cautionary|safe harbor|non-gaap financial measures|(?:use|reconciliation) of non-gaap|investor (?:presentation|relations)|"
                   r"supplemental|condensed consolidated|media contacts?|contacts?:|source:|recent (?:business )?highlights|"
                   r"(?:first|second|third|fourth) quarter (?:\w+ )?(?:highlights|results|summary)|segment results|financial results)")
_NO_GUIDE = re.compile(r"(?i)(will provide (?:forward-looking )?guidance (?:on|in connection with|during)|"
                       r"does not provide|not providing (?:financial )?guidance|no longer provides?)")
_INLINE_HEADING = re.compile(r"^(?:[A-Z][\w&]*\s+){0,4}(?:Outlook|Guidance)\d?\s+(?=[A-Z])")
_HEADING_SKIP = re.compile(r"(?i)^(?:\d{1,2}\s+|[•●◦▪*]|\(\d\))|\b(reports?|reported|raises?|reaffirms?|lowers?|updates?|announces?|increases?)\b")


def _text(html: str) -> str:
    """A release's text, one line per paragraph, list item or table row (a row's cells joined by ' | ')."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    for tr in soup.find_all("tr"):
        cells = [re.sub(r"\s+", " ", c.get_text(" ")).strip() for c in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c and c not in ("$", "%", ")")]
        tr.replace_with(soup.new_string("\n" + " | ".join(cells) + "\n"))
    for el in soup.find_all(["br", "p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
        el.append("\n")
    t = soup.get_text("").replace("\xa0", " ").replace("​", "")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\s*\n\s*", "\n", t).strip()


def outlook_section(text: str) -> str:
    """The outlook section of a release's text (lines joined by newlines), or '' when it gives no guidance.

    The section starts at a heading line — short, naming Outlook or Guidance, not a headline ("Raises ...
    Outlook") or footnote — whose next lines say what the company expects and carry a figure; it ends at
    the next section (conference call, forward-looking statements, highlights ...) or SECTION_MAX."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        # a heading on its own line, or run into the section's first sentence ("Outlook For the third quarter ...")
        inline = _INLINE_HEADING.match(line) if len(line) > 90 else None
        if (len(line) > 90 and not inline) or not _KEY.search(line[:90]) or _HEADING_SKIP.search(line.strip()[:90]):
            continue
        ahead = ((line[inline.end():] + " ") if inline else "") + " ".join(lines[i + 1:i + 4])
        ahead = ahead[:SECTION_LOOKAHEAD]
        if _NO_GUIDE.search(ahead):
            return ""
        if not _FORWARD.search(ahead) or re.search(r"(?i)\breported\b", ahead[:200]):
            continue
        body, size = [line], len(line)
        for nxt in lines[i + 1:]:
            if _STOP.search(nxt.strip()) or size > SECTION_MAX:
                break
            body.append(nxt)
            size += len(nxt) + 1
        section = "\n".join(body)
        if re.search(r"\$\s?\d|\d\s?%|\d\s*percent", section):
            return section.strip()
    return ""


_WORDS_Q = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_PERIOD = re.compile(
    r"(?i)\b(?:(?P<qw>first|second|third|fourth)[- ](?:fiscal[- ])?quarter(?:\s+of)?(?:\s+(?:fiscal(?:\s+year)?|fy))?\s*'?(?P<qy>(?:20)\d\d|\d\d(?!\d))?"
    r"|q(?P<qn>[1-4])\b\s*(?:of\s+)?(?:(?:fiscal(?:\s+year)?|fy)\s*'?)?(?P<qy2>(?:20)\d\d|\d\d(?!\d))?"
    r"|fq(?P<fq>[1-4])\s*-\s*(?P<fqy>\d\d)"
    r"|(?:full[- ](?:fiscal[- ])?year|fiscal(?:\s+year)?|fy)\s*'?(?P<fy>(?:20)\d\d|\d\d(?!\d))"
    r"|(?P<fyw>full[- ](?:fiscal[- ])?year|the year)"
    r"|(?:(?:for|in)\s+(?:calendar\s+)?(?:year\s+)?|calendar\s+(?:year\s+)?)(?P<cy>20\d\d)"
    r"|(?P<qt>the quarter))")
_YEAR_NEAR = re.compile(r"(?i)\b(?:fy\s*'?(\d{2,4})|(?:fiscal(?: year)?|full[- ]year)\s+(20\d\d)|(20\d\d))\b")
_BACKREF = re.compile(r"(?i)(compared (?:to|with)|versus|vs\.?|from|over|than|prior|last|ago|included|includes|including|half of|end of|"
                      r"which|reported|in the)\s*(?:the\s+)?$")
_NUMTOK = r"\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|\(?-?\d+(?:\.\d+)?\)?"
_SCALE = r"(?:\s*(billion|million|thousand|bn|b|m)\b)?"
_MONEY = rf"\$\s*(?:{_NUMTOK})"
_RANGE_SEP = r"\s*(?:to|and|-|–|—)\s*"
_V_MONEY_PM = re.compile(rf"(?i)({_MONEY}){_SCALE},?\s*(?:plus or minus|±|\+/-)\s*(\$?\s*(?:{_NUMTOK})){_SCALE}\s*(%)?")
_V_MONEY_RANGE = re.compile(rf"(?i)({_MONEY}){_SCALE}{_RANGE_SEP}(\$?\s*(?:{_NUMTOK})){_SCALE}(?!\s*%)")
_V_MONEY = re.compile(rf"(?i)({_MONEY}){_SCALE}")
_PCT = r"(?:%|\s*percent\b)"
_V_PCT_PM = re.compile(rf"(?i)(-?\d+(?:\.\d+)?){_PCT},?\s*(?:plus or minus|±|\+/-)\s*(\d+(?:\.\d+)?)\s*(%|percent|basis points|bps)")
_V_PCT_RANGE = re.compile(rf"(?i)(?:(down|up|decline of|growth of)\s+)?(flat|-?\d+(?:\.\d+)?){_PCT}?\s*(?:to|and|-|–|—)\s*(?:(down|up)\s+)?(-?\d+(?:\.\d+)?){_PCT}(?!\s*(?:points?|pts))")
_V_PCT = re.compile(rf"(?i)(-?\d+(?:\.\d+)?){_PCT}(?!\s*(?:points?|pts))")
_METRICS = [   # (metric, unit it is stated in, pattern) — the earliest match in a clause names it, the longest on a tie
    ("eps", "money", r"(?:adjusted\s+)?(?:diluted\s+)?earnings(?=[^.$]{0,40}\$[^;]{0,40}\bper share)|(?:diluted\s+)?(?:(?:non[- ]gaap|adjusted|gaap)\s+)?(?:diluted\s+)?(?:earnings|(?:net\s+)?income|eps)\s+per\s+(?:diluted\s+)?share|\beps\b|per diluted share"),
    ("gross_margin", "pct", r"gross (?:profit )?margins?(?: rate)?"),
    ("operating_margin", "pct", r"operating (?:income |profit )?margins?(?: rate)?"),
    ("operating_income", "money", r"(?:income|profit) from operations|operating (?:income|profit)(?! margin)"),
    ("net_income", "money", r"net (?:income|earnings)(?! per)"),
    ("comparable_sales", "growth", r"comparable (?:store )?sales|comp sales|same[- ]store sales"),
    ("revenue", "money", r"(?:(?:total|net|consolidated)\s+)?(?:revenues?|sales)"),
]
_METRIC_RX = [(m, u, re.compile(rf"(?i)\b{rx}")) for m, u, rx in _METRICS]
_SEGMENT = re.compile(r"([A-Z][\w&/\-]*(?:\s+(?:and\s+)?[A-Z][\w&/\-]*){0,3})\s+$")   # "Total Cloud", "Product", "Subscription and Support"
_HEADLINE_REVENUE = re.compile(r"(?i)^(?:total\s+|net\s+|consolidated\s+)?(?:revenues?|sales|net sales|net revenues?)$")
_MULT = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "m": 1e6, "thousand": 1e3}


def _num(s: str | None) -> float | None:
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    neg = (s.startswith("(") and s.endswith(")")) or s.startswith("-")
    try:
        v = float(s.strip("()-").strip())
    except ValueError:
        return None
    return -v if neg else v


def _scaled(v, *scales):
    k = next((x.lower() for x in scales if x), "")
    return None if v is None else v * _MULT.get(k, 1)


def _value(seg: str, unit: str, table_scale: float = 1.0) -> tuple[str | None, float | None, float | None, int]:
    """(unit, low, high, end) of the first figure in a clause; (None, None, None, 0) when it states none."""
    if unit == "money":
        m = _V_MONEY_PM.search(seg)
        if m:
            mid, tol = _scaled(_num(m.group(1)), m.group(2)), _num(m.group(3))
            if mid is not None and tol is not None:
                if m.group(5):
                    return "money", mid * (1 - tol / 100), mid * (1 + tol / 100), m.end()
                tol = _scaled(tol, m.group(4), m.group(2))
                return "money", mid - tol, mid + tol, m.end()
        m = _V_MONEY_RANGE.search(seg)
        if m and _num(m.group(1)) is not None and _num(m.group(3)) is not None:
            lo, hi = _scaled(_num(m.group(1)), m.group(2), m.group(4)), _scaled(_num(m.group(3)), m.group(4), m.group(2))
            if not (m.group(2) or m.group(4)):
                lo, hi = lo * table_scale, hi * table_scale
            return "money", min(lo, hi), max(lo, hi), m.end()
        m = _V_MONEY.search(seg)
        if m and _num(m.group(1)) is not None:
            v = _scaled(_num(m.group(1)), m.group(2)) * (1 if m.group(2) else table_scale)
            return "money", v, v, m.end()
        # a money metric stated as a change ("revenue to grow 3% to 4%") falls through to the growth forms
    m = _V_PCT_PM.search(seg)
    if m:
        mid, tol = float(m.group(1)), float(m.group(2))
        tol = tol / 100 if m.group(3).lower() in ("basis points", "bps") else tol
        return ("pct" if unit == "pct" else "growth"), (mid - tol) / 100, (mid + tol) / 100, m.end()
    m = _V_PCT_RANGE.search(seg)
    if m:
        lo = 0.0 if m.group(2).lower() == "flat" else float(m.group(2))
        hi = float(m.group(4))
        d1, d2 = (m.group(1) or "").lower(), (m.group(3) or "").lower()
        if d1.startswith(("down", "decline")):
            lo = -abs(lo)
        if d2 == "down" or (d1.startswith(("down", "decline")) and not d2):
            hi = -abs(hi)
        u = "pct" if unit == "pct" else "growth"
        if u == "growth" and not (d1 or d2) and re.search(r"(?i)\b(decline|decrease|down|lower)\b", seg[:m.start()]) and lo >= 0 and hi > 0:
            lo, hi = -hi, -lo
        return u, min(lo, hi) / 100, max(lo, hi) / 100, m.end()
    m = _V_PCT.search(seg)
    if m:
        v = float(m.group(1)) / 100
        u = "pct" if unit == "pct" else "growth"
        if u == "growth" and re.search(r"(?i)\b(decline|decrease|down|lower)\b", seg[:m.start()]) and v > 0:
            v = -v
        return u, v, v, m.end()
    return None, None, None, 0


def _period_at(seg: str, start: int = 0, end: int | None = None) -> dict | None:
    """The first period named in seg[start:end] that is not a back-reference ("compared with the third quarter")."""
    for m in _PERIOD.finditer(seg, start, len(seg) if end is None else end):
        if _BACKREF.search(seg[max(0, m.start() - 30):m.start()]):
            continue
        g = m.groupdict()
        if g["qt"]:
            return {"kind": "Q", "quarter": None, "year": None, "label": m.group(0)}
        if g["fyw"]:
            y = _YEAR_NEAR.search(seg[m.end():m.end() + 22])
            return {"kind": "FY", "quarter": None, "year": _year(next((x for x in y.groups() if x), None)) if y else None,
                    "label": (m.group(0) + (seg[m.end():y.end() + m.end()] if y else "")).strip()}
        if g["fy"] or g["cy"]:
            return {"kind": "FY", "quarter": None, "year": _year(g["fy"] or g["cy"]), "label": m.group(0).strip()}
        q = _WORDS_Q.get((g["qw"] or "").lower()) or int(g["qn"] or g["fq"] or 0) or None
        y = g["qy"] or g["qy2"] or g["fqy"]
        if not y:
            near = _YEAR_NEAR.search(seg[m.end():m.end() + 14])
            y = next((x for x in near.groups() if x), None) if near else None
        return {"kind": "Q", "quarter": q, "year": _year(y), "label": m.group(0).strip()}
    return None


def _year(s: str | None) -> int | None:
    if not s:
        return None
    y = int(s)
    return y + 2000 if y < 100 else y


def _basis(s: str) -> str | None:
    if re.search(r"(?i)\bgaap and (?:non[- ]gaap|adjusted)\b", s):
        return "both"
    if re.search(r"(?i)\b(non[- ]gaap|adjusted|adj\.|core)(?:\b|(?<=\.))", s):
        return "non_gaap"
    if re.search(r"(?i)\bgaap\b", s):
        return "gaap"
    return None


def _statements(section: str) -> list[str]:
    out = []
    for line in section.split("\n"):
        if "|" in line:   # a table row is one statement ("Adj. EPS | $2.80 to $2.87" must not split at "Adj.")
            out.append(line.strip())
            continue
        for p in re.split(r"\s*[•●◦▪]\s*|(?<=[.;])\s+(?=[A-Z(])", line):
            p = p.strip(" ;:")
            if len(p) > 8:
                out.append(p)
    return out


def _clauses(s: str) -> list[tuple[str, str, str, int]]:
    """(metric, unit, metric phrase, start) for each metric named in a statement, in order."""
    hits = []
    for metric, unit, rx in _METRIC_RX:
        for m in rx.finditer(s):
            hits.append((m.start(), -(m.end() - m.start()), metric, unit, m.group(0)))
    hits.sort()
    out, last_end = [], -1
    for start, neg_len, metric, unit, phrase in hits:
        if start < last_end:
            continue   # inside a longer phrase already taken ("net income per share" is not also "net income")
        out.append((metric, unit, phrase, start))
        last_end = start - neg_len
    return out


_BASELINE = re.compile(r"(?i)\b(based on the following|is based on|prior[- ]year (?:figures|results)|last year's|"
                       r"compared to the prior forecast|previous guidance of|prior guidance of|includes? \$|excludes? \$|"
                       r"assum(?:es|ing) (?:approximately )?\$)")
_FOOTNOTE = re.compile(r"^(?:\(\d+\)|\d\s|\*|†)")
_OF_REVENUE = re.compile(r"(?i)^\s*of\s+(?:projected\s+|net\s+|total\s+)?(?:revenues?|sales)")
_PRIOR_COL = re.compile(r"(?i)\b(prior|previous|last)\b")
_NOT_SEGMENT = re.compile(r"(?i)the|our|its|of|for|to|in|on|at|full|year|fiscal|quarter|first|second|third|fourth|"
                          r"fy\d*|q[1-4]|\d+|raises?|initiates?|updates?|maintains?|reaffirms?|expects?|expected|now|sees|"
                          r"guidance|outlook|total|net|consolidated|company|that|which|with|is|are|be|will")
_LABEL_DROP = re.compile(r"^(?:Total|Net|Consolidated|The|Our)\b\s*")


def _header_slots(rows: list[list[str]], width: int) -> list[dict] | None:
    """A table's value columns, in order, from its header rows (`width`: the value cells of a row): each with the
    basis, the period, and whether to skip it — a change column, or the prior guidance (Walmart's "Prior guidance |
    Change | Updated guidance"). None when no header row lines up with the values."""
    def slot(c):
        return {"basis": _basis(c), "period": _period_at(c),
                "skip": bool(_PRIOR_COL.search(c) or re.search(r"(?i)^(?:%?\s*change|y/y|growth|vs\.?)", c.strip()))}
    best = None
    for cells in rows:
        cells = cells[1:] if len(cells) == width + 1 else cells   # a header that also names the label column
        if len(cells) == width:
            sl = [slot(c) for c in cells]
            if best is None or sum(bool(x["basis"] or x["period"]) for x in sl) >= sum(bool(x["basis"] or x["period"]) for x in best):
                best = sl if best is None else [{**o, **{k: v for k, v in n.items() if v}} for o, n in zip(best, sl)]
    if best and not any(x["basis"] or x["period"] or x["skip"] for x in best):
        best = None   # "2026 | 2025": a results table's years, not a guidance header
    for cells in rows:   # a row of bases above a row of periods ("GAAP | Non-GAAP" over "FY27 | Change | FY27 | Change")
        bases = [_basis(c) for c in cells if _basis(c)]
        if best and bases and not any(x["basis"] for x in best) and len(best) % len(bases) == 0:
            per = len(best) // len(bases)
            for i, x in enumerate(best):
                x["basis"] = bases[i // per]
    return best


_VERSION_COL = re.compile(r"(?i)\b(as of|original|prior|previous|updated|current|revised|new)\b")


def _last_header(rows: list[list[str]], width: int) -> list[str]:
    for cells in reversed(rows):
        cells = cells[1:] if len(cells) == width + 1 else cells
        if len(cells) == width:
            return cells
    return []


def _is_header(cells: list[str]) -> bool:
    if len(cells) < 2:
        return False
    rest = _PERIOD.sub("", " ".join(cells))
    rest = re.sub(r"(?i)\b(?:20\d\d|fy\s*'?\d\d|q[1-4])\b|\(\d\)|\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b", "", rest)
    return not re.search(r"\d", rest)


def parse(section: str) -> list[dict]:
    """The section's forward-looking statements, each with what could be read from it: one item per figure
    (a statement naming revenue and EPS, or one figure for the quarter and one for the year, gives several)."""
    out, seen = [], set()
    current = None          # the period a lead-in set ("For the first quarter of fiscal 2027, the company expects:")
    lead_in = False         # the bullets right after a lead-in are forward-looking without saying so
    headers, table_forward = [], False
    money_scale = 1e6 if re.search(r"(?i)\bin millions\b", section) else 1e9 if re.search(r"(?i)\bin billions\b", section) else 1.0
    prev_forward = prev_header = in_table = False
    bases_seen: list[str] = []
    for s in _statements(section):
        cells = [c for c in (x.strip() for x in re.split(r"\s*\|\s*", s)) if c]
        table = len(cells) > 1
        own = _period_at(s)
        own = _fill(own, current)   # "Full-year net sales ..." under "expectations for 2026:"; "... for the quarter"
        if table and not in_table:
            table_forward = True   # a table inside the outlook section is guidance until it shows it is results
        in_table = table
        if table and _is_header(cells):
            if not headers or not prev_header:
                headers = []
            headers.append(cells)
            hb = [_basis(c) for c in cells if _basis(c)]
            if len(hb) >= 2:
                bases_seen = hb
            # a guidance table says so in its header or in the line before it; a results table ("Three Months Ended") does not
            if re.search(r"(?i)\bended\b|three months|six months|nine months|twelve months", s):
                table_forward = False
            if own:
                current = own
            prev_header = True
            continue
        prev_header = False
        if not table and (own or len(s) > 150):
            headers = []   # a new table's title ("Full Year FY27 Guidance") or prose: the old header no longer applies
        if _FOOTNOTE.search(s) or _BOILERPLATE.search(s) or (not table and re.search(r"(?i)\b(based on the following|is based on)\b", s)):
            prev_forward = False
            continue
        if not table:
            cut = _BASELINE.search(s)
            if cut:
                s = s[:cut.start()].rstrip(" ,;")   # "..., up from previous guidance of $5,840 million": keep the new figure
        fwd_own = bool(_FORWARD.search(s))
        if table and any(re.fullmatch(r"\(?-?[\d,]+(?:\.\d+)?\)?", c) for c in cells[1:]):
            table_forward = False   # bare numbers ("3,998 | 4,273 | -6%"): a results table, to its end
        forward = (table and table_forward) or (not table and (fwd_own or (lead_in and len(s) < 220)))
        prev_forward = fwd_own
        clauses = _clauses(cells[0] if table else s)
        if not clauses:
            if own and (fwd_own or s.endswith(":") or len(s) < 60):   # a lead-in, or a period on its own line ("Fiscal year 2027")
                current = own
            if fwd_own:
                lead_in = True
                if not table:
                    out.append({"metric": None, "metric_label": None, "basis": None, **_pfields(own or current),
                                "unit": None, "low": None, "high": None, "text": s[:600]})
            continue
        if not forward or (_PAST.search(s) and not _STRONG_FWD.search(s)):
            continue   # a result reported, not an expectation
        if own and not table:
            current = own
        got = False
        if table:
            metric, unit, phrase, start = clauses[0]
            if re.match(r"(?i)\s*growth", cells[0][start + len(phrase):]):
                unit = "growth"   # "Revenue growth | 11% - 12%"
            label = _label(cells[0], metric, phrase, start, table=True)
            vcells = cells[1:]
            if any(re.fullmatch(r"\(?-?[\d,]+(?:\.\d+)?\)?", c) for c in vcells):
                continue   # bare numbers: a results table ("3,998 | 4,273 | -6%"), not guidance
            slots = _header_slots(headers, len(vcells))
            versions = [i for i, c in enumerate(_last_header(headers, len(vcells))) if _VERSION_COL.search(c)]
            if len(versions) >= 2:
                # dated versions of the guidance ("Original | As of 5.21 | As of 8.20"): the latest column, where
                # "Unchanged" means the version before it
                latest = next((c for c in reversed(vcells[:versions[-1] + 1]) if not re.fullmatch(r"(?i)unchanged|same|reaffirmed", c)), None)
                vcells, slots = ([latest] if latest else []), [{"basis": None, "period": None, "skip": False}]
            has_money = unit == "money" and any(_value(c, "money")[0] == "money" for c in vcells)
            figs = [c for c in vcells if not _BASELINE.search(c) and _value(c, unit)[0] and not (has_money and _value(c, unit)[0] == "growth")]
            if not slots and len(figs) > 1:
                if len(figs) == len(bases_seen):   # the GAAP / non-GAAP header of the table above still applies
                    slots = [{"basis": b, "period": None, "skip": False} for b in bases_seen]
                    vcells = figs
                else:
                    continue   # several figures and no header to say which is which (a results table): not read
            for ci, cell in enumerate(vcells):
                sl = slots[ci] if slots else None
                if (sl and sl["skip"]) or _BASELINE.search(cell):
                    continue
                u, lo, hi, _ = _value(cell, unit, money_scale if metric != "eps" else 1.0)
                if not u or (u == "growth" and has_money):
                    continue   # a change column beside the figure itself
                basis = (sl and sl["basis"]) or _basis(cells[0])
                per = (sl and sl["period"]) or _period_at(cells[0]) or current
                got |= _add(out, seen, metric, label, basis, per, u, lo, hi, s)
                if not slots:
                    break   # no header to say what a second column is: keep the first
            continue
        for k, (metric, unit, phrase, start) in enumerate(clauses):
            stop = clauses[k + 1][3] if k + 1 < len(clauses) else len(s)
            seg = s[start + len(phrase):stop]
            label = _label(s, metric, phrase, start)
            if re.match(r"(?i)\s*growth", seg):
                unit = "growth"
            pos = 0
            while True:
                u, lo, hi, end = _value(seg[pos:], unit, money_scale if metric != "eps" else 1.0)
                if not u:
                    break
                tail = s[start + len(phrase) + pos + end:]
                if u in ("growth", "pct") and _OF_REVENUE.match(tail):   # "66 percent of projected revenue": a margin
                    u = "pct"
                    metric = {"operating_income": "operating_margin", "gross_profit": "gross_margin"}.get(metric, metric)
                after = _period_at(seg, pos + end, pos + end + 30)
                per = after if after and re.match(r"(?i)\s*,?\s*for\b", tail) else (_period_at(s, 0, start) or own or current)
                per = _fill(per, current)
                prev_end = (clauses[k - 1][3] + len(clauses[k - 1][2])) if k else 0
                basis = _basis(s[prev_end:start + len(phrase)]) or _basis(re.split(r"(?i),?\s+and\s+|;", s[start + len(phrase):stop])[0])
                got |= _add(out, seen, metric, label, basis, per, u, lo, hi, s)
                pos += end
                # a second figure counts only when it names its own period ("$0.62 to $0.64 for Q3 and $2.80 to $2.87 for FY27")
                if not (after and re.match(r"(?i)\s*,?\s*for\b", tail)):
                    break
                nxt = re.search(r"(?i)\band\b", seg[pos:pos + 40])
                if not nxt:
                    break
                pos += nxt.end()
        if not got and fwd_own:
            out.append({"metric": None, "metric_label": None, "basis": None, **_pfields(own or current),
                        "unit": None, "low": None, "high": None, "text": s[:600]})
    return out


def _label(s: str, metric: str, phrase: str, start: int, table: bool = False) -> str:
    """The metric as written, with the segment it is qualified by ("Total Cloud revenue", "Annual recurring revenue")."""
    if table:   # a table row's label cell is the label, less its footnote marks
        label = re.sub(r"\s*\(\d+\)|\d$", "", s).strip()
        return label[:1].upper() + label[1:]
    label = phrase.strip()
    if metric == "revenue" and not re.match(r"(?i)(total|consolidated)\b", label):
        words = re.findall(r"[A-Za-z][\w&/\-]*", s[max(0, start - 60):start])
        seg = []
        for w in reversed(words[-4:]):   # the words just before "revenue", back to the first that is not a segment name
            if _NOT_SEGMENT.fullmatch(w) or (w.isupper() and len(w) <= 5):   # ...or a ticker-like name ("AMD expects")
                break
            seg.insert(0, w)
        while seg and seg[0].lower() == "and":
            seg.pop(0)
        if seg:
            label = f"{' '.join(seg)} {label}"
    return label[:1].upper() + label[1:]


def headline_revenue(label: str | None) -> bool:
    """Whether a revenue line is the company's total ("Revenue", "Net sales (cc)", "Total revenue growth"), not a
    segment ("Cloud revenue") or a measure like annual recurring revenue."""
    if not label:
        return False
    core = re.sub(r"(?i)\s*\([^)]*\)|\s+growth\b|\s*\d$", "", label).strip()
    return bool(_HEADLINE_REVENUE.match(core))


def _fill(p: dict | None, current: dict | None) -> dict | None:
    """A period missing its year or quarter takes them from the lead-in's period of the same kind."""
    if not p or not current or current["kind"] != p["kind"]:
        return p
    return {**p, "year": p["year"] or current["year"], "quarter": p["quarter"] or current["quarter"]}


def _pfields(p: dict | None) -> dict:
    return {"period_kind": p["kind"] if p else None, "fiscal_year": p["year"] if p else None,
            "fiscal_quarter": p["quarter"] if p else None, "period_label": p["label"] if p else None}


def _add(out, seen, metric, label, basis, per, unit, lo, hi, text) -> bool:
    key = (metric, label.lower(), basis, per and per["kind"], per and per["year"], per and per["quarter"], round(lo or 0, 6), round(hi or 0, 6))
    if key in seen:
        return True
    seen.add(key)
    out.append({"metric": metric, "metric_label": label, "basis": basis, **_pfields(per), "unit": unit,
                "low": lo, "high": hi, "text": text[:600]})
    return True


# ------------------------------------------------------------------ fetching (SEC)

def releases(symbol: str, since: dt.date | None = None, limit: int = RELEASES_BACK) -> list[dict]:
    """The company's results releases (8-K, item 2.02), newest first: filing date, accession, filing index URL."""
    from . import financials as fin
    cik = fin._sec_cik(symbol)
    if cik is None:
        return []
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=fin._sec_headers(), timeout=30)
    time.sleep(SEC_PAUSE)
    r.raise_for_status()
    f = r.json().get("filings", {}).get("recent", {})
    out = []
    for i, form in enumerate(f.get("form", [])):
        if form != "8-K" or "2.02" not in (f.get("items", [""] * (i + 1))[i] or ""):
            continue
        day = dt.date.fromisoformat(f["filingDate"][i])
        if since and day <= since:
            break
        acc = f["accessionNumber"][i]
        out.append({"filed": day, "accession": acc,
                    "index": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{acc}-index.html"})
        if len(out) >= limit:
            break
    return out


def exhibit_url(index_url: str) -> str | None:
    """The press release in a filing: its first EX-99 document (by the index's Type column)."""
    from bs4 import BeautifulSoup
    from . import financials as fin
    r = requests.get(index_url, headers=fin._sec_headers(), timeout=30)
    time.sleep(SEC_PAUSE)
    r.raise_for_status()
    for tr in BeautifulSoup(r.text, "lxml").select("table.tableFile tr"):
        td = [c.get_text(strip=True) for c in tr.find_all("td")]
        a = tr.find("a")
        if len(td) >= 4 and a and td[3].upper().startswith("EX-99") and a["href"].lower().endswith((".htm", ".html", ".txt")):
            return "https://www.sec.gov" + a["href"]
    return None


def read_release(url: str) -> tuple[str, list[dict]]:
    from . import financials as fin
    r = requests.get(url, headers=fin._sec_headers(), timeout=60)
    time.sleep(SEC_PAUSE)
    r.raise_for_status()
    section = outlook_section(_text(r.text))
    return section, (parse(section) if section else [])


def _store(market: str, symbol: str, rel: dict, url: str | None, section: str, items: list[dict]) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM guidance_items WHERE market=%s AND symbol=%s AND accession=%s", (market, symbol, rel["accession"]))
        for i, it in enumerate(items):
            cur.execute("""INSERT INTO guidance_items (market, symbol, accession, idx, metric, metric_label, basis, period_kind,
                             fiscal_year, fiscal_quarter, period_label, unit, low, high, text)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (market, symbol, rel["accession"], i, it["metric"], it["metric_label"], it["basis"], it["period_kind"], it["fiscal_year"],
                         it["fiscal_quarter"], it["period_label"], it["unit"], it["low"], it["high"], it["text"]))
        cur.execute("""INSERT INTO guidance_releases (market, symbol, accession, filed, url, section, items, figures, parser)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (market, symbol, accession) DO UPDATE SET url=EXCLUDED.url, section=EXCLUDED.section,
                         items=EXCLUDED.items, figures=EXCLUDED.figures, parser=EXCLUDED.parser, fetched_at=now()""",
                    (market, symbol, rel["accession"], rel["filed"], url, section, len(items),
                     sum(1 for it in items if it["unit"]), PARSER_VERSION))


def fetch_symbol(market: str, symbol: str) -> dict:
    """Read the company's results releases not read yet (or read by an older parser); never raises."""
    try:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT accession, parser FROM guidance_releases WHERE market=%s AND symbol=%s", (market, symbol))
            known = dict(cur.fetchall())
        new = [r for r in releases(symbol) if known.get(r["accession"]) != PARSER_VERSION]
        found = 0
        for rel in new:
            url = exhibit_url(rel["index"])
            section, items = read_release(url) if url else ("", [])
            _store(market, symbol, rel, url, section, items)
            found += bool(section)
        note = f"{len(new)} new releases read · {found} with an outlook"
    except Exception as exc:  # noqa: BLE001 — one bad company must not stop the batch
        new, note = [], f"failed ({type(exc).__name__}: {exc})"[:300]
        logger.warning("%s %s: %s", market, symbol, exc)
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO guidance_status (market, symbol, fetched_at, note) VALUES (%s,%s,now(),%s)
                       ON CONFLICT (market, symbol) DO UPDATE SET fetched_at=now(), note=EXCLUDED.note""", (market, symbol, note))
    return {"read": len(new), "note": note}


def refresh(market: str, symbols: list[str], force: bool = False, progress=None) -> dict:
    """Read new results releases for `symbols` (markets whose filings come from SEC EDGAR only)."""
    if MARKETS[market].quarterly_source != "sec_edgar":
        return {"requested": len(symbols), "skipped": "no SEC filings for this market"}
    init_schema()
    with db.get_connection().cursor() as cur:
        # fresh: checked lately, and every release read by the current rules (a PARSER_VERSION bump re-reads them)
        cur.execute("""SELECT symbol FROM guidance_status s WHERE market=%s AND fetched_at > now() - %s * interval '1 day'
                       AND NOT EXISTS (SELECT 1 FROM guidance_releases r WHERE r.market=s.market AND r.symbol=s.symbol
                                       AND r.parser < %s)""", (market, MAX_AGE_DAYS, PARSER_VERSION))
        fresh = {r[0] for r in cur.fetchall()}
    todo = [s for s in symbols if force or s not in fresh]
    stats = {"requested": len(symbols), "skipped_fresh": len(symbols) - len(todo), "releases_read": 0, "failed": 0}
    for i, sym in enumerate(todo):
        if progress:
            progress(f"guidance: {i + 1:,}/{len(todo):,} companies · {stats['releases_read']:,} releases read")
        r = fetch_symbol(market, sym)
        stats["releases_read"] += r["read"]
        stats["failed"] += r["note"].startswith("failed")
    return stats


# ------------------------------------------------------------------ read (the page and the chart)

POSITION_TOL = 0.0025   # a consensus within 0.25% of a range end (a rounding of the company's figure) counts as inside it
CHANGE_FLAT = 0.005      # a guidance midpoint moving less than this (0.5%) from the prior release reads as maintained
_ORDER = {"revenue": 0, "comparable_sales": 1, "eps": 2, "operating_income": 3, "operating_margin": 4, "gross_margin": 5,
          "net_income": 6}
METRIC_NAME = {"revenue": "Revenue", "comparable_sales": "Comparable sales", "eps": "EPS", "operating_income": "Operating income",
               "operating_margin": "Operating margin", "gross_margin": "Gross margin", "net_income": "Net income"}


def _releases(market: str, symbol: str) -> list[dict]:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('guidance_releases')")
        if cur.fetchone()[0] is None:
            return []
        cur.execute("""SELECT accession, filed, url, section, figures FROM guidance_releases WHERE market=%s AND symbol=%s
                       ORDER BY filed DESC""", (market, symbol))
        rels = [{"accession": a, "filed": f, "url": u, "has_outlook": bool(sec), "figures": n} for a, f, u, sec, n in cur.fetchall()]
        cols = ["accession", "idx", "metric", "metric_label", "basis", "period_kind", "fiscal_year", "fiscal_quarter",
                "period_label", "unit", "low", "high", "text"]
        cur.execute(f"SELECT {', '.join(cols)} FROM guidance_items WHERE market=%s AND symbol=%s ORDER BY accession, idx",
                    (market, symbol))
        items = [dict(zip(cols, r)) for r in cur.fetchall()]
    by = {}
    for it in items:
        by.setdefault(it["accession"], []).append(it)
    for r in rels:
        r["items"] = _clean(by.get(r["accession"], []))
    return rels


def _clean(items: list[dict]) -> list[dict]:
    """Figures only, one per metric / line / basis / period (a release states its outlook in the highlights and
    again in a table), headline revenue named plainly, basis dropped where it does not apply."""
    out, seen = [], set()
    for it in items:
        if not it["unit"]:
            continue
        it = dict(it)
        if it["metric"] in ("revenue", "comparable_sales"):
            it["basis"] = None
        if it["basis"] == "both":
            it["basis"] = "non_gaap"   # stated once for both: the figure analysts compare with
        it["headline"] = it["metric"] != "revenue" or headline_revenue(it["metric_label"])
        line = METRIC_NAME[it["metric"]] if it["headline"] else re.sub(r"(?i)\s+growth$", "", it["metric_label"] or "")
        if it["unit"] == "growth" and it["metric"] not in ("comparable_sales",):
            line += " growth"
        it["line"] = line
        it["mid"] = (it["low"] + it["high"]) / 2 if it["low"] is not None and it["high"] is not None else None
        key = (line.lower(), it["basis"], it["period_kind"], it["fiscal_year"], it["fiscal_quarter"], it["unit"])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    out.sort(key=lambda x: (0 if x["period_kind"] == "Q" else 1 if x["period_kind"] == "FY" else 2,
                            not x["headline"], _ORDER.get(x["metric"], 9), x["basis"] != "non_gaap", x["line"]))
    return out


def _same(a: dict, b: dict) -> bool:
    return (a["line"].lower() == b["line"].lower() and a["basis"] == b["basis"] and a["unit"] == b["unit"]
            and a["period_kind"] == b["period_kind"] and a["fiscal_quarter"] == b["fiscal_quarter"]
            and (a["period_kind"] != "Q" or a["fiscal_quarter"] is not None)   # "the quarter" of two releases is two quarters
            and a["fiscal_year"] is not None and a["fiscal_year"] == b["fiscal_year"])


def _change(new: float | None, old: float | None, unit: str) -> str | None:
    if new is None or old is None:
        return None
    if unit in ("pct", "growth"):   # margins and growth rates move in points: a tenth of a point is the floor
        d = new - old
        return "maintained" if abs(d) < 0.001 else "raised" if d > 0 else "lowered"
    d = (new - old) / abs(old) if old else 0
    return "maintained" if abs(d) < CHANGE_FLAT else "raised" if d > 0 else "lowered"


def _position(value: float | None, lo: float | None, hi: float | None) -> str | None:
    if value is None or lo is None or hi is None:
        return None
    tol = abs(hi) * POSITION_TOL if abs(hi) > 0.5 else 0.0005   # rounding: a consensus a hair past the range end is at it
    return "above" if value > hi + tol else "below" if value < lo - tol else "within"


def _consensus_period(periods: list[dict], it: dict, filed: dt.date) -> dict | None:
    """The analyst-estimate period a release's guidance figure is for: the first quarter (or fiscal year) ending
    after the release, the fiscal year also agreeing with the year the release names."""
    q = it["period_kind"] == "Q"
    cands = sorted((p for p in periods if p.get("end_date") and p["quarter"] == q
                    and dt.date.fromisoformat(p["end_date"]) > filed), key=lambda p: p["end_date"])
    if not cands:
        return None
    p = cands[0]
    if not q and it["fiscal_year"] and dt.date.fromisoformat(p["end_date"]).year not in (it["fiscal_year"], it["fiscal_year"] + 1):
        return None
    return p


def _versus(it: dict, p: dict | None) -> dict | None:
    """The consensus for the same figure, where one exists: revenue against revenue, non-GAAP EPS against EPS."""
    if not p or not it["headline"]:
        return None
    if it["metric"] == "revenue" and it["unit"] == "money":
        v = p.get("rev_avg")
    elif it["metric"] == "revenue" and it["unit"] == "growth":
        v = p.get("rev_growth")
    elif it["metric"] == "eps" and it["unit"] == "money" and it["basis"] in ("non_gaap", None):
        v = p.get("eps_avg")
    else:
        return None
    if v is None:
        return None
    return {"value": v, "position": _position(v, it["low"], it["high"]), "period": p["period"], "name": p["name"],
            "vs_mid": (v - it["mid"]) / abs(it["mid"]) if it["mid"] and it["unit"] == "money" else
                      (v - it["mid"]) if it["mid"] is not None else None}


def summary(market: str, symbol: str, est: dict | None = None) -> dict | None:
    """The latest results release's outlook: each figure with the prior release's figure for the same period
    (raised / lowered / maintained) and the analysts' consensus now (above / within / below the range), the
    statements as written, and the releases read. None for a market without SEC filings or nothing read."""
    if MARKETS[market].quarterly_source != "sec_edgar":
        return None
    rels = _releases(market, symbol)
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('guidance_status')")
        st = None
        if cur.fetchone()[0] is not None:
            cur.execute("SELECT fetched_at, note FROM guidance_status WHERE market=%s AND symbol=%s", (market, symbol))
            st = cur.fetchone()
    if not rels and not st:
        return None
    latest = next((r for r in rels if r["has_outlook"]), None)
    periods = (est or {}).get("periods") or []
    items = []
    if latest:
        older = [r for r in rels if r["filed"] < latest["filed"]]
        for it in latest["items"]:
            prior = next(((r, o) for r in older for o in r["items"] if _same(it, o)), None)
            items.append({**{k: it[k] for k in ("line", "metric", "basis", "unit", "low", "high", "mid", "period_kind",
                                                 "fiscal_year", "fiscal_quarter", "period_label", "headline", "text")},
                          "prior": {"filed": str(prior[0]["filed"]), "low": prior[1]["low"], "high": prior[1]["high"],
                                    "change": _change(it["mid"], prior[1]["mid"], it["unit"])} if prior else None,
                          "consensus": _versus(it, _consensus_period(periods, it, latest["filed"]))})
        with db.get_connection().cursor() as cur:
            cur.execute("""SELECT text FROM guidance_items WHERE market=%s AND symbol=%s AND accession=%s ORDER BY idx""",
                        (market, symbol, latest["accession"]))
            written = list(dict.fromkeys(r[0] for r in cur.fetchall()))
    else:
        written = []
    read = []
    for it in items:
        if not it["headline"] or it["metric"] not in ("revenue", "eps"):
            continue
        per = _period_words(it)
        bits = []
        if it["prior"] and it["prior"]["change"]:
            bits.append(f"{it['prior']['change']} from the {_d(it['prior']['filed'])} release")
        c = it["consensus"]
        if c and c["position"]:
            bits.append(f"consensus {'inside' if c['position'] == 'within' else c['position']} the range")
        if bits:
            read.append(f"{per} {it['line'] if it['metric'] != 'eps' or it['basis'] != 'non_gaap' else 'non-GAAP EPS'}: "
                        + "; ".join(bits) + ".")
    return {"latest": {"filed": str(latest["filed"]), "url": latest["url"]} if latest else None,
            "items": items, "written": written[:40], "read": read[:6],
            "releases": [{"filed": str(r["filed"]), "url": r["url"], "has_outlook": r["has_outlook"], "figures": r["figures"]}
                         for r in rels[:RELEASES_BACK]],
            "fetched_at": st[0].isoformat() if st else None, "note": st[1] if st else None,
            "consensus_asof": (est or {}).get("asof"),
            "source": "the company's results press release (SEC Form 8-K, exhibit 99), read by rules"}


def _period_words(it: dict) -> str:
    if it["period_kind"] == "Q":
        return f"Q{it['fiscal_quarter'] or '?'}" + (f" FY{str(it['fiscal_year'])[2:]}" if it["fiscal_year"] else "")
    if it["period_kind"] == "FY":
        return f"FY{str(it['fiscal_year'])[2:]}" if it["fiscal_year"] else "Full year"
    return ""


def _d(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


def quarter_guidance(market: str, symbol: str, report_date: str, actual_eps: float | None = None,
                     actual_revenue: float | None = None, consensus: dict | None = None) -> dict | None:
    """What the company guided for the quarter a report on `report_date` covers: the quarterly figures of the
    last results release filed before it (at least a week earlier, so not the report itself) — with the
    reported figures (a past report) or the analysts' consensus (`consensus`, an estimates period: an
    upcoming one) placed against the range: above / within / below."""
    if MARKETS[market].quarterly_source != "sec_edgar":
        return None
    d = dt.date.fromisoformat(report_date)
    rels = [r for r in _releases(market, symbol) if r["has_outlook"] and (d - r["filed"]).days >= 7]
    if not rels:
        return None
    r = rels[0]
    if (d - r["filed"]).days > 130:
        return None   # a release more than a quarter before: not the guidance for this report
    q = [it for it in r["items"] if it["period_kind"] == "Q" and it["headline"]]
    rev = next((it for it in q if it["metric"] == "revenue" and it["unit"] == "money"), None)
    eps = next((it for it in q if it["metric"] == "eps" and it["unit"] == "money" and it["basis"] == "non_gaap"), None) \
        or next((it for it in q if it["metric"] == "eps" and it["unit"] == "money"), None)
    if not rev and not eps:
        return None
    pick = lambda it: {"low": it["low"], "high": it["high"], "basis": it["basis"], "line": it["line"]} if it else None  # noqa: E731
    out = {"filed": str(r["filed"]), "url": r["url"], "revenue": pick(rev), "eps": pick(eps)}
    if rev and actual_revenue is not None:
        out["revenue"]["actual"], out["revenue"]["position"] = actual_revenue, _position(actual_revenue, rev["low"], rev["high"])
    if eps and actual_eps is not None:
        out["eps"]["actual"], out["eps"]["position"] = actual_eps, _position(actual_eps, eps["low"], eps["high"])
    if consensus:
        if rev and consensus.get("rev_avg") is not None:
            out["revenue"]["consensus"] = consensus["rev_avg"]
            out["revenue"]["consensus_position"] = _position(consensus["rev_avg"], rev["low"], rev["high"])
        if eps and eps["basis"] in ("non_gaap", None) and consensus.get("eps_avg") is not None:
            out["eps"]["consensus"] = consensus["eps_avg"]
            out["eps"]["consensus_position"] = _position(consensus["eps_avg"], eps["low"], eps["high"])
    return out


def reported_sales(market: str, symbol: str) -> dict[str, float]:
    """{quarter end: revenue} from the stored quarterly results (marketdata/financials.py)."""
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT period_end, value FROM financial_lines WHERE market=%s AND symbol=%s AND period_type='Q'
                       AND line='sales' AND value IS NOT NULL""", (market, symbol))
        return {str(d): float(v) for d, v in cur.fetchall()}


def quarter_reported(sales: dict[str, float], report_date: str) -> float | None:
    """Revenue of the quarter a report covers: the latest quarter that ended in the 120 days before it."""
    d = dt.date.fromisoformat(report_date)
    ends = [e for e in sales if 0 < (d - dt.date.fromisoformat(e)).days <= 120]
    return sales[max(ends)] if ends else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--symbols", required=True, help="comma-separated")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(refresh(a.market, [s.strip() for s in a.symbols.split(",") if s.strip()], force=a.force))


if __name__ == "__main__":
    main()
