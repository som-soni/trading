"""Stock analysis: one framework for analysing a company, and the analyses made with it.

A FRAMEWORK (`framework.py`) is a fixed list of pillars — business, growth, profitability, financial
health, earnings quality, expectations, ownership, valuation, trend and risk — each asking a few
questions. Some questions the stored data answers (CHECKS: a rule with its thresholds as module
constants, graded good / ok / bad); the rest only you can answer (QUESTIONS: you rate them and write
why). A verdict closes it: your decision, conviction, thesis and what would prove it wrong.

AN ANALYSIS (`store.py`) is one stock read through the framework on one day: the evidence as it stood
(frozen, so a later re-read does not rewrite what you saw), your answers and your verdict. A stock keeps
every analysis made of it, so you can see how your view — and the evidence — moved.

`evidence.py` gathers the stored data a check reads (the Fundamentals page's tables, the day's stock
snapshot, the Quality page's scores, analysts' estimates) — it never downloads. The web app's
Chart › Analysis tab shows it.

    PYTHONPATH=. python3 -m analysis --market us --symbol NVDA
    PYTHONPATH=. python3 -m analysis --framework

Not investment advice: the checks are screening rules of thumb over filings that can be restated.
"""
