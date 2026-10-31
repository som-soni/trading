---
name: sunday-review
description: Weekly deep review of the trading repo (code, web UI, jobs, data, backtests, docs, tests) that ranks verified fixes and the gaps worth filling — missing tests, evals and features. Run on Sunday with a large token budget.
disable-model-invocation: true
---

# Sunday review

Run a thorough, read-only review of this repository and write a ranked report of verified
fixes and gaps. This is the week's large token budget, so prefer breadth and verification over
speed: many parallel reviewers, each finding checked against the source before it is reported.

The user invoking this skill is the opt-in for a multi-agent workflow. Load the
`workflow-authoring` skill and run the review as a Workflow (phases below). Use up to about 16
reviewer agents plus one verifier per finding. If the Workflow tool is not available, run the
same dimensions as parallel `Agent` calls instead.

Read `CLAUDE.md` first. Its rules are the review standard for every dimension.

## Ground rules (every agent gets these)

- **Read only.** Do not edit or create files in the repo, except the report at the end. Do not
  run `git add`, `commit`, `checkout`, `stash` or `reset`: other sessions share this checkout.
- **No side effects.** No `jobs enqueue`, no `jobs run`, no downloads, no POST, PUT or DELETE
  to the web server. Read-only `SELECT`s against Postgres are fine. Never run a `verify` stage
  backtest: a verify run spends that version's one hold-out.
- **macOS.** There is no `timeout` command. Run long commands in the background.
- **Evidence.** Every finding names `file:line`, what is wrong, a concrete failing input and the
  wrong output, and a one-line fix. Mark it CONFIRMED (both sides of the code path read, or
  reproduced) or PLAUSIBLE. Skip style nits unless they break a `CLAUDE.md` rule.

## Phase 1: inventory (do this yourself, before fanning out)

1. `git log --since="8 days ago" --stat` and `git status`. List what changed this week and what
   is uncommitted. New and changed code gets the closest review.
2. Read the newest `REVIEW-*.md` in the repo root. Its open items are the baseline: each one is
   either fixed, still open or regressed this week.
3. Read `TODO.md`. Its unchecked items are candidate functionality gaps.
4. Run every test, in the background, from `scripts/`, logging each module separately:

   ```bash
   for t in $(ls tests/test_*.py | sed 's#tests/##; s#\.py##'); do PYTHONPATH=. .venv/bin/python -m tests.$t > LOG_$t 2>&1; echo "$t exit=$?"; done
   ```

   Also run `tests.golden_strategies --check` and `tests.test_backtest_stages --all`. Write the
   logs to the scratchpad, not the repo.
