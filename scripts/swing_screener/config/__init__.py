from .base import MarketConfig
from .us import US_CONFIG
from .india import INDIA_CONFIG

MARKETS = {
    "us": US_CONFIG,
    "india": INDIA_CONFIG,
}

__all__ = ["MarketConfig", "US_CONFIG", "INDIA_CONFIG", "MARKETS"]
