<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**面向外汇现货与贵金属的 LLM 辅助技术分析。**

以点为单位衡量的多周期指标 · 24/5 交易时段感知 · 可插拔数据源 · 使用你自己的 API 密钥

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-178%20passing-brightgreen.svg)](#测试)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#测试)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#贡献)

[English](README.md) ·
**简体中文** ·
[繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) ·
[한국어](README.ko.md) ·
[Bahasa Indonesia](README.id.md) ·
[Español](README.es.md) ·
[Português](README.pt-BR.md) ·
[Français](README.fr.md) ·
[Deutsch](README.de.md) ·
[Русский](README.ru.md)

</div>

---

## 概览

`daily_forex_analysis` 会从你能访问的任意行情数据源获取 K 线，计算多周期技术图景，
可选地请求语言模型进行解读，并生成一份报告——你可以在终端里阅读、提交到磁盘，
或推送到 Telegram。

借助 Yahoo Finance，它可以在**零配置、无需 API 密钥**的情况下运行。其余所有能力
——付费数据、LLM 点评、通知推送——都只在你提供自己的凭据后才会启用。

<div align="center">
  <img src="assets/demo.gif" alt="daily_forex_analysis running in a terminal" width="900">
</div>

```console
$ python main.py --symbols EURUSD,USDJPY --dry-run

### EUR/USD  ▲

Last price 1.15540 (source: yfinance)

Multi-timeframe read: **up** (confidence: medium) — timeframes agree on an uptrend

| Timeframe | Trend | RSI | ATR (pips) | Range position | Range width |
| --- | --- | --- | --- | --- | --- |
| H1 | ▲ up | 53.0 | 6.9 | 53% | 60 |
| D1 | → sideways | 60.4 | 56.0 | 89% | 225 |

- **H1**: fast EMA above slow EMA by 7.4 pips. RSI 53.0 mid-range; MACD histogram
  negative. ATR 6.9 pips (percentile 17 of recent history); compressed ranges often
  precede breakouts. High 1.158212, low 1.152206.

Most active during: London, New York
```

---

## 为什么这不是换了标签的股票分析器

外汇有一整套股票市场并不存在的惯例。一旦搞错，页面上的每一个数字都会失去意义。

| | 股票 | 外汇现货 | 本项目的处理方式 |
| --- | --- | --- | --- |
| **价格变动单位** | 1 分就是 1 分 | 在 EUR/USD 上 1 点是 0.0001，而在 USD/JPY 上是 0.01 | `instruments.py` 负责每个货币对的点值大小；代码中不会硬编码 `0.0001` |
| **交易时间** | 交易所开盘与收盘 | 连续交易，周日 21:00 → 周五 21:00 UTC | `sessions.py` 报告当前交易时段，并标记伦敦–纽约重叠时段 |
| **估值** | 市盈率、盈利、账面价值 | 货币没有盈利 | 不会凭空编造基本面数据 |
| **品种标识** | 不透明的代码（`AAPL`） | 一*对*货币 | 代码解析为基础货币与报价货币，各自遵循自身惯例 |

一次 0.0010 的波动在 EUR/USD 上是 **10 点**，在 USD/JPY 上却是 **0.1 点**。本代码库中
的每一段距离都由品种自身的惯例推导得出。

---

## 安装

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

需要 Python 3.9 或更高版本。

---

## 快速开始

```bash
# Show configuration and which providers are usable — no network required
python main.py --check

# Analyse the default watchlist, print to stdout, write nothing
python main.py --dry-run

# Your pairs, your timeframes, written to reports/
python main.py --symbols EURUSD,GBPUSD,XAUUSD --timeframes H1,H4,D1

# Machine-readable output
python main.py --symbols EURUSD --format json
```

### CLI 参考

| 参数 | 说明 |
| --- | --- |
| `--symbols` | 以逗号分隔的货币对，例如 `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | `H1,H4,D1` 的任意子集 |
| `--bars` | 每个周期请求的 K 线数量（默认 `300`） |
| `--provider` | 强制使用 `twelvedata`、`alphavantage` 或 `yfinance` |
| `--format` | `markdown`（默认）或 `json` |
| `--output-dir` | 报告的输出目录 |
| `--dry-run` | 仅分析并打印：不调用 LLM、不写文件、不发送通知 |
| `--no-push` | 跳过通知推送 |
| `--stdout` | 在写入文件的同时打印报告 |
| `--check` | 打印配置与数据源状态后退出 |
| `--log-level` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |

---

## 配置

将 `.env.example` 复制为 `.env`，只填写你需要的项。所有取值也都可以通过环境变量提供。

### 数据源

各数据源按顺序尝试，直到某一个能满足**全部**请求的周期，因此单份报告绝不会混用
惯例不同的数据来源。缺少凭据的数据源会被静默跳过。

| 数据源 | 凭据 | 备注 |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | 原生 4 小时 K 线；提供免费额度 |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | 仅外汇，不含贵金属；免费额度有频率限制 |
| Yahoo Finance | *无* | 默认兜底数据源，无需密钥 |

可用 `--provider twelvedata` 或 `FOREX_PROVIDER` 强制指定其中之一。

> [!NOTE]
> 关于 Yahoo Finance，有两点需要事先了解：
> - Yahoo 没有 4 小时 K 线，因此 `H4` 是由小时数据**重采样**得来的。
> - Yahoo 没有贵金属现货报价，因此 `XAUUSD` 取自 **COMEX 期货**
>   （`GC=F`）。期货存在基差与展期效应，价位会与你券商的现货价略有差异。
>   用于研判结构没问题，但不适合用于实际下单。

### LLM 点评（可选）

任何兼容 OpenAI 的 `/chat/completions` 端点均可使用。

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

把 `LLM_BASE_URL` 指向 OpenRouter、DeepSeek、Groq、Together，或本地的
llama.cpp / vLLM 服务即可，其他都不用改。`OPENAI_API_KEY`、
`OPENROUTER_API_KEY`、`DEEPSEEK_API_KEY` 和 `GROQ_API_KEY` 也都被接受，因此
你无需重命名已有的密钥。

> [!IMPORTANT]
> 模型从不接触原始 K 线，也从不生成数字。它接收的是已经计算好的读数，任务只是
> 对其进行解读，这使得每一个价格和价位都保持确定性且可审计。即使没有密钥，
> 报告仍会仅依据计算得出的分析生成。

### Telegram 推送（可选）

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

用 [@BotFather](https://t.me/BotFather) 创建机器人，并从
[@userinfobot](https://t.me/userinfobot) 获取你的 chat id。用 `--no-push` 可跳过推送。
推送失败绝不会丢弃已经写好的报告。

### 全部配置项

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `FOREX_SYMBOLS` | 主要货币对 + `XAUUSD` | 以逗号分隔的货币对 |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | H1、H4、D1 的子集 |
| `FOREX_BARS` | `300` | 每个周期请求的 K 线数量 |
| `FOREX_PROVIDER` | *自动* | 优先使用的数据源名称 |
| `FOREX_OUTPUT_DIR` | `reports` | 报告写入位置 |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` 或 `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |

---

## 交易品种

以下所有写法都会解析为同一个品种：

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

支持范围：主要与次要货币交叉盘，外加 `XAUUSD`（黄金）、`XAGUSD`
（白银）、`XPTUSD`（铂金）和 `XPDUSD`（钯金）。

---

## 计算内容

**每个周期**

- EMA(20/50) 趋势，并带有以 ATR 缩放的噪声下限，因此均线收敛时会被报告为
  *横盘* 而非虚假趋势
- Wilder RSI(14)
- MACD(12/26/9)
- ATR(14) 以及波动率区间百分位（收缩 / 正常 / 扩张）
- Bollinger 与 Donchian 通道
- 在近期区间中的位置，以及以点表示的区间宽度

**跨周期**

给出明确的共振结论——`up`、`down`、`sideways` 或 `conflicted`——并附带置信度。
多周期一致性是主观外汇分析中最有价值的结构性信号，因此本项目会直接计算并明确
陈述，而不是留给模型自己推断。

所有距离都按品种自身的惯例以点为单位表示。

---

## 定时运行

**Cron** —— 每个工作日 07:00 UTC，在伦敦开盘之后运行：

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** —— 仓库内置了工作流 `.github/workflows/daily.yml`
（`workflow_dispatch` 加每日定时）。把你的密钥添加为仓库 secrets 即可启用 LLM 与
Telegram 步骤；缺少 secrets 只会让这些功能保持关闭。

---

## 架构

```
forex/
├── instruments.py   symbol parsing, pip conventions
├── sessions.py      24/5 market hours, Tokyo/London/New York sessions
├── providers.py     data sources with ordered fallback
├── analysis.py      indicators and structure (pure functions)
├── llm.py           optional commentary over computed readings
├── report.py        Markdown and JSON rendering
├── notify.py        optional Telegram push
├── config.py        environment / .env configuration
└── pipeline.py      fetch → analyse → interpret → render → notify
main.py              CLI
```

`analysis.py` 是纯函数式的：传入一个 DataFrame，输出一组数字。不涉及网络、
不涉及配置、不涉及 LLM。这也正是指标测试能够完全离线地针对合成序列运行的原因。

**故障隔离是一项设计目标。** 某个货币对出错只会记录在报告的“失败”一节中，
而不会中断整次运行。LLM 调用或 Telegram 推送失败也绝不会丢弃已经计算好的报告。

### 新增数据源

继承 `CandleProvider`，实现两个方法，然后把它追加到 `build_providers()` 中。
代码库中其他任何地方都无需改动。

```python
from forex.providers import CandleProvider

class MyProvider(CandleProvider):
    name = "myprovider"

    def is_available(self) -> bool:
        return bool(os.getenv("MY_API_KEY"))

    def fetch(self, instrument, timeframe, bars):
        ...  # return a DataFrame with open/high/low/close
```

---

## 测试

```bash
python -m pytest          # 178 tests
```

没有任何测试触及网络。数据源被打桩替换，K 线是带固定随机种子的合成数据，
指标则针对可手工验算的用例进行校验——单调上涨必须给出 RSI 100，跳空高开
K 线的真实波幅必须使用前一根收盘价，同一个 ATR 在日元交叉盘上以点计数时
必须小 100 倍。

> [!NOTE]
> 随仓库提供的 CI 工作流在仓库启用 GitHub Actions 之前无法运行；在被锁定或未
> 绑定付费方式的账户上，每次运行都会在开始前失败。上面的数字来自 Python 3.14
> 上的本地运行，以及在独立虚拟环境中进行的一次全新可编辑安装。

---

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 至少有一个货币对分析成功 |
| `1` | 所有货币对均失败 |
| `2` | 品种参数无效 |

---

## 贡献

欢迎提交 issue 与 pull request。有价值的贡献包括新的数据源、更多指标、
通知渠道，以及 README 翻译。

请保持 `analysis.py` 的纯函数特性并且不含网络调用，同时补充可离线运行的测试。

---

## 免责声明

本项目基于公开市场数据生成技术读数，仅用于**教育目的**。它不会告诉你该买入或
卖出什么，也不能替代你自己的分析或持牌财务顾问的意见。免费数据源可能延迟或
出错——在依据这里的任何内容行动之前，请先与你的券商核对价格。外汇交易存在
重大亏损风险。

---

## 许可证

[MIT](LICENSE)

灵感来自
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)
的流水线结构。本项目是面向外汇的独立实现，与其不共享任何代码。
