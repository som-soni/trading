import argparse

import uvicorn

from . import ingest


def main() -> None:
    ap = argparse.ArgumentParser(description="Serve the trading viewer")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-ingest", action="store_true", help="skip loading new reports at startup")
    args = ap.parse_args()
    if not args.no_ingest:
        print("Loading reports:", ingest.ingest())
    uvicorn.run("swing_screener.web.server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
