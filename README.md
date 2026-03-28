# stockAnalysis

现在支持两种使用方式：
- **Web 端（推荐）**：浏览器可视化分析 + 实时盯盘
- **CLI 端**：命令行分析与盯盘

## Web 端功能（你要的“真正 Web 端”）

启动服务（推荐一键脚本）：

```bash
python run_web.py
```

或使用原始方式：

```bash
python web_app.py
```

浏览器打开：

```text
http://127.0.0.1:8080
```

Web 页面支持：
1. 输入股票代码后点击“分析股票”
2. 自动返回：实时行情 + 历史+新闻综合分析 + 买卖建议（股数、止损、止盈）
3. 点击“开始盯盘”后每 5 秒刷新行情
4. 短时波动超过阈值（默认 1.2%）会在页面告警日志中提示

## CLI 功能

### 1) 分析股票

```bash
python cli.py analyze 600519 --cash 120000 --days 180 --max-news 20
```

### 2) 开盘实时盯盘

```bash
python cli.py watch 600519 --interval 5 --alert-pct 1.2 --limit 3
```

## 对应你的 4 个需求

1. **按股票代码分析**
   - `/api/analyze` 和 `cli.py analyze` 都支持
2. **A 股开盘实时盯盘**
   - Web 前端可持续轮询 `/api/quote`，CLI 有 `watch`
3. **历史走势 + 国内外新闻分析未来趋势**
   - 技术面（MA/MACD/RSI）+ 新闻面（中英新闻标题情绪）
4. **买卖时机 + 具体买卖股数**
   - 输出信号与风险预算下的建议股数（A 股按 100 股一手）

## 目录结构

```text
stockAnalysis/
├── web_app.py            # Web 服务 + 前端页面
├── cli.py                # CLI 入口
├── requirements.txt
└── stock_analysis/
    ├── __init__.py
    ├── analyzer.py       # 趋势分析 + 交易计划
    ├── data_source.py    # 实时行情/历史K线/新闻抓取
    ├── models.py
    └── realtime.py       # 开盘判断 + 盯盘循环
```

## 说明

- 当前实现尽量只用 Python 标准库，减少依赖安装失败问题。
- 真实行情/新闻依赖外部数据源；若网络受限，接口可能不可用。
- 本项目仅用于研究和软件开发测试，不构成投资建议。


### 一键启动参数

```bash
python run_web.py --host 127.0.0.1 --port 8080
python run_web.py --no-open   # 仅启动服务，不自动打开浏览器
```
