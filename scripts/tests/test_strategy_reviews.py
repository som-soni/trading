"""The review tracker reads the skill's version and refuses verdict values outside the skill's vocabulary.
No database.

    PYTHONPATH=. .venv/bin/python -m tests.test_strategy_reviews
"""

import sys

from swing_screener.backtesting import strategy_reviews as sr

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def refuses(verdicts: dict) -> bool:
    try:
        sr._check_verdicts(verdicts)
    except ValueError:
        return True
    return False


def main() -> int:
    v = sr.skill_version()
    check("SKILL.md carries a 'Skill version: N' line", isinstance(v, int) and v >= 1, v)
    text = sr.SKILL_MD.read_text()
    check("the skill's changelog has an entry for its current version", f"- **{v}** (" in text)
    check("a valid verdict passes", not refuses({"us": {"code": "clean", "edge": "small", "robust": "fragile",
                                                         "vs_buy_hold": "matches with less risk"}}))
    check("an unknown market is refused", refuses({"mars": {"code": "clean"}}))
    check("an unknown verdict key is refused", refuses({"us": {"vibe": "good"}}))
    check("a value outside the vocabulary is refused", refuses({"us": {"robust": "pretty robust"}}))
    print(f"\n{'OK — the tracker speaks the skill’s vocabulary.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
