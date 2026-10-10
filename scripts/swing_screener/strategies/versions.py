"""Enforce that changing a strategy's rules requires a version bump.

Version metadata nobody updates is worse than none, because it reads as a
guarantee and isn't one. So the version is checked against a lock file rather
than trusted: `versions.lock.json` records each strategy's version alongside a
fingerprint of its tunables, and `--check` fails when a fingerprint has moved
while the version stayed put.

This exists because of a specific failure. Minervini's `VCP_TIGHT_PCT` was
changed from 12% to 10% in place; every backtest run before that point became
irreproducible, and nothing anywhere recorded that the rules had moved. The
numbers in the research ledger silently stopped describing the code.

    PYTHONPATH=. python3 -m swing_screener.strategies.versions            # status
    PYTHONPATH=. python3 -m swing_screener.strategies.versions --check    # CI gate
    PYTHONPATH=. python3 -m swing_screener.strategies.versions --update   # after a deliberate bump

Typical cycle: change a threshold, run `--check`, be told to bump, raise
`version` and add a `changelog` entry saying what moved and why, then
`--update` to record the new state.
"""

import argparse
import json
import sys
from pathlib import Path

from . import _REGISTRY, all_specs

def _vkey(v: str) -> tuple:
    """Sort versions numerically, so 10.0 follows 9.0 rather than 1.0."""
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


LOCK_PATH = Path(__file__).resolve().parent / "versions.lock.json"


def current_state() -> dict:
    out = {}
    for key, cls in sorted(all_specs().items()):
        out[key] = {
            "family": cls.family_name(),
            "version": cls.version,
            "fingerprint": cls.fingerprint(),
            "params": {k: v for k, v in sorted(cls.spec_params().items())},
        }
    return out


def load_lock() -> dict:
    if not LOCK_PATH.exists():
        return {}
    return json.loads(LOCK_PATH.read_text())


def save_lock(state: dict) -> None:
    LOCK_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _param_diff(old: dict, new: dict) -> list[str]:
    lines = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k, "—"), new.get(k, "—")
        if a != b:
            lines.append(f"      {k}: {a} -> {b}")
    return lines


def verify(key: str) -> str | None:
    """None when one strategy's rules match what the lock file records for its
    version; otherwise an explanation of what moved.

    The backtest calls this before it runs. A run whose rules are not the
    recorded ones cannot be attributed to a version afterwards: the report
    directory would say v1.0 while the code had quietly become something else,
    which is the exact failure the lock file exists to prevent.
    """
    cls = all_specs().get(key)
    if cls is None:
        return None
    fp, was = cls.fingerprint(), load_lock().get(key)
    if was is None:
        return (f"{key} is not recorded in {LOCK_PATH.name} (rules fingerprint {fp}).")
    if was["fingerprint"] == fp and was["version"] == cls.version:
        return None
    what = (f"version v{was['version']} -> v{cls.version}"
            if was["version"] != cls.version else f"version stayed v{cls.version}")
    diff = _param_diff(was.get("params", {}), cls.spec_params())
    return (f"{key}: the code's rules are not the ones recorded for this version "
            f"({was['fingerprint']} -> {fp}, {what})."
            + ("\n    What moved:\n" + "\n".join(diff) if diff else ""))


def check() -> tuple[list[str], list[str]]:
    """Returns (problems, notes). A problem fails the check; a note does not."""
    lock, now = load_lock(), current_state()
    problems: list[str] = []
    notes: list[str] = []

    for key, cur in now.items():
        was = lock.get(key)
        if was is None:
            notes.append(f"  NEW   {key} ({cur['family']} {cur['version']}, "
                         f"{cur['fingerprint']}) — not yet locked")
            continue
        same_fp = was["fingerprint"] == cur["fingerprint"]
        same_ver = was["version"] == cur["version"]
        if same_fp and same_ver:
            continue
        if not same_fp and same_ver:
            problems.append(
                f"  {key}: rules changed but version is still {cur['version']} "
                f"({was['fingerprint']} -> {cur['fingerprint']}).\n"
                f"    Bump `version`, add a `changelog` entry, then re-run with "
                f"--update. Changed:\n"
                + "\n".join(_param_diff(was.get("params", {}), cur["params"]))
            )
        elif not same_ver and same_fp:
            notes.append(f"  {key}: version {was['version']} -> {cur['version']} "
                         f"with identical rules (documentation-only bump)")
        else:
            cls = all_specs()[key]
            logged = any(e[0] == cur["version"] for e in cls.changelog)
            msg = (f"  OK    {key}: {was['version']} -> {cur['version']}, "
                   f"rules changed as expected")
            if not logged:
                problems.append(
                    f"  {key}: bumped to {cur['version']} but `changelog` has no "
                    f"entry for it — record what changed and why.")
            else:
                notes.append(msg)

    for key in lock:
        if key not in now:
            notes.append(f"  GONE  {key} is in the lock file but no longer registered")
    return problems, notes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if a rule set changed without a version bump")
    ap.add_argument("--update", action="store_true",
                    help="record the current versions and fingerprints")
    args = ap.parse_args()

    if args.update:
        state = current_state()
        save_lock(state)
        print(f"Locked {len(state)} strategies -> {LOCK_PATH.name}")
        for k, v in state.items():
            print(f"  {k:20} {v['family']:16} v{v['version']}-{v['fingerprint']}")
        return

    problems, notes = check()
    for n in notes:
        print(n)
    if problems:
        print("\nVERSION CHECK FAILED:\n")
        for p in problems:
            print(p)
            print()
        if args.check:
            sys.exit(1)
        return
    if args.check:
        print("\nVersion check passed — every rule set matches its recorded version.")
    else:
        now = current_state()
        print(f"\n{len(now)} strategies, by family:")
        fams: dict[str, list] = {}
        for k, v in now.items():
            fams.setdefault(v["family"], []).append((k, v))
        for fam, members in sorted(fams.items()):
            # newest version first, and mark it: with several versions in a
            # family the question is always "which one is current", and
            # marking the key that matches the family name answers a
            # different, less useful question
            members.sort(key=lambda kv: _vkey(kv[1]["version"]), reverse=True)
            latest = members[0][1]["version"] if members else None
            print(f"  {fam}")
            for k, v in members:
                variant = all_specs()[k].variant_of
                mark = "*" if v["version"] == latest and not variant else " "
                tag = f"  (variant of {variant})" if variant else ""
                print(f"   {mark} {k:22} v{v['version']}-{v['fingerprint']}  "
                      f"({len(v['params'])} params){tag}")
        print("\n  * = current version of its family")


if __name__ == "__main__":
    main()
