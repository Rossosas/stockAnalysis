from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from urllib.error import URLError

from stock_analysis import (
    analyze_trend,
    as_dict,
    build_trade_plan,
    fetch_history,
    fetch_news_headlines,
    fetch_realtime_snapshot,
    watch_realtime,
)


def _offline_history(days: int) -> list[dict]:
    base = datetime.now() - timedelta(days=days)
    price = 20.0
    rows: list[dict] = []
    for i in range(days):
        d = base + timedelta(days=i)
        drift = 0.02
        shock = random.uniform(-0.4, 0.4)
        open_p = max(1.0, price + shock)
        close = max(1.0, open_p + random.uniform(-0.3, 0.3) + drift)
        high = max(open_p, close) + random.uniform(0, 0.2)
        low = min(open_p, close) - random.uniform(0, 0.2)
        vol = random.uniform(5e5, 4e6)
        rows.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "open": round(open_p, 3),
                "close": round(close, 3),
                "high": round(high, 3),
                "low": round(low, 3),
                "volume": vol,
                "turnover": vol * close,
            }
        )
        price = close
    return rows


def cmd_analyze(code: str, cash: float, days: int, max_news: int) -> None:
    warnings: list[str] = []

    try:
        snap = fetch_realtime_snapshot(code)
    except (URLError, ValueError) as exc:
        warnings.append(f"实时行情不可用，使用离线价格: {exc}")
        mock_price = _offline_history(1)[-1]["close"]
        snap = type("Snap", (), {"code": code, "name": code, "price": mock_price, "change_pct": 0.0, "volume": 0.0, "turnover": 0.0, "timestamp": datetime.now().isoformat()})()

    try:
        history = fetch_history(code, days=days)
    except (URLError, ValueError, json.JSONDecodeError) as exc:
        warnings.append(f"历史行情不可用，使用离线历史: {exc}")
        history = _offline_history(days)

    try:
        headlines = fetch_news_headlines(code, stock_name=getattr(snap, "name", code), limit=max_news)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"新闻接口不可用，使用离线新闻: {exc}")
        headlines = [
            "公司发布季度业绩，盈利同比增长",
            "行业政策出现边际改善预期",
            "海外宏观波动加剧，风险偏好下降",
        ]

    analysis = analyze_trend(code=getattr(snap, "code", code), history=history, news_titles=headlines)
    plan = build_trade_plan(
        code=getattr(snap, "code", code),
        latest_price=float(getattr(snap, "price", analysis.latest_price)),
        analysis=analysis,
        account_cash=cash,
    )

    snapshot_dict = {
        "code": getattr(snap, "code", code),
        "name": getattr(snap, "name", code),
        "price": float(getattr(snap, "price", analysis.latest_price)),
        "change_pct": float(getattr(snap, "change_pct", 0.0)),
        "volume": float(getattr(snap, "volume", 0.0)),
        "turnover": float(getattr(snap, "turnover", 0.0)),
        "timestamp": getattr(snap, "timestamp", datetime.now().isoformat()),
    }

    result = {
        "snapshot": snapshot_dict,
        "analysis": as_dict(analysis),
        "trade_plan": as_dict(plan),
        "headlines": headlines,
        "warnings": warnings,
        "generated_at": datetime.utcnow().isoformat(),
        "disclaimer": "仅供研究，不构成投资建议。",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_watch(code: str, interval: int, alert_pct: float, limit: int | None) -> None:
    print(f"开始盯盘: {code}, interval={interval}s, alert={alert_pct}%")

    def _on_update(snap):
        print(
            f"[{snap.timestamp}] {snap.code} {snap.name} "
            f"price={snap.price:.3f} change={snap.change_pct:.2f}% vol={snap.volume:.0f}"
        )

    def _on_alert(snap, msg: str):
        print(f"[ALERT] {msg} @ {snap.timestamp}, price={snap.price:.3f}")

    watch_realtime(
        code=code,
        fetch_snapshot=fetch_realtime_snapshot,
        on_update=_on_update,
        on_alert=_on_alert,
        interval_sec=interval,
        alert_pct=alert_pct,
        max_iterations=limit,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A股实时分析与盯盘工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_analyze = sub.add_parser("analyze", help="分析股票并生成建议")
    p_analyze.add_argument("code", help="股票代码，如 600519")
    p_analyze.add_argument("--cash", type=float, default=100000, help="账户可用资金")
    p_analyze.add_argument("--days", type=int, default=180, help="历史数据天数")
    p_analyze.add_argument("--max-news", type=int, default=20, help="新闻标题数")

    p_watch = sub.add_parser("watch", help="开盘时实时盯盘")
    p_watch.add_argument("code", help="股票代码，如 600519")
    p_watch.add_argument("--interval", type=int, default=5, help="轮询秒数")
    p_watch.add_argument("--alert-pct", type=float, default=1.2, help="短时波动告警阈值")
    p_watch.add_argument("--limit", type=int, default=None, help="最大轮询次数（调试）")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "analyze":
        cmd_analyze(code=args.code, cash=args.cash, days=args.days, max_news=args.max_news)
    elif args.cmd == "watch":
        cmd_watch(code=args.code, interval=args.interval, alert_pct=args.alert_pct, limit=args.limit)


if __name__ == "__main__":
    main()
