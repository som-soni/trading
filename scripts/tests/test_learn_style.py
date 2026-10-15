"""Every Learn guide stands on its own and reads plainly.

The Learn section teaches trading — the broader context, the market, a stock,
and then strategies and derivatives. It may use the app's stored market data to
draw its charts and measure its examples, but it must not depend on the app:
no page names, file paths, code names or the app's own strategy backtests. And
it must be readable by someone new to trading on a first pass.

This test enforces the measurable part of that standard:

  standalone
    1. no references to the app ("this app", "the app's", page names such as
       "Markets →", "the Chart page");
    2. no file paths or code identifiers in prose (`core/regime.py`,
       `CASH_YIELD`, `trend_pullback`);
    3. no figures from the app's own strategy backtests (run ids, spec ids);
  readable
    4. an "In short" block of 3-5 bullets near the top;
    5. paragraphs of at most MAX_PARA_SENTENCES sentences;
    6. sentences of at most MAX_SENTENCE_WORDS words, averaging at most
       MAX_AVG_WORDS;
    7. at most MAX_NUMBERS_PER_SENTENCE numbers in one sentence (a date counts
       once) — a sentence carrying more belongs in a table;
  linked
    8. every link to another guide points at a file that exists.

What it cannot check — that an unfamiliar term is explained where it first
appears, that an example comes before the rule — is left to a read-through.

Guides not yet rewritten to this standard are listed in NOT_YET_CONVERTED:
they are reported but do not fail. Take a guide off the list when it is
rewritten; a listed guide that already passes fails the test, so the list only
shrinks.

Run: `PYTHONPATH=. python3 -m tests.test_learn_style`
"""

import re
import statistics
import sys

from swing_screener import paths

MAX_PARA_SENTENCES = 5
MAX_SENTENCE_WORDS = 35
MAX_AVG_WORDS = 18
MAX_NUMBERS_PER_SENTENCE = 3
IN_SHORT_WITHIN_LINES = 20      # the "In short" block must start this close to the top
IN_SHORT_BULLETS = (3, 5)

NOT_YET_CONVERTED = {
    "learn-bases", "learn-candlestick-patterns", "learn-chart-patterns", "learn-fund-earnings",
    "learn-fund-quality", "learn-fund-valuation", "learn-health-breadth", "learn-health-distribution",
    "learn-health-trend", "learn-health-volatility", "learn-macro-calendar", "learn-macro-commodities",
    "learn-macro-currencies", "learn-macro-cycle", "learn-macro-inflation", "learn-macro-liquidity-credit",
    "learn-macro-rates", "learn-macro-yield-curve", "learn-price-indicators", "learn-price-oscillators",
    "learn-price-rs", "learn-price-stages", "learn-price-volume", "learn-process-biases",
    "learn-process-journal", "learn-process-plan", "learn-risk-expectancy", "learn-risk-portfolio",
    "learn-risk-sizing", "learn-risk-stops-exits", "learn-sectors-groups", "learn-start-here",
    "learn-supply-demand", "learn-system-families", "learn-system-filters",
    "learn-system-screens-strategies", "learn-test-backtesting", "learn-test-reading", "learn-vcp",
}