5. **Golden check failures need attribution, not a re-record.** The check prints only its first
   80 differences, so count field differences from the JSON instead of the printed lines. To
   find which commit moved a strategy, export the commit's parent with `git archive <sha>
   scripts | tar -x -C <scratch dir>`. Symlink `data/` into the export, copy `scripts/.env` with
   `command cp -f` (plain `cp` prompts here), and copy in the current baseline JSON. Then run the
   check there. Delete the export afterwards, because it holds the database password.

## Phase 2: parallel review dimensions

Give each reviewer its scope, the ground rules and the inventory's list of this week's changes.
Ask each reviewer for at most about 15 findings, ranked.

1. **This week's diff.** Correctness of every commit and uncommitted change since the last review.
   Check field names end to end (loader, server, JavaScript), empty and fresh-database paths, and
   every `CLAUDE.md` rule the change touches.
2. **Backtest engines.** Look-ahead (deciding and filling on the same close), stage-boundary
   reads past `asof.end()`, survivorship, off-by-one on signal and fill days, sizing, costs, P&L
   on resizes and partial exits, NaN handling in rankings and filters.
3. **Strategies.** Docs match behaviour (`gate_docs`, `setup_docs`, `exit_rules`, `status`
   naming its stage), version and changelog bumps, `signal_exempt_consts`, `signal_version`
   pins. Look for setups that can never fire or never pass their own rules: run a setup's plan
   path on real symbols where it fires.
4. **Screens and the stock analysis framework.** Predicates restated instead of reused, bare
   thresholds, point-in-time correctness of snapshot fields, screen-study biases, check
   thresholds as `{NAME}` placeholders, framework `VERSION` bumps.
5. **Jobs and the queue.** Layer violations (downloads outside `marketdata/`), queue tables
   touched outside `jobs/queue.py`, missing `after` dependencies, lanes, failures swallowed or
   recorded as success, non-atomic delete-then-insert, schedules that can overlap, secrets
   logged or written.
6. **Data layer and loaders.** Freshness, holiday and stray rows, splits and corporate actions,
   timezone handling between markets, caches not keyed by asof or constants, silent
   `except Exception`.
7. **Web server.** 500s on bad input (probe with `curl` GETs only), hard-coded markets, slow
   endpoints (time the cold path), work on the request thread, connection handling, unbounded
   scans, GETs with side effects, write endpoints without `_require_local`.
8. **Web client code.** Stale-async races (`alive()` after `await`), unhandled rejections,
   cleanup chains, XSS (`esc()`), hard-coded markets and currencies, duplicated helpers, the
   longest functions and the natural file seams.
9. **UI walk-through in the browser.** Start the `trading-web` preview. Visit every top-level
   page and its sub-tabs at desktop size and at 375 px wide. For each page note time to first
   content, console errors, failed requests, horizontal overflow, colour-only signals, controls
   with no keyboard path and empty or confusing states. Take screenshots of the problems.
10. **Fundamentals, estimates and the company page.** Sources, point-in-time use of filings,
    analyst estimate handling, the page's numbers against the stored data for a few stocks in
    each market.
11. **Learn guides and the app manual.** Registration in the three `app.js` maps and `learn.js`,
    the style test, stand-alone rules (no app names, no backtest citations), claims that the
    stored data can check, and app-guide pages that no longer match the app.
12. **Security and operations.** Secrets in files, logs or plists. The server's bind address.
    File permissions on `.env`. Disk use of the signal cache and logs. Backups of Postgres.
13. **Test gaps.** For each `CLAUDE.md` rule, is there a test that fails when it is broken? List
    rules with no test, tests that can pass while proving nothing (empty samples, unexercised
    branches) and the cheapest test that would close each gap.
14. **Evals: does the research answer what it claims?** Which strategies have no verify run, no
    pre-stated pass criteria, or a `status` that quotes an in-sample figure as a verdict. Which
    screens have no screen study. Whether paper trading or forward tracking exists for any
    strategy. Propose the evaluations worth adding, each with its pass criteria.
15. **Functionality gaps.** From `TODO.md`, the review's open items and a trader's daily
    workflow (Today → Market → Screens → Strategies → Chart → Watchlists), what is missing or
    awkward. Rank by how directly it feeds a trading decision.

## Phase 3: verify each finding

Send each finding to a fresh verifier that gets the code location, not the reviewer's reasoning.
The verifier reads the code path or reproduces the failure and returns CONFIRMED, PLAUSIBLE or
REJECTED with one line of evidence. Drop REJECTED findings. Merge duplicates found by more than
one reviewer.

## Phase 4: the report

Write `REVIEW-<today's ISO date>.md` in the repo root. Keep it skimmable:

1. **Verdict in short:** 3–5 bullets.
2. **Since last review:** a table of last week's open items, each fixed, open or regressed.
3. **Test suite:** each failing test with its cause, and golden differences attributed to commits.
4. **Fix now:** confirmed bugs, ranked by impact on a trading decision or a backtest result.
5. **UI and performance:** what a user feels, with the measured timings.
6. **Gaps:** missing tests, missing evals, and missing functionality, as three short lists, each
   item with its cheapest next step.
7. **Suggested order:** the next five pieces of work, each sized (minutes, an afternoon, a sprint).

Every item gets `file:line` and its CONFIRMED or PLAUSIBLE mark. Do not commit the report.

## Phase 5: hand-off

Tell the user the verdict in a few sentences and link the report. For each self-contained group
of fixes in the suggested order, propose a session with `start_session` (initiation
`own_initiative`, its own worktree, a brief naming the files and what done looks like). Fix
nothing in this session unless the user asks.
