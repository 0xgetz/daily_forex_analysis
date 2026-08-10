<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**スポットFXと貴金属のためのLLM支援テクニカル分析。**

pips単位で計測するマルチタイムフレーム指標 · 24/5セッション認識 · 差し替え可能なデータプロバイダ · APIキーは各自で用意

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-214%20passing-brightgreen.svg)](#テスト)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#テスト)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#コントリビューション)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md) ·
**日本語** ·
[한국어](README.ko.md) ·
[Bahasa Indonesia](README.id.md) ·
[Español](README.es.md) ·
[Português](README.pt-BR.md) ·
[Français](README.fr.md) ·
[Deutsch](README.de.md) ·
[Русский](README.ru.md)

</div>

---

## 概要

`daily_forex_analysis` は、利用可能なマーケットデータプロバイダからローソク足を取得し、
マルチタイムフレームのテクニカルな全体像を計算し、必要に応じて言語モデルにその解釈を依頼して、
ターミナルで読める・ディスクにコミットできる・Telegramへ送信できるレポートを出力する。

Yahoo Finance を使えば **設定ゼロ・APIキー不要** で動作する。それ以外の機能 —
プレミアムデータ、LLMによるコメント、通知 — は、自分の認証情報を与えたときにのみ有効化される。

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

## これがラベルだけ変えた株式アナライザではない理由

FXには株式に対応物のない慣習がある。それを取り違えると、ページ上のあらゆる数値が無意味になる。

| | 株式 | スポットFX | 本プロジェクトでの扱い |
| --- | --- | --- | --- |
| **値動きの単位** | 1セントは1セント | 1 pip は EUR/USD では 0.0001 だが USD/JPY では 0.01 | `instruments.py` が各ペアの pip サイズを管理する。`0.0001` をハードコードする箇所はない |
| **取引時間** | 取引所の寄り付きと引け | 連続取引、日曜 21:00 → 金曜 21:00 UTC | `sessions.py` が現在のセッションを報告し、ロンドン・ニューヨークの重複時間帯を明示する |
| **バリュエーション** | PER、利益、簿価 | 通貨に利益は存在しない | ファンダメンタルズを捏造しない |
| **銘柄の同一性** | 不透明なティッカー（`AAPL`） | 通貨の*ペア* | シンボルは基軸通貨と決済通貨に分解され、それぞれの慣習を持つ |

0.0010 の値動きは EUR/USD では **10 pips**、USD/JPY では **0.1 pips** である。
本コードベースにおけるすべての距離は、その銘柄自身の慣習から導出される。

---

## インストール

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Python 3.9 以降が必要。

---

## クイックスタート

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

### CLIリファレンス

| フラグ | 説明 |
| --- | --- |
| `--symbols` | カンマ区切りの通貨ペア。例: `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | `H1,H4,D1` の部分集合 |
| `--bars` | タイムフレームごとに取得するローソク足の本数（デフォルト `300`） |
| `--provider` | `twelvedata`、`alphavantage`、`yfinance` を強制指定する |
| `--format` | `markdown`（デフォルト）または `json` |
| `--output-dir` | レポートの出力先ディレクトリ |
| `--dry-run` | 分析と表示のみ: LLM呼び出しなし、ファイル出力なし、通知なし |
| `--no-push` | 通知をスキップする |
| `--stdout` | レポートをファイル出力するとともに標準出力にも表示する |
| `--check` | 設定とプロバイダの状態を表示して終了する |
| `--log-level` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |

---

## 設定

`.env.example` を `.env` にコピーし、必要な項目だけを埋める。すべての値は環境変数として
与えることもできる。

### データプロバイダ

プロバイダは、要求された**すべての**タイムフレームを満たすものが見つかるまで順に試される。
そのため単一のレポート内で慣習の異なるソースが混在することはない。認証情報のないプロバイダは
黙ってスキップされる。

| プロバイダ | 認証情報 | 備考 |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | ネイティブな4時間足あり。無料プランが利用可能 |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | FXのみ、貴金属は非対応。無料プランはレート制限あり |
| Yahoo Finance | *なし* | デフォルトのフォールバック。キー不要 |

`--provider twelvedata` または `FOREX_PROVIDER` で強制指定できる。

> [!NOTE]
> Yahoo Finance について、あらかじめ知っておくべき2つの注意点:
> - Yahoo には4時間足が存在しないため、`H4` は1時間足から**リサンプリング**される。
> - Yahoo にはスポット貴金属のレートがないため、`XAUUSD` は **COMEX先物**（`GC=F`）から
>   提供される。先物にはベーシスとロールの影響があるため、水準はブローカーのスポット価格と
>   わずかに異なる。構造を読む用途には十分だが、執行には向かない。

### LLMによるコメント（任意）

OpenAI互換の `/chat/completions` エンドポイントであれば何でも動作する。

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

`LLM_BASE_URL` を OpenRouter、DeepSeek、Groq、Together、あるいはローカルの
llama.cpp / vLLM サーバに向けるだけでよく、他は何も変えなくてよい。`OPENAI_API_KEY`、
`OPENROUTER_API_KEY`、`DEEPSEEK_API_KEY`、`GROQ_API_KEY` はいずれも受け付けられるので、
すでに持っているキーの名前を変える必要はない。

> [!IMPORTANT]
> モデルが生のローソク足を見ることはなく、数値を生成することもない。モデルは計算済みの
> 数値を受け取り、その解釈を求められるだけである。これにより、あらゆる価格と水準は
> 決定論的で監査可能なまま保たれる。キーがなくても、計算による分析だけからレポートは
> 生成される。

### Telegram送信（任意）

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

[@BotFather](https://t.me/BotFather) でボットを作成し、chat id は
[@userinfobot](https://t.me/userinfobot) から取得する。送信をスキップするには `--no-push` を使う。
送信に失敗しても、すでに書き出されたレポートが破棄されることはない。

### 全設定項目

| 変数 | デフォルト | 意味 |
| --- | --- | --- |
| `FOREX_SYMBOLS` | メジャー通貨 + `XAUUSD` | カンマ区切りの通貨ペア |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | H1, H4, D1 の部分集合 |
| `FOREX_BARS` | `300` | タイムフレームごとに取得するローソク足の本数 |
| `FOREX_PROVIDER` | *自動* | 優先するプロバイダ名 |
| `FOREX_OUTPUT_DIR` | `reports` | レポートの出力先 |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` または `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |

---

## シンボル

以下の表記はすべて同一の銘柄として解決される:

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

対応: メジャーおよびマイナーのクロス通貨、加えて `XAUUSD`（金）、`XAGUSD`（銀）、
`XPTUSD`（プラチナ）、`XPDUSD`（パラジウム）。

---

## 計算される内容

**タイムフレームごと**

- EMA(20/50) によるトレンド判定。ATRでスケールしたノイズ下限を持たせ、圧縮した移動平均は
  誤ったトレンドではなく*レンジ*として報告される
- Wilder方式の RSI(14)
- MACD(12/26/9)
- ATR(14) と、ボラティリティ・レジームのパーセンタイル（収縮 / 通常 / 拡大）
- Bollinger バンドと Donchian チャネル
- 直近レンジ内での位置、および pips 単位のレンジ幅

**タイムフレーム横断**

`up`、`down`、`sideways`、`conflicted` のいずれかによる明示的なコンフルエンス判定と、
その確信度。マルチタイムフレームの一致は裁量的なFX分析において最も有用な構造的シグナルで
あるため、モデルの推測に委ねるのではなく、計算して平明に明示している。

すべての距離は、その銘柄自身の慣習に従って pips で表される。

---

## スケジューリング

**Cron** — 平日ごと、ロンドン市場オープン後の 07:00 UTC:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — `.github/workflows/daily.yml` にワークフローを同梱している
（`workflow_dispatch` と日次スケジュール）。LLM と Telegram のステップを有効にするには、
リポジトリシークレットとしてキーを追加する。シークレットがなければ、それらの機能は単に
無効化される。

---

## アーキテクチャ

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

`analysis.py` は純粋である: DataFrame が入り、数値が出る。ネットワークも設定もLLMもない。
だからこそ指標のテストは合成系列に対して完全にオフラインで実行できる。

**障害の隔離は設計目標である。** ひとつのペアが壊れても、実行を中断するのではなく、
レポートの Failures セクションに記録される。LLM呼び出しやTelegram送信の失敗が、
すでに計算済みのレポートを破棄することはない。

### データプロバイダの追加

`CandleProvider` をサブクラス化し、2つのメソッドを実装して、`build_providers()` に追加する。
コードベースの他の部分を変更する必要はない。

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

## テスト

```bash
python -m pytest          # 214 tests
```

ネットワークに触れるテストはひとつもない。プロバイダはスタブ化され、ローソク足は合成かつ
シード固定であり、指標は手計算可能なケースに対して検証されている — 単調上昇なら RSI は 100
にならなければならない、ギャップアップしたローソク足の true range は前日終値を使わなければ
ならない、同じATRがJPYクロスでは pips 換算で 100 分の 1 と表示されなければならない、など。

> [!NOTE]
> 同梱のCIワークフローは、リポジトリで GitHub Actions が有効になるまで実行できない。
> ロックされたアカウントや課金設定のないアカウントでは、すべての実行が開始前に失敗する。
> 上記の件数は Python 3.14 でのローカル実行と、別の仮想環境でのクリーンな editable
> インストールによるものである。

---

## 終了コード

| コード | 意味 |
| --- | --- |
| `0` | 少なくとも1つのペアが分析された |
| `1` | すべてのペアが失敗した |
| `2` | シンボル引数が不正 |

---

## コントリビューション

Issue と Pull Request を歓迎する。有用な貢献としては、新しいデータプロバイダ、追加の指標、
通知チャネル、READMEの翻訳などが挙げられる。

`analysis.py` は純粋でネットワーク呼び出しを含まない状態に保ち、オフラインで実行できる
テストを追加してほしい。

---

## 免責事項

本プロジェクトは、公開マーケットデータから**教育目的で**テクニカルな読み取りを生成する。
何を買うべきか売るべきかを指示するものではなく、自身の分析や有資格のファイナンシャル
アドバイザーの代わりになるものでもない。無料のデータソースは遅延したり誤っていたりする
ことがある — ここでの内容に基づいて行動する前に、ブローカーで価格を確認すること。
外国為替取引には多大な損失リスクが伴う。

---

## ライセンス

[MIT](LICENSE)

[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) の
パイプライン構造に着想を得ている。本プロジェクトはFX向けの独立した実装であり、
コードを共有していない。
