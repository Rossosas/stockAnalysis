from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from stock_analysis import (
    analyze_trend,
    as_dict,
    build_trade_plan,
    fetch_history,
    fetch_news_headlines,
    fetch_realtime_snapshot,
)

INDEX_HTML = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>A股分析Web端</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 980px; margin: 20px auto; padding: 0 12px; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 14px; margin-bottom: 12px; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; }
    input, button { padding: 8px; }
    pre { background: #111; color: #0f0; padding: 10px; border-radius: 8px; overflow: auto; }
    .muted { color: #666; }
  </style>
</head>
<body>
  <h1>📈 A股股票分析 Web 端</h1>
  <p class=\"muted\">仅供研究，不构成投资建议。</p>

  <div class=\"card\">
    <div class=\"row\">
      <input id=\"code\" value=\"600519\" placeholder=\"股票代码\" />
      <input id=\"cash\" value=\"120000\" placeholder=\"账户资金\" />
      <button onclick=\"runAnalyze()\">分析股票</button>
      <button onclick=\"toggleWatch()\" id=\"watchBtn\">开始盯盘</button>
    </div>
    <p class=\"muted\">分析结果中包含：下个交易日开盘预测（predicted_next_open）及预测区间。</p>
  </div>

  <div class=\"card\"><h3>实时行情</h3><pre id=\"quote\">尚未请求</pre></div>
  <div class=\"card\"><h3>综合分析 + 买卖建议</h3><pre id=\"analysis\">尚未请求</pre></div>
  <div class=\"card\"><h3>告警日志</h3><pre id=\"alerts\">尚未告警</pre></div>

  <script>
    let watchTimer = null;
    let prevPrice = null;

    function val(id) { return document.getElementById(id).value.trim(); }
    function setText(id, text) { document.getElementById(id).textContent = text; }

    async function runAnalyze() {
      const code = val('code');
      const cash = val('cash') || '100000';
      const res = await fetch(`/api/analyze?code=${encodeURIComponent(code)}&cash=${encodeURIComponent(cash)}`);
      const data = await res.json();
      setText('analysis', JSON.stringify(data, null, 2));
      if (data.snapshot) setText('quote', JSON.stringify(data.snapshot, null, 2));
    }

    async function fetchQuote() {
      const code = val('code');
      const res = await fetch(`/api/quote?code=${encodeURIComponent(code)}`);
      const data = await res.json();
      setText('quote', JSON.stringify(data, null, 2));

      if (!data.error && data.price != null) {
        if (prevPrice != null) {
          const pct = ((data.price - prevPrice) / prevPrice) * 100;
          if (Math.abs(pct) >= 1.2) {
            const line = `[${new Date().toLocaleTimeString()}] ${code} 短时波动 ${pct.toFixed(2)}% 价格=${data.price}`;
            const old = document.getElementById('alerts').textContent;
            setText('alerts', old === '尚未告警' ? line : `${line}\n${old}`);
          }
        }
        prevPrice = data.price;
      }
    }

    function toggleWatch() {
      const btn = document.getElementById('watchBtn');
      if (watchTimer) {
        clearInterval(watchTimer);
        watchTimer = null;
        btn.textContent = '开始盯盘';
        return;
      }
      prevPrice = null;
      fetchQuote();
      watchTimer = setInterval(fetchQuote, 5000);
      btn.textContent = '停止盯盘';
    }
  </script>
</body>
</html>
"""


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


def json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/quote":
            params = parse_qs(parsed.query)
            code = (params.get("code") or [""])[0].strip()
            if not code:
                json_response(self, {"error": "missing code"}, status=400)
                return
            try:
                snap = fetch_realtime_snapshot(code)
                json_response(self, as_dict(snap))
            except Exception as exc:  # noqa: BLE001
                json_response(self, {"error": str(exc), "code": code}, status=502)
            return

        if parsed.path == "/api/analyze":
            params = parse_qs(parsed.query)
            code = (params.get("code") or [""])[0].strip()
            cash = float((params.get("cash") or ["100000"])[0])
            days = int((params.get("days") or ["180"])[0])
            max_news = int((params.get("max_news") or ["20"])[0])

            if not code:
                json_response(self, {"error": "missing code"}, status=400)
                return

            warnings: list[str] = []
            try:
                snap = fetch_realtime_snapshot(code)
            except (URLError, ValueError, Exception) as exc:  # noqa: BLE001
                warnings.append(f"实时行情不可用，使用离线价格: {exc}")
                mock_price = _offline_history(1)[-1]["close"]
                snap = type("Snap", (), {"code": code, "name": code, "price": mock_price, "change_pct": 0.0, "volume": 0.0, "turnover": 0.0, "timestamp": datetime.now().isoformat()})()

            try:
                history = fetch_history(code, days=days)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"历史行情不可用，使用离线历史: {exc}")
                history = _offline_history(days)

            try:
                news = fetch_news_headlines(code, stock_name=getattr(snap, "name", code), limit=max_news)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"新闻不可用，使用离线新闻: {exc}")
                news = [
                    "公司发布季度业绩，盈利同比增长",
                    "行业政策出现边际改善预期",
                    "海外宏观波动加剧，风险偏好下降",
                ]

            analysis = analyze_trend(code=getattr(snap, "code", code), history=history, news_titles=news)
            plan = build_trade_plan(
                code=getattr(snap, "code", code),
                latest_price=float(getattr(snap, "price", analysis.latest_price)),
                analysis=analysis,
                account_cash=cash,
            )
            json_response(
                self,
                {
                    "snapshot": {
                        "code": getattr(snap, "code", code),
                        "name": getattr(snap, "name", code),
                        "price": float(getattr(snap, "price", analysis.latest_price)),
                        "change_pct": float(getattr(snap, "change_pct", 0.0)),
                        "volume": float(getattr(snap, "volume", 0.0)),
                        "turnover": float(getattr(snap, "turnover", 0.0)),
                        "timestamp": getattr(snap, "timestamp", datetime.now().isoformat()),
                    },
                    "analysis": as_dict(analysis),
                    "trade_plan": as_dict(plan),
                    "headlines": news,
                    "warnings": warnings,
                    "generated_at": datetime.utcnow().isoformat(),
                    "disclaimer": "仅供研究，不构成投资建议。",
                },
            )
            return

        json_response(self, {"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Web server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
