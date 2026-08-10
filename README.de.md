<div align="center">

# daily_forex_analysis

**LLM-gestützte technische Analyse für Spot-FX und Metalle.**

Multi-Timeframe-Indikatoren, gemessen in Pips · Berücksichtigung der 24/5-Sessions · austauschbare Datenanbieter · eigene API-Schlüssel verwenden

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-178%20passing-brightgreen.svg)](#tests)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#tests)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#mitwirken)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) ·
[한국어](README.ko.md) ·
[Bahasa Indonesia](README.id.md) ·
[Español](README.es.md) ·
[Português](README.pt-BR.md) ·
[Français](README.fr.md) ·
**Deutsch** ·
[Русский](README.ru.md)

</div>

---

## Überblick

`daily_forex_analysis` ruft Kerzen von demjenigen Marktdatenanbieter ab, auf den Zugriff
besteht, berechnet ein technisches Bild über mehrere Zeitebenen, lässt es optional von
einem Sprachmodell interpretieren und schreibt einen Bericht, der im Terminal gelesen,
auf die Festplatte übernommen oder per Telegram versandt werden kann.

Mit Yahoo Finance läuft das Projekt **ohne jede Konfiguration und ohne API-Schlüssel**.
Jede weitere Fähigkeit — Premium-Daten, LLM-Kommentar, Benachrichtigungen — wird erst
aktiv, wenn eigene Zugangsdaten hinterlegt werden.

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

## Warum dies kein Aktienanalysator mit ausgetauschten Bezeichnungen ist

FX bringt Konventionen mit, für die es am Aktienmarkt kein Gegenstück gibt. Werden sie
falsch behandelt, ist jede Zahl auf der Seite bedeutungslos.

| | Aktien | Spot-FX | Wie dieses Projekt damit umgeht |
| --- | --- | --- | --- |
| **Bewegungseinheit** | 1 Cent ist 1 Cent | ein Pip ist 0,0001 bei EUR/USD, aber 0,01 bei USD/JPY | `instruments.py` verwaltet die Pip-Größe jedes Paares; nirgends ist `0.0001` fest verdrahtet |
| **Handelszeiten** | Eröffnung und Schluss der Börse | fortlaufend, Sonntag 21:00 → Freitag 21:00 UTC | `sessions.py` meldet die laufende Session und markiert die Überlappung London–New York |
| **Bewertung** | KGV, Gewinne, Buchwert | eine Währung hat keine Gewinne | es werden keine Fundamentaldaten erfunden |
| **Instrumentenidentität** | undurchsichtiges Kürzel (`AAPL`) | ein *Paar* aus Währungen | Symbole werden in Basis- und Kurswährung mit jeweils eigenen Konventionen zerlegt |

Eine Bewegung von 0,0010 entspricht **10 Pips** bei EUR/USD und **0,1 Pips** bei
USD/JPY. Jede Distanz in dieser Codebasis wird aus der Konvention des jeweiligen
Instruments abgeleitet.

---

## Installation

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Erfordert Python 3.9 oder neuer.

---

## Schnellstart

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

### CLI-Referenz

| Flag | Beschreibung |
| --- | --- |
| `--symbols` | Kommagetrennte Paare, z. B. `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | Teilmenge von `H1,H4,D1` |
| `--bars` | Angeforderte Kerzen pro Zeitebene (Standard `300`) |
| `--provider` | Erzwingt `twelvedata`, `alphavantage` oder `yfinance` |
| `--format` | `markdown` (Standard) oder `json` |
| `--output-dir` | Zielverzeichnis für Berichte |
| `--dry-run` | Nur analysieren und ausgeben: kein LLM-Aufruf, keine Datei, keine Benachrichtigung |
| `--no-push` | Benachrichtigungen überspringen |
| `--stdout` | Bericht zusätzlich zum Schreiben ausgeben |
| `--check` | Konfiguration und Anbieterstatus ausgeben, dann beenden |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Konfiguration

`.env.example` nach `.env` kopieren und nur das ausfüllen, was benötigt wird. Jeder Wert
kann auch als Umgebungsvariable übergeben werden.

### Datenanbieter

Die Anbieter werden der Reihe nach versucht, bis einer **alle** angeforderten Zeitebenen
bedienen kann; so vermischt ein einzelner Bericht niemals Quellen mit unterschiedlichen
Konventionen. Ein Anbieter ohne Zugangsdaten wird stillschweigend übersprungen.

| Anbieter | Zugangsdaten | Hinweise |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Native 4-Stunden-Kerzen; kostenlose Stufe verfügbar |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | Nur FX, keine Metalle; kostenlose Stufe mit Ratenbegrenzung |
| Yahoo Finance | *keine* | Standard-Fallback, kein Schlüssel erforderlich |

Mit `--provider twelvedata` oder `FOREX_PROVIDER` lässt sich ein Anbieter erzwingen.

> [!NOTE]
> Zwei Einschränkungen von Yahoo Finance, die man von Anfang an kennen sollte:
> - Yahoo kennt keine 4-Stunden-Kerze, daher wird `H4` aus Stundendaten **neu abgetastet**.
> - Yahoo liefert keine Spot-Notierung für Metalle, daher wird `XAUUSD` aus
>   **COMEX-Futures** (`GC=F`) bezogen. Futures unterliegen Basis- und Rolleffekten,
>   sodass das Niveau leicht vom Spotpreis des eigenen Brokers abweicht. Für das Lesen
>   der Struktur geeignet, nicht für die Ausführung.

### LLM-Kommentar (optional)

Jeder OpenAI-kompatible `/chat/completions`-Endpunkt funktioniert.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

`LLM_BASE_URL` auf OpenRouter, DeepSeek, Groq, Together oder einen lokalen
llama.cpp- / vLLM-Server richten — mehr ist nicht nötig. `OPENAI_API_KEY`,
`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` und `GROQ_API_KEY` werden ebenfalls akzeptiert,
ein bereits vorhandener Schlüssel muss also nicht umbenannt werden.

> [!IMPORTANT]
> Das Modell sieht niemals Rohkerzen und erzeugt niemals Zahlen. Es erhält die bereits
> berechneten Messwerte und soll sie interpretieren, wodurch jeder Preis und jedes
> Niveau deterministisch und nachprüfbar bleibt. Ohne Schlüssel wird der Bericht weiterhin
> allein aus der berechneten Analyse erstellt.

### Telegram-Versand (optional)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Einen Bot mit [@BotFather](https://t.me/BotFather) erstellen und die Chat-ID über
[@userinfobot](https://t.me/userinfobot) abrufen. Der Versand lässt sich mit `--no-push`
überspringen. Ein fehlgeschlagener Versand verwirft niemals einen Bericht, der bereits
geschrieben wurde.

### Alle Einstellungen

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `FOREX_SYMBOLS` | Majors + `XAUUSD` | Kommagetrennte Paare |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Teilmenge von H1, H4, D1 |
| `FOREX_BARS` | `300` | Angeforderte Kerzen pro Zeitebene |
| `FOREX_PROVIDER` | *automatisch* | Bevorzugter Anbietername |
| `FOREX_OUTPUT_DIR` | `reports` | Wohin Berichte geschrieben werden |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` oder `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Symbole

Alle diese Schreibweisen verweisen auf dasselbe Instrument:

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

Unterstützt werden: die Major- und Minor-Währungspaare sowie `XAUUSD` (Gold), `XAGUSD`
(Silber), `XPTUSD` (Platin) und `XPDUSD` (Palladium).

---

## Was berechnet wird

**Pro Zeitebene**

- EMA(20/50)-Trend mit einer per ATR skalierten Rauschschwelle, damit komprimierte
  Durchschnitte als *seitwärts* und nicht als falscher Trend gemeldet werden
- Wilder RSI(14)
- MACD(12/26/9)
- ATR(14) plus ein Perzentil des Volatilitätsregimes (kontrahierend / normal / expandierend)
- Bollinger- und Donchian-Kanäle
- Position innerhalb der aktuellen Range sowie Range-Breite in Pips

**Über die Zeitebenen hinweg**

Ein explizites Konfluenz-Urteil — `up`, `down`, `sideways` oder `conflicted` — mit einem
Konfidenzniveau. Die Übereinstimmung mehrerer Zeitebenen ist das nützlichste strukturelle
Signal in der diskretionären FX-Analyse und wird daher berechnet und klar benannt,
anstatt sie dem Modell zur Ableitung zu überlassen.

Jede Distanz wird in Pips gemäß der Konvention des jeweiligen Instruments angegeben.

---

## Zeitplanung

**Cron** — an jedem Wochentag um 07:00 UTC, nach der Eröffnung in London:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — ein Workflow liegt unter `.github/workflows/daily.yml` bei
(`workflow_dispatch` plus täglicher Zeitplan). Die eigenen Schlüssel als Repository-Secrets
hinterlegen, um die LLM- und Telegram-Schritte zu aktivieren; fehlende Secrets schalten
diese Funktionen einfach ab.

---

## Architektur

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

`analysis.py` ist rein: ein DataFrame geht hinein, Zahlen kommen heraus. Kein Netzwerk,
keine Konfiguration, kein LLM. Deshalb laufen die Indikatortests vollständig offline
gegen synthetische Zeitreihen.

**Fehlerisolierung ist ein Entwurfsziel.** Ein defektes Paar wird im Abschnitt „Failures“
des Berichts vermerkt, anstatt den Lauf abzubrechen. Ein fehlgeschlagener LLM-Aufruf oder
Telegram-Versand verwirft niemals einen Bericht, der bereits berechnet wurde.

### Einen Datenanbieter hinzufügen

Von `CandleProvider` ableiten, zwei Methoden implementieren und das Ergebnis an
`build_providers()` anhängen. Nichts anderes in der Codebasis muss geändert werden.

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
python -m pytest          # 178 tests
```

Kein Test greift auf das Netzwerk zu. Anbieter sind gestubbt, Kerzen sind synthetisch und
mit festem Seed erzeugt, und Indikatoren werden gegen von Hand nachrechenbare Fälle
geprüft — ein monotoner Anstieg muss RSI 100 ergeben, die True Range einer Gap-up-Kerze
muss den vorherigen Schlusskurs verwenden, derselbe ATR muss bei einem JPY-Cross in Pips
100× kleiner ausfallen.

> [!NOTE]
> Der beigelegte CI-Workflow kann erst laufen, wenn GitHub Actions für das Repository
> aktiviert ist; bei einem gesperrten oder nicht abrechnungsfähigen Konto scheitert jeder
> Lauf vor dem Start. Die oben genannten Zahlen stammen aus lokalen Läufen unter
> Python 3.14 und aus einer frischen editierbaren Installation in einer separaten
> virtuellen Umgebung.

---

## Exit-Codes

| Code | Bedeutung |
| --- | --- |
| `0` | Mindestens ein Paar wurde analysiert |
| `1` | Jedes Paar ist fehlgeschlagen |
| `2` | Ungültiges Symbolargument |

---

## Mitwirken

Issues und Pull Requests sind willkommen. Nützliche Beiträge sind unter anderem neue
Datenanbieter, zusätzliche Indikatoren, Benachrichtigungskanäle und README-Übersetzungen.

Bitte `analysis.py` rein und frei von Netzwerkaufrufen halten und Tests ergänzen, die
offline laufen.

---

## Haftungsausschluss

Dieses Projekt erzeugt technische Messwerte aus öffentlichen Marktdaten zu
**Bildungszwecken**. Es sagt nicht, was gekauft oder verkauft werden soll, und ist kein
Ersatz für eine eigene Analyse oder für eine zugelassene Finanzberatung. Kostenlose
Datenquellen können verzögert oder falsch sein — Preise vor jeder Handlung auf Basis
dieser Angaben beim Broker verifizieren. Der Handel mit Devisen birgt ein erhebliches
Verlustrisiko.

---

## Lizenz

[MIT](LICENSE)

Inspiriert von der Pipeline-Struktur von
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis).
Dies ist eine unabhängige Implementierung für FX und teilt keinen Code damit.
