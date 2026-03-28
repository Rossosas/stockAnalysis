from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import Iterable

from .models import TradePlan, TrendAnalysis


def _sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return mean(values) if values else 0.0
    return mean(values[-period:])


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _calc_rsi(close: list[float], period: int = 14) -> float:
    if len(close) <= period:
        return 50.0
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(close)):
        delta = close[i] - close[i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))

    avg_gain = mean(gains[-period:])
    avg_loss = mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _calc_macd(close: list[float]) -> tuple[float, float]:
    ema12 = _ema_series(close, 12)
    ema26 = _ema_series(close, 26)
    min_len = min(len(ema12), len(ema26))
    if min_len == 0:
        return 0.0, 0.0
    macd_line = [ema12[i] - ema26[i] for i in range(min_len)]
    signal_line = _ema_series(macd_line, 9)
    return macd_line[-1], signal_line[-1] if signal_line else 0.0


def _next_trading_day(last_date_str: str) -> str:
    dt = datetime.strptime(last_date_str, "%Y-%m-%d")
    nxt = dt + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt.strftime("%Y-%m-%d")


def _predict_next_open(history: list[dict]) -> tuple[float, float, float, str, str]:
    rows = sorted(history, key=lambda x: x["date"])
    closes = [float(x["close"]) for x in rows]
    opens = [float(x.get("open", x["close"])) for x in rows]

    lookback = min(20, len(rows))
    recent_closes = closes[-lookback:]
    recent_opens = opens[-lookback:]

    # 1) 收盘线性趋势（近20日）
    trend = 0.0
    if lookback >= 2:
        trend = (recent_closes[-1] - recent_closes[0]) / (lookback - 1)

    # 2) 隔夜跳空（开盘-前收）均值
    gaps: list[float] = []
    for i in range(1, len(rows)):
        prev_close = closes[i - 1]
        if prev_close > 0:
            gaps.append((opens[i] - prev_close) / prev_close)
    avg_gap = mean(gaps[-lookback:]) if gaps else 0.0
    gap_std = pstdev(gaps[-lookback:]) if len(gaps[-lookback:]) > 1 else 0.01

    latest_close = closes[-1]
    trend_adjusted_close = latest_close + trend
    predicted_open = trend_adjusted_close * (1 + avg_gap)

    # 给一个简易区间（约1个标准差）
    low = predicted_open * (1 - gap_std)
    high = predicted_open * (1 + gap_std)

    pred_date = _next_trading_day(rows[-1]["date"])
    reason = (
        f"lookback={lookback}, trend/day={trend:.4f}, avg_gap={avg_gap:.4%}, "
        f"gap_std={gap_std:.4%}, last_close={latest_close:.3f}"
    )
    return predicted_open, low, high, pred_date, reason


def simple_news_sentiment(news_titles: Iterable[str]) -> float:
    positive = ["上涨", "增持", "突破", "利好", "盈利", "增长", "超预期", "beat", "surge", "upgrade"]
    negative = ["下跌", "减持", "亏损", "利空", "调查", "违规", "裁员", "miss", "downgrade", "selloff"]

    score = 0
    for raw in news_titles:
        title = raw.lower()
        score += sum(word in raw for word in positive[:7]) + sum(word in title for word in positive[7:])
        score -= sum(word in raw for word in negative[:7]) + sum(word in title for word in negative[7:])

    if score == 0:
        return 0.0
    normalized = max(-1.0, min(1.0, score / 10))
    return normalized


def analyze_trend(code: str, history: list[dict], news_titles: Iterable[str]) -> TrendAnalysis:
    if not history:
        raise ValueError("history is empty")

    rows = sorted(history, key=lambda x: x["date"])
    close = [float(x["close"]) for x in rows]
    latest = close[-1]

    ma20 = _sma(close, 20)
    ma60 = _sma(close, 60)
    rsi = _calc_rsi(close)
    macd, macd_signal = _calc_macd(close)

    predicted_open, pred_low, pred_high, pred_date, pred_reason = _predict_next_open(rows)

    tech_score = 0.0
    tech_score += 0.3 if latest > ma20 else -0.3
    tech_score += 0.35 if ma20 > ma60 else -0.35
    tech_score += 0.2 if macd > macd_signal else -0.2
    tech_score += 0.15 if 35 <= rsi <= 75 else -0.15

    # 如果预测下个交易日开盘高于最新收盘，额外给少量加分
    pred_bias = 0.1 if predicted_open > latest else -0.1
    tech_score += pred_bias

    news_score = simple_news_sentiment(news_titles)
    trend_score = 0.75 * tech_score + 0.25 * news_score
    confidence = min(0.95, 0.55 + abs(trend_score) / 1.2)

    if trend_score >= 0.6:
        signal = "strong_buy"
    elif trend_score >= 0.2:
        signal = "buy"
    elif trend_score <= -0.6:
        signal = "strong_sell"
    elif trend_score <= -0.2:
        signal = "sell"
    else:
        signal = "hold"

    reason = (
        f"MA20={ma20:.2f}, MA60={ma60:.2f}, RSI={rsi:.2f}, "
        f"MACD={macd:.3f}/{macd_signal:.3f}, news={news_score:.2f}, "
        f"tech={tech_score:.2f}, pred_bias={pred_bias:+.2f}"
    )

    return TrendAnalysis(
        code=code,
        trend_score=round(trend_score, 4),
        signal=signal,
        confidence=round(confidence, 4),
        reason=reason,
        latest_price=round(latest, 3),
        predicted_next_open=round(predicted_open, 3),
        prediction_range_low=round(pred_low, 3),
        prediction_range_high=round(pred_high, 3),
        prediction_date=pred_date,
        prediction_reason=pred_reason,
    )


def build_trade_plan(
    code: str,
    latest_price: float,
    analysis: TrendAnalysis,
    account_cash: float,
    max_risk_pct: float = 0.02,
) -> TradePlan:
    if latest_price <= 0:
        raise ValueError("latest_price must be positive")
    if account_cash <= 0:
        raise ValueError("account_cash must be positive")

    if analysis.signal in ("buy", "strong_buy"):
        stop_pct = 0.05
        take_profit_pct = 0.10
    elif analysis.signal in ("sell", "strong_sell"):
        stop_pct = 0.03
        take_profit_pct = 0.06
    else:
        stop_pct = 0.04
        take_profit_pct = 0.08

    stop_loss = latest_price * (1 - stop_pct)
    take_profit = latest_price * (1 + take_profit_pct)
    risk_per_share = max(0.01, latest_price - stop_loss)

    max_loss_amount = account_cash * max_risk_pct
    raw_shares = int(max_loss_amount / risk_per_share)
    lot_adjusted = (raw_shares // 100) * 100

    affordable_shares = int(account_cash / latest_price)
    affordable_lot = (affordable_shares // 100) * 100
    shares = max(0, min(lot_adjusted, affordable_lot))

    if analysis.signal in ("hold", "sell", "strong_sell"):
        shares = 0

    max_position_cost = shares * latest_price
    reason = (
        f"signal={analysis.signal}, confidence={analysis.confidence}, "
        f"risk_budget={max_risk_pct:.1%}, shares={shares}"
    )

    return TradePlan(
        code=code,
        signal=analysis.signal,
        entry_price=round(latest_price, 3),
        stop_loss=round(stop_loss, 3),
        take_profit=round(take_profit, 3),
        shares=shares,
        max_position_cost=round(max_position_cost, 2),
        reason=reason,
    )


def as_dict(obj) -> dict:
    return asdict(obj)
