from __future__ import annotations

import argparse
import threading
import time
import webbrowser

from web_app import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="一键启动 stockAnalysis Web")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8080, help="监听端口")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    if not args.no_open:
        def _open_browser() -> None:
            time.sleep(1.0)
            try:
                webbrowser.open(url)
            except Exception:
                pass

        threading.Thread(target=_open_browser, daemon=True).start()

    print("=" * 60)
    print("stockAnalysis Web 已启动")
    print(f"访问地址: {url}")
    print("默认可直接输入股票代码后点击【分析股票】")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
