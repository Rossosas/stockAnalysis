from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

from .models import StockSnapshot

UA = "Mozilla/5.0 (stockAnalysis bot)"


def _http_get(url: str, timeout: int = 10, encoding: str | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        data = resp.read()
    return data.decode(encoding or "utf-8", errors="ignore")


def code_to_market_prefix(code: str) -> str:
    c = code.strip().lower()
    if c.startswith(("sh", "sz", "bj")):
        return c
    if c.startswith(("6", "9")):
        return f"sh{c}"
    if c.startswith(("0", "3", "2", "8", "4")):
        return f"sz{c}"
    return f"sh{c}"


def code_to_secid(code: str) -> str:
    c = code.strip().lower()
    if c.startswith("sh"):
        return f"1.{c[2:]}"
    if c.startswith(("sz", "bj")):
        return f"0.{c[2:]}"
    if c.startswith(("6", "9")):
        return f"1.{c}"
    return f"0.{c}"


def fetch_realtime_snapshot(code: str) -> StockSnapshot:
    symbol = code_to_market_prefix(code)
    url = f"https://qt.gtimg.cn/q={symbol}"
    raw = _http_get(url, encoding="gbk")

    parts = raw.split("~")
    if len(parts) < 38:
        raise ValueError(f"unexpected quote payload for {code}: {raw[:120]}")

    name = parts[1].strip() or symbol
    raw_code = parts[2].strip() or symbol
    price = float(parts[3] or 0)
    prev_close = float(parts[4] or 0)
    volume_lot = float(parts[6] or 0)
    turnover = float(parts[37] or 0)
    timestamp = parts[30] if len(parts) > 30 else datetime.utcnow().isoformat()

    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

    return StockSnapshot(
        code=raw_code,
        name=name,
        price=round(price, 3),
        change_pct=round(change_pct, 3),
        volume=volume_lot,
        turnover=turnover,
        timestamp=timestamp,
    )


def fetch_history(code: str, days: int = 180) -> list[dict]:
    secid = code_to_secid(code)
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}&klt=101&fqt=1&lmt={days}&end=20500101"
        "&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
    )
    payload = _http_get(url)
    m = re.search(r"\((\{.*\})\)", payload)
    text = m.group(1) if m else payload
    data = json.loads(text)

    klines = (((data or {}).get("data") or {}).get("klines")) or []
    rows: list[dict] = []
    for item in klines:
        # date,open,close,high,low,volume,turnover,amp,pct,chg,turnover_rate
        cols = item.split(",")
        if len(cols) < 7:
            continue
        rows.append(
            {
                "date": cols[0],
                "open": float(cols[1]),
                "close": float(cols[2]),
                "high": float(cols[3]),
                "low": float(cols[4]),
                "volume": float(cols[5]),
                "turnover": float(cols[6]),
            }
        )
    if not rows:
        raise ValueError(f"no history found for {code}")
    return rows


def _fetch_google_news_rss(query: str, lang: str, country: str, limit: int) -> list[str]:
    q = urllib.parse.quote(query)
    url = (
        "https://news.google.com/rss/search"
        f"?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"
    )
    xml_text = _http_get(url)
    root = ET.fromstring(xml_text)
    out: list[str] = []
    for item in root.findall("./channel/item/title"):
        if item.text:
            out.append(item.text.strip())
        if len(out) >= limit:
            break
    return out


def fetch_news_headlines(code: str, stock_name: str = "", limit: int = 40) -> list[str]:
    base_terms = [code]
    if stock_name:
        base_terms.append(stock_name)
    query_cn = " OR ".join(base_terms + ["A股", "上证", "深证", "财报"])
    query_en = " OR ".join(base_terms + ["China stock", "earnings", "macro"])

    cn_news = _fetch_google_news_rss(query_cn, lang="zh-CN", country="CN", limit=limit // 2)
    en_news = _fetch_google_news_rss(query_en, lang="en-US", country="US", limit=limit // 2)

    merged: list[str] = []
    seen = set()
    for title in cn_news + en_news:
        cleaned = title.replace(" - Google News", "").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            merged.append(cleaned)
    return merged[:limit]
