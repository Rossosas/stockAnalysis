from __future__ import annotations

import time
from datetime import datetime
from typing import Callable

from .models import StockSnapshot


CN_FIXED_HOLIDAYS = {(1, 1), (5, 1), (10, 1)}


def is_a_share_market_open(now: datetime | None = None) -> bool:
    now = now or datetime.now()

    if now.weekday() >= 5:
        return False
    if (now.month, now.day) in CN_FIXED_HOLIDAYS:
        return False

    hm = now.hour * 60 + now.minute
    morning = 9 * 60 + 30 <= hm <= 11 * 60 + 30
    afternoon = 13 * 60 <= hm <= 15 * 60
    return morning or afternoon


def watch_realtime(
    code: str,
    fetch_snapshot: Callable[[str], StockSnapshot],
    on_update: Callable[[StockSnapshot], None],
    on_alert: Callable[[StockSnapshot, str], None] | None = None,
    interval_sec: int = 5,
    alert_pct: float = 1.5,
    max_iterations: int | None = None,
) -> None:
    """开盘时盯盘，支持涨跌幅告警。"""
    count = 0
    prev_price: float | None = None

    while True:
        if not is_a_share_market_open():
            time.sleep(interval_sec)
            continue

        snap = fetch_snapshot(code)
        on_update(snap)

        if on_alert and prev_price and prev_price > 0:
            move_pct = (snap.price - prev_price) / prev_price * 100
            if abs(move_pct) >= alert_pct:
                on_alert(snap, f"{code} 短时波动 {move_pct:.2f}%")

        prev_price = snap.price
        count += 1
        if max_iterations and count >= max_iterations:
            return
        time.sleep(interval_sec)
