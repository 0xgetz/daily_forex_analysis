<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**運用 LLM 輔助的外匯即期與貴金屬技術分析工具。**

以點（pip）衡量的多時間框架指標 · 24/5 交易時段感知 · 可插拔資料供應商 · 使用你自己的 API 金鑰

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-214%20passing-brightgreen.svg)](#測試)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#測試)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#貢獻)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
**繁體中文** ·
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

## 總覽

`daily_forex_analysis` 會從你能取用的任一市場資料供應商抓取 K 線，計算多時間框架的技術面全貌，並可選擇性地請語言模型加以解讀，最後產出一份報告——你可以在終端機閱讀、寫入磁碟保存，或推送到 Telegram。

使用 Yahoo Finance 時，本專案**無需任何設定、也不需要 API 金鑰**即可運行。其餘所有功能——付費資料、LLM 評述、通知推送——都只在你提供自己的憑證後才會啟用。

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

## 為什麼這不是換個標籤的股票分析工具

外匯有一套股票市場並不存在的慣例。搞錯這些慣例，報告上的每一個數字都會失去意義。

| | 股票 | 即期外匯 | 本專案的處理方式 |
| --- | --- | --- | --- |
| **價格變動單位** | 1 分就是 1 分 | EUR/USD 的 1 點是 0.0001，但 USD/JPY 的 1 點是 0.01 | `instruments.py` 掌管每個貨幣對的點值大小；程式中沒有任何地方硬寫 `0.0001` |
| **交易時間** | 交易所有開盤與收盤 | 連續交易，週日 21:00 → 週五 21:00 UTC | `sessions.py` 回報當前交易時段，並標示倫敦與紐約的重疊時段 |
| **評價方式** | 本益比、盈餘、帳面價值 | 貨幣沒有盈餘 | 不憑空編造任何基本面資料 |
| **標的身分** | 不透明的代號（`AAPL`） | 一*組*貨幣配對 | 代號會解析為基準貨幣與計價貨幣，各自帶有專屬慣例 |

0.0010 的波動在 EUR/USD 上是 **10 點**，在 USD/JPY 上卻是 **0.1 點**。本程式碼庫中的每一個距離，都是依照該標的自身的慣例推導出來的。

---

## 安裝

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

需要 Python 3.9 或更新版本。

---

## 快速開始

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

### CLI 參數說明

| 參數 | 說明 |
| --- | --- |
| `--symbols` | 以逗號分隔的貨幣對，例如 `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | `H1,H4,D1` 的任意子集 |
| `--bars` | 每個時間框架要求的 K 線數量（預設 `300`） |
| `--provider` | 強制指定 `twelvedata`、`alphavantage` 或 `yfinance` |
| `--format` | `markdown`（預設）或 `json` |
| `--output-dir` | 報告的輸出目錄 |
| `--dry-run` | 只分析並列印：不呼叫 LLM、不寫檔、不發送通知 |
| `--no-push` | 略過通知推送 |
| `--stdout` | 寫檔的同時也把報告列印出來 |
| `--check` | 列印設定與供應商狀態後結束 |
| `--log-level` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |

---

## 設定

將 `.env.example` 複製為 `.env`，只填入你需要的項目。所有設定值也都可以透過環境變數提供。

### 資料供應商

系統會依序嘗試各家供應商，直到其中一家能滿足**所有**要求的時間框架為止，因此同一份報告絕不會混用慣例不同的資料來源。未提供憑證的供應商會被靜默略過。

| 供應商 | 憑證 | 說明 |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | 原生提供 4 小時 K 線；有免費方案 |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | 僅支援外匯，不含貴金屬；免費方案有速率限制 |
| Yahoo Finance | *無* | 預設的後備來源，不需金鑰 |

可用 `--provider twelvedata` 或 `FOREX_PROVIDER` 強制指定其中一家。

> [!NOTE]
> 有兩點關於 Yahoo Finance 的注意事項值得事先了解：
> - Yahoo 沒有 4 小時 K 線，因此 `H4` 是由小時線**重新取樣**而來。
> - Yahoo 沒有即期貴金屬報價，因此 `XAUUSD` 由 **COMEX 期貨**（`GC=F`）提供。期貨帶有基差與轉倉效應，所以價位會與你券商的即期價格略有差異。用來判讀結構沒問題，但不適合作為實際下單依據。

### LLM 評述（選用）

任何相容於 OpenAI `/chat/completions` 的端點都可以使用。

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

把 `LLM_BASE_URL` 指向 OpenRouter、DeepSeek、Groq、Together，或本機的 llama.cpp / vLLM 伺服器，其他設定完全不必改動。`OPENAI_API_KEY`、`OPENROUTER_API_KEY`、`DEEPSEEK_API_KEY` 與 `GROQ_API_KEY` 也都能被接受，所以你不需要為既有的金鑰改名。

> [!IMPORTANT]
> 模型永遠看不到原始 K 線，也不會產生任何數字。它收到的是已經計算完成的讀數，任務只是加以解讀，因此每一個價格與價位都保持確定性且可稽核。即使沒有金鑰，報告仍然能單憑計算出的分析結果產出。

### Telegram 推送（選用）

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

透過 [@BotFather](https://t.me/BotFather) 建立機器人，並從 [@userinfobot](https://t.me/userinfobot) 取得你的 chat id。用 `--no-push` 可略過推送。推送失敗絕不會丟棄已經寫好的報告。

### 所有設定項

| 變數 | 預設值 | 意義 |
| --- | --- | --- |
| `FOREX_SYMBOLS` | 主要貨幣對 + `XAUUSD` | 以逗號分隔的貨幣對 |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | H1、H4、D1 的任意子集 |
| `FOREX_BARS` | `300` | 每個時間框架要求的 K 線數量 |
| `FOREX_PROVIDER` | *自動* | 偏好的供應商名稱 |
| `FOREX_OUTPUT_DIR` | `reports` | 報告寫入的位置 |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` 或 `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |

---

## 代號

以下這些寫法都會解析成同一個標的：

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

支援範圍：主要與次要貨幣交叉盤，另加 `XAUUSD`（黃金）、`XAGUSD`（白銀）、`XPTUSD`（白金）與 `XPDUSD`（鈀金）。

---

## 計算內容

**各時間框架分別計算**

- EMA(20/50) 趨勢，並搭配以 ATR 縮放的雜訊底線，讓過度壓縮的均線被判定為*盤整*，而不是誤判為趨勢
- Wilder RSI(14)
- MACD(12/26/9)
- ATR(14) 以及波動率狀態百分位（收縮 / 正常 / 擴張）
- Bollinger 與 Donchian 通道
- 在近期區間中的位置，以及以點表示的區間寬度

**跨時間框架綜合**

一個明確的共振結論——`up`、`down`、`sideways` 或 `conflicted`——並附上信心水準。多時間框架的一致性是主觀外匯分析中最實用的結構訊號，因此我們直接計算並明確陳述，而不是留給模型自行推測。

所有距離都依照該標的自身的慣例以點表示。

---

## 排程

**Cron** —— 每個工作日 07:00 UTC，倫敦開盤之後執行：

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** —— 專案已內附工作流程檔 `.github/workflows/daily.yml`（支援 `workflow_dispatch` 以及每日排程）。把你的金鑰加為 repository secrets 即可啟用 LLM 與 Telegram 步驟；缺少 secrets 時，這些功能只會單純停用。

---

## 架構

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

`analysis.py` 是純函式模組：輸入一個 DataFrame，輸出數字。不涉及網路、不涉及設定、不涉及 LLM。這也是為什麼指標測試能完全離線、針對合成序列執行。

**故障隔離是明確的設計目標。** 單一貨幣對出錯時，只會記錄在報告的 Failures 區段，不會中止整趟執行。LLM 呼叫或 Telegram 推送失敗，絕不會丟棄已經計算完成的報告。

### 新增資料供應商

繼承 `CandleProvider`，實作兩個方法，再把它加到 `build_providers()` 即可。程式碼庫的其他部分都不需要改動。

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

## 測試

```bash
python -m pytest          # 214 tests
```

沒有任何測試會碰觸網路。供應商都以 stub 取代，K 線是帶固定種子的合成資料，指標則對照可手算驗證的案例檢查——單調上漲必須得出 RSI 100、跳空上漲 K 線的真實區間必須採用前一根收盤價、同樣的 ATR 在日圓交叉盤上以點計算時必須小 100 倍。

> [!NOTE]
> 內附的 CI 工作流程必須先在該 repository 啟用 GitHub Actions 才能執行；在被鎖定或未設定付費資訊的帳號上，每次執行都會在開始前就失敗。上述數字來自在 Python 3.14 上的本機執行，以及在另一個虛擬環境中的全新 editable 安裝。

---

## 結束代碼

| 代碼 | 意義 |
| --- | --- |
| `0` | 至少有一個貨幣對分析成功 |
| `1` | 所有貨幣對皆失敗 |
| `2` | 代號參數無效 |

---

## 貢獻

歡迎提出 issue 與 pull request。實用的貢獻方向包括新的資料供應商、額外的指標、通知管道，以及 README 翻譯。

請保持 `analysis.py` 為純函式且不含網路呼叫，並補上可離線執行的測試。

---

## 免責聲明

本專案基於公開市場資料產生技術面讀數，僅供**教育用途**。它不會告訴你該買什麼或賣什麼，也不能取代你自己的分析或持照財務顧問的建議。免費資料來源可能延遲或有誤——在依據本專案任何內容行動之前，請先向你的券商核對價格。外匯交易帶有重大虧損風險。

---

## 授權

[MIT](LICENSE)

本專案的流程架構靈感來自 [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)。這是一份針對外匯市場的獨立實作，與其不共用任何程式碼。
