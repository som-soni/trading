---
name: daily-quiz
description: Give the user today's trading-knowledge quiz, or grade the answers they paste back. A comprehensive, spaced-repetition course across every dimension of trading — live market review, macro, sectors, fundamentals, price action, a broad strategy catalog (far beyond the portal's own), risk and sizing, execution, F&O, testing and statistics, psychology, tax and regulation, market history. Use when the user asks for a quiz, test, "today's test", or pastes answers to one.
argument-hint: "[grade | exam | focus <dimension>] (empty = today's quiz)"
---

# Daily trading quiz

The goal: over months, the user builds a complete theoretical grounding in trading, which they then
solidify with paper and live trading. Each day is one quiz of about 12 questions. The answers are
withheld until the user replies; then every question is graded and every miss is explained, and the
miss comes back on a later day until it is right twice.

Mode: $ARGUMENTS
- empty → write today's quiz (§2).
- `grade`, or the user's message carries answers → grade them (§4).
- `exam` → a 20-question mixed exam over everything covered so far, no new material (every 7th quiz
  is one anyway).
- `focus <dimension>` → today's quiz drawn mostly from that dimension (still with the re-tests).

Work in /Users/admin/Workspace/trading. Read-only: never edit code, queue jobs or commit.

## 1. State — read it first, write it last

The tracker is `/Users/admin/.claude/projects/-Users-admin-Workspace-trading/memory/daily-trading-test.md`:
the user's level per dimension, the **weak-spot queue** (misses still to re-test), the **coverage
grid** (each dimension's last date and recent score), and the day log. Read it before writing or
grading anything. Never reveal its contents as answers.

## 2. Writing today's quiz

The curriculum is [curriculum.md](curriculum.md): 16 dimensions with their topics, and a strategy
catalog. Pick about 12 questions:

| Slot | Count | How to choose |
|---|---|---|
| Re-test | 2–3 | Oldest items in the weak-spot queue, with **new numbers and a new framing** — never the same question. |
| Market review | 1 | Today's real market, from stored data (§3). |
| Chart drill | 1 | A real stock at a real past date, point in time (§3). |
| Risk & maths | 1 | A calculation: R, expectancy, sizing, drawdown, costs, SE, Kelly, risk of ruin. |
| Strategy | 1 | From the catalog, rotating; at least two in three from outside the portal's built strategies. |
| Rotation | 5–6 | The dimensions least recently covered, weighted toward low scores. No dimension twice except re-tests. |

Mix the question types across the day: recall, calculation, scenario/decision ("what do you do now?"),
spot-the-mistake, compare-two, explain-in-your-own-words, and one "teach it" question a week (explain a
concept to a beginner in 3 sentences). At least half should be scenario or calculation — knowing a
definition is not the goal.

**Difficulty** follows the dimension's level in the tracker: L1 definitions and single-step sums; L2
multi-step calculations and standard scenarios; L3 judgement calls with conflicting evidence; L4
design questions ("build the exit rules for…", "what would make this backtest lie?"). Move a dimension
up after two quizzes at ≥ 80% on it, down after two at < 50%.

**Sources.** The Learn guides (`research/learn-*.md`, order in `GUIDE_ORDER` of
`scripts/swing_screener/web/static/app.js`) are the in-portal course: use them for vocabulary and to
stay consistent with what the user has read. Do **not** stop at them: the curriculum is deliberately
wider, so draw also on the standard literature (named books and published research, stated
accurately) and general market knowledge. Rules that change — tax rates, SEBI/F&O rules, lot sizes,
margin rules, settlement cycles — must be checked with a web search before you ask about them; say
"as of <date>". Never treat the portal's own backtest results or strategy `status` texts as proven
facts: those strategies are still being refined.

**Format** (the user pastes the quiz back with answers written under each question, so keep it
paste-friendly):

```
# Day N: <theme of the day>            (Exam if it is one)
<one line: which dimensions today, and which re-tests>

**Part A: Today's market**   — Q1 market review, Q2 chart drill
**Part B: <rotation themes>** — numbered questions
**Part C: Re-test**           — say which earlier miss each re-tests

Answer under each question; "I don't know" is fine.
```

Every question is self-contained: give all numbers needed, units (₹ / $), and for multiple choice say
"pick one" or "pick all that are true". Use Indian and US examples about equally. No answers, hints or
worked steps in the quiz.

Append the day to the tracker's log as "issued, awaiting answers", with the question topics.

## 3. Live questions from the stored data

The web app runs at http://localhost:8000 and only reads stored data. Useful reads (GET):

- `/api/markets` — market keys; `/api/market-snapshot?market=<m>` (optional `&date=`) — the daily
  review's readings: index vs averages, slopes, ratios, distance from highs;
- `/api/breadth?market=<m>`, `/api/breadth-series`, `/api/sectors?market=<m>&level=sector`,
  `/api/macro?market=<m>` — breadth, sector leadership, rates/dollar/oil/credit;
- `/api/prices?market=<m>&symbol=<s>&tf=D&bars=300` — daily bars for a chart drill. The symbol carries
  the market's ticker suffix from `/api/markets` (`RELIANCE.NS`, `AAPL`).

**Market review question:** give the user 4–8 real readings from the latest session (state the date)
and ask for a judgement: the regime (uptrend / correction / bear / transition), what the readings
disagree on, what would change their mind, and how exposure should differ. Grade the reasoning, not a
"right" forecast — there is no single answer; say what the standard frameworks (trend, breadth,
volatility, distribution) each point to.

**Chart drill:** pick a liquid stock and a past date with something worth reading (a base, a breakout,
a failed breakout, a stage change, a gap, a climax). Describe the bars up to that date only — trend vs
50/200-day, the pattern, volume, relative strength, the nearest levels — or give a short OHLCV table.
Ask what they see and what they would do (entry, stop, size, or stand aside). When grading, reveal what
happened next and why that outcome does not by itself prove the decision right or wrong.

These are learning exercises, not recommendations: never frame a live question as "should you buy X
now", and do not give personalised investment advice.

If the server is down, use the database read-only (`scripts/swing_screener/marketdata/db.py`) with a
scratchpad script, or fall back to a web search for the market facts and say so.

## 4. Grading

When the user replies with answers:

1. Score each question ✓ (1), ½ or ✗ (0). Be strict on numbers, generous on wording; credit correct
   reasoning with an arithmetic slip as ½.
2. Start with a score table (question, topic, result), then one line on what improved since the last
   quiz and what is still weak.
3. For each ½ or ✗: the right answer first, then the reasoning **intuition first, then the formula,
   then a worked example with the question's numbers**. For anything missed twice, slow down further:
   a fresh analogy and a second worked example. For ✓ answers, one line, adding the nuance they missed
   if any.
4. Give the reveal for the chart drill and the frameworks' read for the market review.
5. Close with what the next quiz will cover (dimensions and re-tests).

Then update the tracker:
- the day's score and a one-line summary;
- each miss → weak-spot queue (concept, how it was got wrong, date); an item leaves the queue after two
  correct re-tests on different days;
- the coverage grid (date, score per dimension) and any level change.

If the user asks for an explanation of a concept between quizzes (as in "explain how R works"), teach
it with one running scenario, and add the concept to the next quiz's re-tests.

## 5. Beyond the quiz

Once a week (on the exam day), add one **practice task** that bridges to real trading, taken from what
they got wrong: e.g. journal the next five paper trades in R; size three real setups from today's
screen with the formula; write their market-regime call each day this week and compare with what
followed; read one company's results and fill in the growth and margin numbers. Note it in the tracker
and ask about it in the next quiz.
