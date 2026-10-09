"""The Screen type: named qualification criteria, evaluated per stock, plus a shared tradability floor."""

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

MIN_BARS = 260             # history a stock needs before any screen considers it


@dataclass(frozen=True)
class Criterion:
    code: str
    fn: Callable          # (StockContext) -> (passed: bool, note: str)
    doc: str              # plain-language rule; {NAME} placeholders are constants of screens/criteria.py


@dataclass
class ScreenResult:
    passed: bool
    results: dict[str, bool] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)
    first_fail: str | None = None


@dataclass(frozen=True)
class Screen:
    key: str
    name: str
    description: str
    thesis: str
    criteria: tuple[Criterion, ...]
    rank_rs: bool = False   # C8-style criterion is replaced by the cross-sectional RS rank when a whole market is screened

    def criterion(self, code: str) -> Callable:
        return next(c.fn for c in self.criteria if c.code == code)

    @staticmethod
    def tradable(cfg, last) -> tuple[bool, str]:
        """The floor every screen applies first: the market's minimum price and liquidity, and a usable ATR."""
        if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
            return False, f"price below {cfg.screener.min_price:g}"
        if cfg.screener.min_dollar_volume:
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, ""

    def evaluate(self, ctx) -> ScreenResult:
        res = ScreenResult(passed=True)
        for c in self.criteria:
            ok, note = c.fn(ctx)
            res.results[c.code] = bool(ok)
            if note:
                res.notes[c.code] = note
            if not ok and res.first_fail is None:
                res.first_fail = c.code
        res.passed = res.first_fail is None
        return res

    def docs(self) -> list[dict]:
        from . import criteria as cmod
        ns = {k: v for k, v in vars(cmod).items() if k.isupper()}
        return [{"code": c.code, "text": c.doc.format(**ns)} for c in self.criteria]
