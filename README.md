# daily_forex_analysis

LLM-assisted technical analysis for spot FX and metals. Fetches candles from
whichever data provider you have access to, computes indicators across multiple
timeframes, optionally asks a language model to interpret them, and writes a
report you can read or push to Telegram.

Runs with **zero configuration and no API keys** using Yahoo Finance. Every other
capability is opt-in via your own credentials.

```
$ python main.py --symbols EURUSD,USDJPY --dry-run

### EUR/USD  ▲
Last price 1.15540 (source: yfinance)
Multi-timeframe read: **up** (confidence: medium) — timeframes agree on an uptrend

| Timeframe | Trend | RSI | ATR (pips) | Range position | Range width |
| --- | --- | --- | --- | --- | --- |
| H1 | ▲ up | 53.0 | 6.9 | 53% | 60 |
| D1 | → sideways | 60.4 | 56.0 | 89% | 225 |
```

## Why this is not a stock analyser with the labels changed

FX has its own conventions, and getting them wrong makes every number
meaningless:

- **Pip size varies by pair.** A 0.0010 move is 10 pips on EUR/USD but 0.1 pips
  on USD/JPY. Distances are computed from each instrument's own convention, never
  a hardcoded `0.0001`.
- **There is no daily open or close.** Spot FX trades continuously from Sunday
  21:00 UTC to Friday 21:00 UTC. The tool reports which session is active
  (Tokyo / London / New York) and flags the London–New York overlap, rather than
  pretending there is an exchange bell.
- **No fundamentals.** There is no P/E ratio for a currency pair, so nothing here
  pretends to value one.

## Install

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Python 3.9 or newer.

## Quick start

```bash
# See what is configured and which providers are usable — no network needed
python main.py --check

# Analyse the default watchlist, print to stdout, write nothing
python main.py --dry-run

# Your pairs, your timeframes, written to reports/
python main.py --symbols EURUSD,GBPUSD,XAUUSD --timeframes H1,H4,D1

# Machine-readable output
python main.py --symbols EURUSD --format json
```

## Configuration

Copy `.env.example` to `.env` and fill in only what you need. Every value can
also be passed as an environment variable or, where applicable, a CLI flag.

### Data providers

Tried in order until one satisfies every requested timeframe. A provider without
credentials is skipped silently.

| Provider | Env var | Notes |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Native 4-hour candles; free tier available |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | FX only, no metals; free tier is rate-limited |
| Yahoo Finance | *(none)* | Default fallback, no key required |

Force one with `--provider twelvedata` or `FOREX_PROVIDER`.

Two provider caveats worth knowing:

- Yahoo has no 4-hour candle, so `H4` is resampled from hourly data.
- Yahoo has no spot metal quote, so `XAUUSD` is served from COMEX futures
  (`GC=F`). Futures carry basis and roll effects, so the level differs slightly
  from your broker's spot price. Fine for reading structure, not for execution.

### LLM commentary (optional)

Any OpenAI-compatible `/chat/completions` endpoint works. Without a key the
report is still produced from the computed analysis alone.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

Point `LLM_BASE_URL` at OpenRouter, DeepSeek, Groq, Together, or a local
llama.cpp / vLLM server and nothing else changes. `OPENAI_API_KEY`,
`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` and `GROQ_API_KEY` are all accepted, so
you need not rename an existing key.

The model never sees raw candles and never produces numbers — it receives the
already-computed readings and is asked to interpret them. That keeps prices and
levels deterministic and auditable.

### Telegram push (optional)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Skip it with `--no-push`. A failed push never discards a written report.

### All settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `FOREX_SYMBOLS` | majors + XAUUSD | Comma-separated pairs |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Subset of H1, H4, D1 |
| `FOREX_BARS` | `300` | Candles requested per timeframe |
| `FOREX_PROVIDER` | *(auto)* | Preferred provider name |
| `FOREX_OUTPUT_DIR` | `reports` | Where reports are written |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` or `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Symbols

Any of these spellings work: `EURUSD`, `eur/usd`, `EUR-USD`, `EUR_USD`,
`EURUSD=X`.

Supported: the 28 major and minor currency crosses, plus `XAUUSD`, `XAGUSD`,
`XPTUSD`, `XPDUSD`.

## What gets computed

Per timeframe: EMA(20/50) trend with an ATR-scaled noise floor, Wilder RSI(14),
MACD(12/26/9), ATR(14) with a volatility-regime percentile, Bollinger and
Donchian channels, and position within the recent range.

Across timeframes: an explicit confluence verdict (`up`, `down`, `sideways`,
`conflicted`) with a confidence level, because multi-timeframe agreement is the
signal most worth stating plainly rather than leaving to the model.

Everything is expressed in pips using the instrument's own convention.

## Scheduling

Cron, every weekday at 07:00 UTC:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

A GitHub Actions workflow is included at `.github/workflows/daily.yml`. It is
`workflow_dispatch` plus a daily schedule; add your keys as repository secrets to
enable the LLM and Telegram steps.

## Architecture

```
forex/
├── instruments.py   symbol parsing, pip conventions
├── sessions.py      24/5 market hours, Tokyo/London/NY sessions
├── providers.py     data sources with ordered fallback
├── analysis.py      indicators and structure (pure functions)
├── llm.py           optional commentary over computed readings
├── report.py        Markdown and JSON rendering
├── notify.py        optional Telegram push
├── config.py        env/.env configuration
└── pipeline.py      fetch -> analyse -> interpret -> render -> notify
main.py              CLI
```

`analysis.py` is pure: a DataFrame goes in, numbers come out. No network, no
config, no LLM. That is why the indicator tests run offline against synthetic
series.

### Adding a data provider

Subclass `CandleProvider`, implement `is_available()` and `fetch()`, and append it
to `build_providers()`. Nothing else needs to change.

```python
class MyProvider(CandleProvider):
    name = "myprovider"

    def is_available(self) -> bool:
        return bool(os.getenv("MY_API_KEY"))

    def fetch(self, instrument, timeframe, bars):
        ...  # return a DataFrame with open/high/low/close
```

## Tests

```bash
python -m pytest          # 178 tests, fully offline
```

No test touches the network. Providers are stubbed, candles are synthetic and
seeded, and indicators are checked against hand-computable cases (a monotonic
rise must give RSI 100, a gap-up candle's true range must use the previous close,
and so on).

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | At least one pair analysed |
| `1` | Every pair failed |
| `2` | Invalid symbol argument |

One pair failing never aborts the run; the error is recorded in the report's
Failures section.

## Not investment advice

This produces technical readings from public market data for educational
purposes. It does not tell you what to buy or sell, and it is not a substitute
for your own analysis or a licensed advisor. Prices from free data sources can be
delayed or wrong — verify with your broker before acting on anything here.

## License

MIT. Inspired by the pipeline structure of
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis);
this is an independent implementation for FX, sharing no code.
