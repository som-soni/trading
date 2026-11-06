"""Zerodha Kite Connect, read-only: your holdings and cash, to start the rebalance account from.

READ-ONLY by construction. The only calls are the login exchange and four GETs (holdings, positions,
equity margins, and the OHLC quote a watchlist's "Pull LTP" asks for); there is no order endpoint in this
module, so the portal cannot trade through it.

Setup, once:
  1. Create a Kite Connect app at developers.kite.trade. Set its redirect URL to
     http://localhost:8000/api/broker/kite/callback
  2. Put its key and secret in scripts/.env (gitignored), never in the code:
        KITE_API_KEY=...
        KITE_API_SECRET=...
  3. Restart the web server.

Each day you use it: "Log in to Kite" on the strategy's Holdings tab opens Zerodha's own login page
(your password goes to Zerodha, never to this app); Zerodha redirects back with a request token, which
is exchanged here for an access token. Kite expires every access token at 06:00 IST the next morning, so
the stored session (`broker_sessions`) is treated as gone after that.

What a sync returns is a DRAFT for the account form, not a saved account: your Zerodha account may hold
stocks that are not part of the strategy, and those are yours to remove before saving.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, time, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests

from ..marketdata import db

API = "https://api.kite.trade"
LOGIN = "https://kite.zerodha.com/connect/login"
IST = ZoneInfo("Asia/Kolkata")
TOKEN_RESET = time(6, 0)   # Kite invalidates every access token at 06:00 IST
TIMEOUT = 15
QUOTE_MAX = 1000           # instruments Kite accepts in one quote call

SCHEMA = """
CREATE TABLE IF NOT EXISTS broker_sessions (
    broker TEXT PRIMARY KEY,           -- "kite"
    user_id TEXT,
    user_name TEXT,
    access_token TEXT NOT NULL,        -- valid until the broker's daily reset; never logged
    login_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


class KiteError(RuntimeError):
    pass


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _keys() -> tuple[str, str]:
    return os.environ.get("KITE_API_KEY", "").strip(), os.environ.get("KITE_API_SECRET", "").strip()


def configured() -> bool:
    key, secret = _keys()
    return bool(key and secret)


def login_url(next_hash: str = "") -> str:
    """Zerodha's own login page for this app. `next_hash` (a portal route) comes back on the callback
    through Kite's redirect_params, so the login returns you to the page you started from."""
    key, _ = _keys()
    if not key:
        raise KiteError("KITE_API_KEY is not set: add it to scripts/.env and restart the server")
    q = {"v": 3, "api_key": key}
    if next_hash:
        q["redirect_params"] = urlencode({"next": next_hash})
    return f"{LOGIN}?{urlencode(q)}"


def _last_reset(now: datetime) -> datetime:
    now = now.astimezone(IST)
    reset = datetime.combine(now.date(), TOKEN_RESET, IST)
    return reset if now >= reset else reset - timedelta(days=1)


def session(now: datetime | None = None) -> dict | None:
    """The stored session if it is still valid (made after the last 06:00 IST reset), else None."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT user_id, user_name, access_token, login_at FROM broker_sessions WHERE broker='kite'")
        r = cur.fetchone()
    if not r or r[3] < _last_reset(now or datetime.now(IST)):
        return None
    return {"user_id": r[0], "user_name": r[1], "access_token": r[2], "login_at": r[3]}


def complete_login(request_token: str) -> dict:
    """Exchange the request token from Zerodha's redirect for an access token, and store it."""
    key, secret = _keys()
    if not (key and secret):
        raise KiteError("KITE_API_KEY / KITE_API_SECRET are not set in scripts/.env")
    checksum = hashlib.sha256((key + request_token + secret).encode()).hexdigest()
    r = requests.post(f"{API}/session/token", timeout=TIMEOUT, headers={"X-Kite-Version": "3"},
                      data={"api_key": key, "request_token": request_token, "checksum": checksum})
    body = _json(r)
    d = body["data"]
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO broker_sessions (broker, user_id, user_name, access_token, login_at)
                       VALUES ('kite', %s, %s, %s, now())
                       ON CONFLICT (broker) DO UPDATE SET user_id=EXCLUDED.user_id, user_name=EXCLUDED.user_name,
                         access_token=EXCLUDED.access_token, login_at=now()""",
                    (d.get("user_id"), d.get("user_name"), d["access_token"]))
    return {"user_id": d.get("user_id"), "user_name": d.get("user_name")}


def logout() -> None:
    """Forget the stored session here. (Kite also expires it at the next 06:00 IST.)"""
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM broker_sessions WHERE broker='kite'")


def _json(r: requests.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        raise KiteError(f"Kite answered HTTP {r.status_code} with no JSON")
    if r.status_code != 200 or body.get("status") != "success":
        if body.get("error_type") == "TokenException":
            logout()
            raise KiteError("The Kite session has expired: log in again")
        raise KiteError(f"Kite: {body.get('message') or body.get('error_type') or r.status_code}")
    return body


def _get(path: str, token: str, params: list | None = None) -> object:
    key, _ = _keys()
    r = requests.get(f"{API}{path}", timeout=TIMEOUT, params=params,
                     headers={"X-Kite-Version": "3", "Authorization": f"token {key}:{token}"})
    return _json(r)["data"]


def account(suffix: str) -> dict:
    """Your Zerodha holdings and available cash, as a draft for the rebalance account.

    shares = settled quantity + T1 (bought, not yet delivered). Shares bought or sold TODAY are not in
    holdings yet: they are listed under `today` with a warning rather than guessed at, so a sync on a
    day you traded says so instead of silently miscounting. `suffix` is the market's ticker suffix
    (".NS"), so a Kite trading symbol reads as the stored symbol.
    """
    s = session()
    if not s:
        raise KiteError("Not logged in to Kite (or the session expired at 06:00 IST): log in first")
    tok = s["access_token"]
    holdings = _get("/portfolio/holdings", tok) or []
    positions = (_get("/portfolio/positions", tok) or {}).get("net", [])
    margins = _get("/user/margins/equity", tok) or {}

    shares, detail, warnings = {}, [], []
    for h in holdings:
        n = float(h.get("quantity") or 0) + float(h.get("t1_quantity") or 0)
        sym = str(h.get("tradingsymbol", "")).upper()
        if n <= 0 or not sym:
            continue
        shares[sym + suffix] = shares.get(sym + suffix, 0.0) + n
        detail.append({"symbol": sym, "exchange": h.get("exchange"), "shares": n,
                       "t1": float(h.get("t1_quantity") or 0), "avg_price": h.get("average_price"),
                       "last_price": h.get("last_price")})
        if float(h.get("used_quantity") or 0) > 0:
            warnings.append(f"{sym}: {h['used_quantity']:g} sold today; holdings may still count them")
    today = [{"symbol": str(p.get("tradingsymbol", "")).upper(), "product": p.get("product"),
              "quantity": p.get("quantity")}
             for p in positions if p.get("product") == "CNC" and float(p.get("quantity") or 0) != 0]
    if today:
        warnings.append("Today's delivery trades are not in holdings until tomorrow: "
                        + ", ".join(f"{t['symbol']} {float(t['quantity']):+g}" for t in today)
                        + ". Adjust those lines by hand, or sync again tomorrow.")
    if any(p.get("product") in ("MIS", "NRML") and float(p.get("quantity") or 0) != 0 for p in positions):
        warnings.append("You hold intraday or F&O positions; they are not part of this account and are left out.")
    cash = float(margins.get("net") or 0.0)
    return {"user_id": s["user_id"], "user_name": s["user_name"], "positions": shares, "cash": cash,
            "cash_note": "Kite's available equity margin ('net'): set it to the cash you run this strategy with.",
            "holdings": detail, "today": today, "warnings": warnings,
            "fetched_at": datetime.now(IST).isoformat(timespec="seconds")}


def quotes(symbols: list[str], suffix: str, exchange: str) -> dict:
    """The last traded price and the previous session's close for stored symbols ("RELIANCE.NS"), from
    Kite's OHLC quote (GET /quote/ohlc). A snapshot when asked, not a feed: nothing is stored, and no
    screen or backtest reads it. Kite's `ohlc.close` is the previous session's close; `ohlc` also carries
    today's open, high and low. A symbol Kite does not know is left out of the answer. Kite serves quotes
    only on a Connect plan with market data: without one it answers with a permission error, raised here.
    """
    s = session()
    if not s:
        raise KiteError("Not logged in to Kite (or the session expired at 06:00 IST): log in first")
    by_inst = {f"{exchange}:{sym[:-len(suffix)] if suffix and sym.endswith(suffix) else sym}": sym for sym in symbols}
    insts, out = list(by_inst), {}
    for i in range(0, len(insts), QUOTE_MAX):
        data = _get("/quote/ohlc", s["access_token"], [("i", x) for x in insts[i:i + QUOTE_MAX]]) or {}
        for inst, d in data.items():
            sym, ltp, prev = by_inst.get(inst), d.get("last_price"), (d.get("ohlc") or {}).get("close")
            if sym is None or ltp is None:
                continue
            o = d.get("ohlc") or {}
            out[sym] = {"ltp": ltp, "prev_close": prev, "open": o.get("open"), "high": o.get("high"), "low": o.get("low"),
                        "change_pct": (ltp / prev - 1) * 100 if prev else None}
    return {"quotes": out, "missing": sorted(set(symbols) - set(out)),
            "fetched_at": datetime.now(IST).isoformat(timespec="seconds")}
