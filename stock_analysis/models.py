from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Signal = Literal["strong_buy", "buy", "hold", "sell", "strong_sell"]


@dataclass
class StockSnapshot:
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    turnover: float
    timestamp: str


@dataclass
class TrendAnalysis:
    code: str
    trend_score: float
    signal: Signal
    confidence: float
    reason: str
    latest_price: float


@dataclass
class TradePlan:
    code: str
    signal: Signal
    entry_price: float
    stop_loss: float
    take_profit: float
    shares: int
    max_position_cost: float
    reason: str
