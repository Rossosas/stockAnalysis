# stockAnalysis

现在支持两种使用方式：
- **Web 端（推荐）**：浏览器可视化分析 + 实时盯盘
- **CLI 端**：命令行分析与盯盘

## 快速开始（推荐）

在项目根目录执行：

```bash
python3 run_web.py
```

如果你的环境里 `python` 命令可用，也可以用：

```bash
python run_web.py
```

浏览器打开：

```text
http://127.0.0.1:8080
```

## Web 端功能（真正 Web 端）

也可使用原始方式启动：

```bash
python3 web_app.py
```

Web 页面支持：
1. 输入股票代码后点击“分析股票”
2. 自动返回：实时行情 + 历史+新闻综合分析 + 买卖建议（股数、止损、止盈）
3. 点击“开始盯盘”后每 5 秒刷新行情
4. 短时波动超过阈值（默认 1.2%）会在页面告警日志中提示

## CLI 功能

### 1) 分析股票

```bash
python3 cli.py analyze 600519 --cash 120000 --days 180 --max-news 20
```

### 2) 开盘实时盯盘

```bash
python3 cli.py watch 600519 --interval 5 --alert-pct 1.2 --limit 3
```

## 对应你的 5 个需求

1. **按股票代码分析**
   - `/api/analyze` 和 `cli.py analyze` 都支持
2. **A 股开盘实时盯盘**
   - Web 前端可持续轮询 `/api/quote`，CLI 有 `watch`
3. **历史走势 + 国内外新闻分析未来趋势**
   - 技术面（MA/MACD/RSI）+ 新闻面（中英新闻标题情绪）
4. **买卖时机 + 具体买卖股数**
   - 输出信号与风险预算下的建议股数（A 股按 100 股一手）
5. **周末/休市预测下个交易日开盘价**
   - 在没有实时成交时，系统会基于最近历史K线估算“下个交易日开盘价”
   - 输出字段：`predicted_next_open`、`prediction_range_low/high`、`prediction_date`

## 目录结构

```text
stockAnalysis/
├── web_app.py            # Web 服务 + 前端页面
├── run_web.py            # 一键启动入口
├── cli.py                # CLI 入口
├── requirements.txt
└── stock_analysis/
    ├── __init__.py
    ├── analyzer.py       # 趋势分析 + 交易计划
    ├── data_source.py    # 实时行情/历史K线/新闻抓取
    ├── models.py
    └── realtime.py       # 开盘判断 + 盯盘循环
```

## 常见问题

- **页面打不开 / `python: command not found`**：请使用 `python3`，并先 `cd` 到项目目录再启动。
- **接口返回 error / 502**：通常是外部行情源或网络代理限制导致，系统会尽量降级返回可用结果并附带 `warnings`。
- **周末能不能用**：可以，周末会基于历史数据输出“下个交易日开盘价预测”。

## 说明

- 当前实现尽量只用 Python 标准库，减少依赖安装失败问题。
- 真实行情/新闻依赖外部数据源；若网络受限，接口可能不可用。
- 本项目仅用于研究和软件开发测试，不构成投资建议。

## 一键启动参数

```bash
python3 run_web.py --host 127.0.0.1 --port 8080
python3 run_web.py --no-open   # 仅启动服务，不自动打开浏览器
```