APP_REFERENCES = [
    r"\bthis app\b", r"\bthe app\b", r"\bapp's\b", r"\bin the app\b", r"Where this shows",
    r"\b(Markets|Screens|Strategies|Chart|Watchlists|Library|System|Today)\s*→",
    r"\bthe (Chart|Breadth|Sectors|Screens|Strategies|Today|Post-market|Fundamentals|Quality|Notes|Status|Runs) (page|tab|screen)\b",
    r"\bReports archive\b", r"\bmacro strip\b",
]
CODE_IN_PROSE = [
    r"`[^`]*\.(py|js|json|md)`", r"\b[\w/]+\.(py|js)\b",
    r"`[A-Za-z0-9]+_[A-Za-z0-9_]+`",                 # snake_case / CONSTANT_CASE identifiers
    r"\b(trend_pullback|chart_pattern|minervini_spec|donchian_breakout|series_facts|report_runs|index_series)\b",
]
OWN_BACKTESTS = [r"\brun \d{2,4}\b", r"\bruns? (id|ids)\b", r"\bv\d+\.\d+-[0-9a-f]{6,}\b", r"\bspec[ _]id\b"]
DATE = re.compile(r"\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b|"
                  r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b|\b\d{4}-\d{2}(-\d{2})?\b")
NUMBER = re.compile(r"(?<![\w.])[-−+]?\d[\d,]*(?:\.\d+)?")
LIST_ITEM = re.compile(r"^([-*+]|\d+[.)])\s+")


def _prose(md: str) -> list[str]:
    """Paragraphs of running text: fences, tables, headings, lists and quotes removed."""
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    paras, cur = [], []
    for line in md.splitlines():
        s = line.strip()
        # a block boundary: a blank line, a heading, a table row, a quote, a rule, or a list item ("- ", "* ",
        # "1. ") — but not a paragraph that opens in bold ("**Like this.**") or a wrapped line starting "1.5%"
        if not s or s.startswith(("#", "|", ">")) or s == "---" or LIST_ITEM.match(s):
            if cur:
                paras.append(" ".join(cur))
                cur = []
            continue
        if line[:1] in (" ", "\t") and not cur:     # the continuation of a list item: part of the list, not prose
            continue
        cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    return [re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", p) for p in paras]


def _sentences(text: str) -> list[str]:
    text = re.sub(r"\b(e\.g|i\.e|vs|etc|approx|Dr|Mr|Ms|St|no)\.", r"\1", text)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(*])", text) if len(s.split()) >= 3]


def _numbers(sentence: str) -> int:
    return len(NUMBER.findall(DATE.sub("DATE0", sentence)))


def check_guide(name: str, md: str, guide_files: set[str]) -> list[str]:
    out: list[str] = []
    body = re.sub(r"```.*?```", "", md, flags=re.S)
    body_no_reading = body.split("## Further reading")[0]
    for pat in APP_REFERENCES:
        for m in re.finditer(pat, body_no_reading, flags=re.I):
            out.append(f"refers to the app: {m.group(0)!r}")
    for pat in CODE_IN_PROSE:
        for m in re.finditer(pat, body_no_reading):
            out.append(f"code or file name in prose: {m.group(0)!r}")
    for pat in OWN_BACKTESTS:
        for m in re.finditer(pat, body_no_reading, flags=re.I):
            out.append(f"cites the app's own backtests: {m.group(0)!r}")

    lines = md.splitlines()
    at = next((i for i, l in enumerate(lines[:IN_SHORT_WITHIN_LINES]) if re.match(r"\**In short\**:?\**$", l.strip(), re.I)), None)
    if at is None:
        out.append(f'no "In short" block in the first {IN_SHORT_WITHIN_LINES} lines')
    else:
        bullets = 0
        for l in lines[at + 1:]:
            if LIST_ITEM.match(l):
                bullets += 1
            elif l.strip() and bullets and not l[:1].isspace():
                break
        lo, hi = IN_SHORT_BULLETS
        if not lo <= bullets <= hi:
            out.append(f'"In short" has {bullets} bullets (want {lo}-{hi})')

    lens = []
    for p in _prose(body_no_reading):
        sents = _sentences(p)
        if len(sents) > MAX_PARA_SENTENCES:
            out.append(f"paragraph of {len(sents)} sentences (max {MAX_PARA_SENTENCES}): {p[:70]!r}…")
        for s in sents:
            w = len(s.split())
            lens.append(w)
            if w > MAX_SENTENCE_WORDS:
                out.append(f"sentence of {w} words (max {MAX_SENTENCE_WORDS}): {s[:70]!r}…")
            n = _numbers(s)
            if n > MAX_NUMBERS_PER_SENTENCE:
                out.append(f"{n} numbers in one sentence (max {MAX_NUMBERS_PER_SENTENCE}; use a table): {s[:70]!r}…")
    if lens and statistics.mean(lens) > MAX_AVG_WORDS:
        out.append(f"average sentence {statistics.mean(lens):.1f} words (max {MAX_AVG_WORDS})")

    for target in re.findall(r"\]\((learn-[a-z0-9-]+)\.md\)", md):
        if target not in guide_files:
            out.append(f"links to {target}.md, which does not exist")
    return out


def main() -> int:
    files = {p.stem: p for p in sorted(paths.RESEARCH_DIR.glob("learn-*.md"))}
    failed, legacy_report, clean_but_listed = {}, {}, []
    for name, p in files.items():
        problems = check_guide(name, p.read_text(), set(files))
        if name in NOT_YET_CONVERTED:
            if problems:
                legacy_report[name] = len(problems)
            else:
                clean_but_listed.append(name)
        elif problems:
            failed[name] = problems
    for name in sorted(set(NOT_YET_CONVERTED) - set(files)):
        clean_but_listed.append(f"{name} (no such guide)")

    converted = len(files) - len(set(files) & NOT_YET_CONVERTED)
    print(f"{converted} of {len(files)} guides converted to the standard; "
          f"{len(legacy_report)} still to do ({sum(legacy_report.values())} issues).")
    for name, problems in sorted(failed.items()):
        print(f"\nFAIL {name} — {len(problems)} issue(s):")
        for x in problems[:25]:
            print("   ", x)
        if len(problems) > 25:
            print(f"    ... and {len(problems) - 25} more")
    if clean_but_listed:
        print("\nTake these off NOT_YET_CONVERTED (they pass, or no longer exist):", ", ".join(clean_but_listed))
    if failed or clean_but_listed:
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:          # report one guide in full: `... test_learn_style learn-macro-rates`
        files = {p.stem for p in paths.RESEARCH_DIR.glob("learn-*.md")}
        for n in sys.argv[1:]:
            probs = check_guide(n, (paths.RESEARCH_DIR / f"{n}.md").read_text(), files)
            print(f"{n}: {len(probs)} issue(s)")
            for x in probs:
                print("   ", x)
        sys.exit(0)
    sys.exit(main())
