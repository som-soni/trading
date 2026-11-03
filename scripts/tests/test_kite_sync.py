"""The Kite account read: holdings and cash become a draft rebalance account, and nothing can trade.

`broker/kite.py` is checked against canned Kite Connect responses -- no network, no account, no
database (the stored session is stubbed). It must: count settled + T1 shares; add the market's ticker
suffix; flag today's delivery trades and shares sold today instead of guessing at them; leave intraday /
F&O positions out; read cash from the equity margin; expire a session at 06:00 IST; and contain no order
endpoint at all, so the portal cannot place a trade through it.

    PYTHONPATH=. .venv/bin/python -m tests.test_kite_sync
"""

import inspect
import os
import sys
from datetime import datetime

from swing_screener.broker import kite

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


class FakeResponse:
    def __init__(self, data, status=200):
        self.status_code, self._data = status, data

    def json(self):
        return self._data


HOLDINGS = [
    {"tradingsymbol": "LAURUSLABS", "exchange": "NSE", "quantity": 24, "t1_quantity": 0, "used_quantity": 0,
     "average_price": 2100.5, "last_price": 2348.0},
    {"tradingsymbol": "SBC", "exchange": "NSE", "quantity": 500, "t1_quantity": 239, "used_quantity": 0,
     "average_price": 60.1, "last_price": 65.34},
    {"tradingsymbol": "TATASTEEL", "exchange": "BSE", "quantity": 300, "t1_quantity": 0, "used_quantity": 100,
     "average_price": 150.0, "last_price": 177.37},
    {"tradingsymbol": "GONE", "exchange": "NSE", "quantity": 0, "t1_quantity": 0, "used_quantity": 0},
]
POSITIONS = {"net": [
    {"tradingsymbol": "AETHER", "product": "CNC", "quantity": 28},
    {"tradingsymbol": "NIFTY26NOVFUT", "product": "NRML", "quantity": 75},
    {"tradingsymbol": "FLAT", "product": "CNC", "quantity": 0},
]}
MARGINS = {"enabled": True, "net": 500000.75, "available": {"cash": 480000.0, "live_balance": 500000.75}}


def fake_get(url, timeout=None, headers=None):
    fake_get.calls.append((url, headers))
    path = url.split("api.kite.trade", 1)[1]
    data = {"/portfolio/holdings": HOLDINGS, "/portfolio/positions": POSITIONS, "/user/margins/equity": MARGINS}[path]
    return FakeResponse({"status": "success", "data": data})


fake_get.calls = []


def main() -> None:
    os.environ["KITE_API_KEY"], os.environ["KITE_API_SECRET"] = "testkey", "testsecret"
    kite.session = lambda now=None: {"user_id": "AB1234", "user_name": "Test", "access_token": "tok"}
    kite.requests.get = fake_get

    print("account(): holdings and cash as a draft")
    a = kite.account(".NS")
    check("settled + T1 shares counted", a["positions"].get("SBC.NS") == 739, a["positions"])
    check("ticker suffix added", set(a["positions"]) == {"LAURUSLABS.NS", "SBC.NS", "TATASTEEL.NS"}, a["positions"])
    check("a zero holding is left out", "GONE.NS" not in a["positions"])
    check("cash is the equity margin's net", a["cash"] == 500000.75, a["cash"])
    check("today's delivery buy is flagged, not added", "AETHER.NS" not in a["positions"]
          and any("AETHER +28" in w for w in a["warnings"]), a["warnings"])
    check("shares sold today are flagged", any(w.startswith("TATASTEEL") for w in a["warnings"]), a["warnings"])
    check("F&O positions are left out, with a note", "NIFTY26NOVFUT.NS" not in a["positions"]
          and any("F&O" in w for w in a["warnings"]), a["warnings"])
    check("auth header carries key:token", all(h.get("Authorization") == "token testkey:tok" for _, h in fake_get.calls))

    print("read-only by construction")
    src = inspect.getsource(kite)
    check("no order endpoint in the module", "/orders" not in src and "place_order" not in src)
    check("only GETs after login", src.count("requests.post(") == 1 and "requests.put(" not in src
          and "requests.delete(" not in src)

    print("session expiry at 06:00 IST")
    reset = kite._last_reset(datetime(2026, 11, 3, 5, 59, tzinfo=kite.IST))
    check("before 06:00 the reset is yesterday's", reset == datetime(2026, 11, 2, 6, 0, tzinfo=kite.IST), reset)
    reset = kite._last_reset(datetime(2026, 11, 3, 6, 0, tzinfo=kite.IST))
    check("from 06:00 the reset is today's", reset == datetime(2026, 11, 3, 6, 0, tzinfo=kite.IST), reset)

    print("login URL")
    u = kite.login_url("#/strategies/momentum_vol_scaled/holdings")
    check("Zerodha's page, this app's key", u.startswith(kite.LOGIN) and "api_key=testkey" in u, u)
    check("the return route rides in redirect_params", "redirect_params=next%3D" in u, u)

    print("errors")
    kite.requests.get = lambda *a, **k: FakeResponse({"status": "error", "error_type": "TokenException",
                                                      "message": "expired"}, 403)
    kite.logout = lambda: None
    try:
        kite.account(".NS")
        check("an expired token raises", False)
    except kite.KiteError as e:
        check("an expired token asks for a new login", "log in again" in str(e), str(e))

    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'OK — Kite sync reads holdings and cannot trade'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
