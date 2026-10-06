"""Long-term investing: track fundamentally strong companies and buy them at
the right price.

Deliberately a separate package from `swing_screener` (swing trading): it fetches
annual statements, scores business quality, and judges whether today's price is
attractive. It shares only infrastructure — the price database in
`swing_screener.marketdata` — and is viewed through the same web app. See
`quality.py`.

    PYTHONPATH=. python3 -m fundamentals.quality --market us --top 500
"""
