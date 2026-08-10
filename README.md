<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**LLM-assisted technical analysis for spot FX and metals.**

Multi-timeframe indicators measured in pips · 24/5 session awareness · pluggable data providers · bring your own API keys

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-214%20passing-brightgreen.svg)](#tests)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#tests)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#contributing)

**English** ·
[简体中文](README.zh-CN.md) ·
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

## Overview

`daily_forex_analysis` fetches candles from whichever market data provider you have
access to, computes a multi-timeframe technical picture, optionally asks a language
model to interpret it, and writes a report you can read in your terminal, commit to
disk, or push to Telegram.

It runs with **zero configuration and no API keys** using Yahoo Finance. Every other
capability — premium data, LLM commentary, notifications — activates only when you
supply your own credentials.

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

## Why this is not a stock analyser with the labels changed

FX carries conventions that have no equity equivalent. Getting them wrong makes every
number on the page meaningless.

| | Equities | Spot FX | How this project handles it |
| --- | --- | --- | --- |
| **Unit of movement** | 1 cent is 1 cent | a pip is 0.0001 on EUR/USD but 0.01 on USD/JPY | `instruments.py` owns each pair's pip size; nothing hardcodes `0.0001` |
| **Trading hours** | exchange open and close | continuous, Sunday 21:00 → Friday 21:00 UTC | `sessions.py` reports the live session and flags the London–New York overlap |
| **Valuation** | P/E, earnings, book value | a currency has no earnings | no fundamentals are invented |
| **Instrument identity** | opaque ticker (`AAPL`) | a *pair* of currencies | symbols parse into base and quote with their own conventions |

A 0.0010 move is **10 pips** on EUR/USD and **0.1 pips** on USD/JPY. Every distance in
this codebase is derived from the instrument's own convention.

---

## Installation

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Requires Python 3.9 or newer.

---

## Quick start

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

### CLI reference

| Flag | Description |
| --- | --- |
| `--symbols` | Comma-separated pairs, e.g. `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | Subset of `H1,H4,D1` |
| `--bars` | Candles requested per timeframe (default `300`) |
| `--provider` | Force `twelvedata`, `alphavantage`, or `yfinance` |
| `--format` | `markdown` (default) or `json` |
| `--output-dir` | Destination directory for reports |
| `--dry-run` | Analyse and print only: no LLM call, no file, no notification |
| `--no-push` | Skip notifications |
| `--stdout` | Print the report as well as writing it |
| `--check` | Print configuration and provider status, then exit |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Configuration

Copy `.env.example` to `.env` and fill in only what you need. Every value can also be
supplied as an environment variable.

### Data providers

Providers are tried in order until one satisfies **every** requested timeframe, so a
single report never mixes sources with different conventions. A provider without
credentials is skipped silently.

| Provider | Credential | Notes |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Native 4-hour candles; free tier available |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | FX only, no metals; rate-limited free tier |
| Yahoo Finance | *none* | Default fallback, no key required |

Force one with `--provider twelvedata` or `FOREX_PROVIDER`.

> [!NOTE]
> Two Yahoo Finance caveats worth knowing up front:
> - Yahoo has no 4-hour candle, so `H4` is **resampled** from hourly data.
> - Yahoo has no spot metal quote, so `XAUUSD` is served from **COMEX futures**
>   (`GC=F`). Futures carry basis and roll effects, so the level differs slightly from
>   your broker's spot price. Fine for reading structure, not for execution.

### LLM commentary (optional)

Any OpenAI-compatible `/chat/completions` endpoint works.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

Point `LLM_BASE_URL` at OpenRouter, DeepSeek, Groq, Together, or a local
llama.cpp / vLLM server and nothing else changes. `OPENAI_API_KEY`,
`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` and `GROQ_API_KEY` are all accepted, so you
need not rename a key you already have.

> [!IMPORTANT]
> The model never sees raw candles and never produces numbers. It receives the
> already-computed readings and is asked to interpret them, which keeps every price and
> level deterministic and auditable. Without a key the report is still produced from
> computed analysis alone.

### Telegram push (optional)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Create a bot with [@BotFather](https://t.me/BotFather) and get your chat id from
[@userinfobot](https://t.me/userinfobot). Skip delivery with `--no-push`. A failed push
never discards a report that was already written.

### All settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `FOREX_SYMBOLS` | majors + `XAUUSD` | Comma-separated pairs |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Subset of H1, H4, D1 |
| `FOREX_BARS` | `300` | Candles requested per timeframe |
| `FOREX_PROVIDER` | *auto* | Preferred provider name |
| `FOREX_OUTPUT_DIR` | `reports` | Where reports are written |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` or `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Symbols

All of these spellings resolve to the same instrument:

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

Supported: the major and minor currency crosses, plus `XAUUSD` (gold), `XAGUSD`
(silver), `XPTUSD` (platinum) and `XPDUSD` (palladium).

---

## What gets computed

**Per timeframe**

- EMA(20/50) trend, with an ATR-scaled noise floor so compressed averages are reported
  as *sideways* rather than as a false trend
- Wilder RSI(14)
- MACD(12/26/9)
- ATR(14) plus a volatility-regime percentile (contracting / normal / expanding)
- Bollinger and Donchian channels
- Position within the recent range, and range width in pips

**Across timeframes**

An explicit confluence verdict — `up`, `down`, `sideways` or `conflicted` — with a
confidence level. Multi-timeframe agreement is the most useful structural signal in
discretionary FX analysis, so it is computed and stated plainly instead of being left
for the model to infer.

Every distance is expressed in pips using the instrument's own convention.

---

## Scheduling

**Cron** — every weekday at 07:00 UTC, after the London open:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — a workflow is included at `.github/workflows/daily.yml`
(`workflow_dispatch` plus a daily schedule). Add your keys as repository secrets to
enable the LLM and Telegram steps; missing secrets simply disable those features.

---

## Architecture

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

`analysis.py` is pure: a DataFrame goes in, numbers come out. No network, no
configuration, no LLM. That is why the indicator tests run entirely offline against
synthetic series.

**Failure isolation is a design goal.** One broken pair is recorded in the report's
Failures section rather than aborting the run. A failed LLM call or Telegram push never
discards a report that was already computed.

### Adding a data provider

Subclass `CandleProvider`, implement two methods, and append it to `build_providers()`.
Nothing else in the codebase needs to change.

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

## Tests

```bash
python -m pytest          # 214 tests
```

No test touches the network. Providers are stubbed, candles are synthetic and seeded,
and indicators are verified against hand-computable cases — a monotonic rise must give
RSI 100, a gap-up candle's true range must use the previous close, the same ATR must
read 100× smaller in pips on a JPY cross.

`tests/test_demo_assets.py` covers the demo-GIF text pipeline in `assets/make_demo.py`:
markdown consumption, table column alignment, and frame-width wrapping. The image
drawing itself is not asserted — comparing rasters is brittle — but every transform
that produced a visible defect is pinned.

> [!NOTE]
> The bundled CI workflow cannot run until GitHub Actions is enabled on the repository;
> on a locked or unbilled account every run fails before starting. The counts above come
> from local runs on Python 3.14 and from a clean editable install in a separate
> virtual environment.

---

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | At least one pair was analysed |
| `1` | Every pair failed |
| `2` | Invalid symbol argument |

---

## Contributing

Issues and pull requests are welcome. Useful contributions include new data providers,
additional indicators, notification channels, and README translations.

Please keep `analysis.py` pure and free of network calls, and add tests that run
offline.

---

## Disclaimer

This project produces technical readings from public market data for **educational
purposes**. It does not tell you what to buy or sell, and it is not a substitute for
your own analysis or for a licensed financial adviser. Free data sources can be delayed
or wrong — verify prices with your broker before acting on anything here. Trading
foreign exchange carries substantial risk of loss.

---

## License

[MIT](LICENSE)

Inspired by the pipeline structure of
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis).
This is an independent implementation for FX and shares no code with it.
