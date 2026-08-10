<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**Технический анализ спотового форекса и металлов с помощью LLM.**

Мультитаймфреймовые индикаторы, измеряемые в пипсах · учёт сессий в режиме 24/5 · подключаемые поставщики данных · используйте свои собственные API-ключи

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-178%20passing-brightgreen.svg)](#тесты)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#тесты)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#как-внести-вклад)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) ·
[한국어](README.ko.md) ·
[Bahasa Indonesia](README.id.md) ·
[Español](README.es.md) ·
[Português](README.pt-BR.md) ·
[Français](README.fr.md) ·
[Deutsch](README.de.md) ·
**Русский**

</div>

---

## Обзор

`daily_forex_analysis` получает свечи от того поставщика рыночных данных, к которому у
вас есть доступ, рассчитывает мультитаймфреймовую техническую картину, при желании
просит языковую модель её истолковать и формирует отчёт, который можно прочитать в
терминале, сохранить на диск или отправить в Telegram.

Он работает **без всякой настройки и без API-ключей** через Yahoo Finance. Все
остальные возможности — платные данные, комментарий от LLM, уведомления —
активируются только тогда, когда вы предоставите собственные учётные данные.

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

## Почему это не анализатор акций с переименованными подписями

На форексе действуют соглашения, которым нет аналога на рынке акций. Ошибка в них
делает бессмысленным каждое число в отчёте.

| | Акции | Спотовый форекс | Как это решено в проекте |
| --- | --- | --- | --- |
| **Единица движения** | 1 цент — это 1 цент | пипс равен 0,0001 на EUR/USD, но 0,01 на USD/JPY | `instruments.py` хранит размер пипса для каждой пары; значение `0.0001` нигде не задано жёстко |
| **Часы торговли** | открытие и закрытие биржи | непрерывно, с воскресенья 21:00 до пятницы 21:00 UTC | `sessions.py` сообщает текущую сессию и отмечает пересечение Лондона и Нью-Йорка |
| **Оценка стоимости** | P/E, прибыль, балансовая стоимость | у валюты нет прибыли | никакие фундаментальные показатели не придумываются |
| **Идентичность инструмента** | непрозрачный тикер (`AAPL`) | *пара* валют | символы разбираются на базовую и котируемую валюту с их собственными соглашениями |

Движение на 0,0010 — это **10 пипсов** на EUR/USD и **0,1 пипса** на USD/JPY. Любое
расстояние в этом коде выводится из соглашения самого инструмента.

---

## Установка

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Требуется Python 3.9 или новее.

---

## Быстрый старт

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

### Справочник по CLI

| Флаг | Описание |
| --- | --- |
| `--symbols` | Пары через запятую, например `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | Подмножество `H1,H4,D1` |
| `--bars` | Количество запрашиваемых свечей на таймфрейм (по умолчанию `300`) |
| `--provider` | Принудительно выбрать `twelvedata`, `alphavantage` или `yfinance` |
| `--format` | `markdown` (по умолчанию) или `json` |
| `--output-dir` | Каталог для сохранения отчётов |
| `--dry-run` | Только анализ и вывод: без вызова LLM, без файла, без уведомления |
| `--no-push` | Не отправлять уведомления |
| `--stdout` | Выводить отчёт в терминал в дополнение к записи в файл |
| `--check` | Показать конфигурацию и состояние поставщиков и выйти |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Конфигурация

Скопируйте `.env.example` в `.env` и заполните только то, что вам нужно. Любое значение
можно также передать через переменную окружения.

### Поставщики данных

Поставщики опрашиваются по порядку, пока один из них не покроет **все** запрошенные
таймфреймы, поэтому в одном отчёте никогда не смешиваются источники с разными
соглашениями. Поставщик без учётных данных молча пропускается.

| Поставщик | Учётные данные | Примечания |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Родные 4-часовые свечи; доступен бесплатный тариф |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | Только форекс, без металлов; бесплатный тариф с ограничением частоты запросов |
| Yahoo Finance | *нет* | Резервный вариант по умолчанию, ключ не требуется |

Выбрать конкретного можно через `--provider twelvedata` или `FOREX_PROVIDER`.

> [!NOTE]
> Две особенности Yahoo Finance, о которых стоит знать заранее:
> - У Yahoo нет 4-часовой свечи, поэтому `H4` **пересчитывается** из часовых данных.
> - У Yahoo нет спотовой котировки на металлы, поэтому `XAUUSD` берётся из **фьючерсов
>   COMEX** (`GC=F`). Фьючерсы несут в себе базис и эффекты роллирования, поэтому
>   уровень немного отличается от спотовой цены вашего брокера. Годится для чтения
>   структуры, но не для исполнения сделок.

### Комментарий от LLM (необязательно)

Подойдёт любая конечная точка `/chat/completions`, совместимая с OpenAI.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

Направьте `LLM_BASE_URL` на OpenRouter, DeepSeek, Groq, Together или локальный сервер
llama.cpp / vLLM — больше ничего менять не нужно. Принимаются `OPENAI_API_KEY`,
`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` и `GROQ_API_KEY`, так что переименовывать уже
имеющийся у вас ключ не придётся.

> [!IMPORTANT]
> Модель никогда не видит сырые свечи и никогда не производит числа. Она получает уже
> рассчитанные показания и должна их истолковать, благодаря чему каждая цена и каждый
> уровень остаются детерминированными и проверяемыми. Без ключа отчёт всё равно
> формируется — только на основе расчётного анализа.

### Отправка в Telegram (необязательно)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Создайте бота через [@BotFather](https://t.me/BotFather) и получите свой chat id у
[@userinfobot](https://t.me/userinfobot). Отключить отправку можно флагом `--no-push`.
Неудачная отправка никогда не приводит к потере уже записанного отчёта.

### Все настройки

| Переменная | По умолчанию | Значение |
| --- | --- | --- |
| `FOREX_SYMBOLS` | основные пары + `XAUUSD` | Пары через запятую |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Подмножество H1, H4, D1 |
| `FOREX_BARS` | `300` | Количество запрашиваемых свечей на таймфрейм |
| `FOREX_PROVIDER` | *авто* | Имя предпочитаемого поставщика |
| `FOREX_OUTPUT_DIR` | `reports` | Куда записываются отчёты |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` или `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Символы

Все эти варианты написания указывают на один и тот же инструмент:

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

Поддерживаются: основные и второстепенные валютные кроссы, а также `XAUUSD` (золото),
`XAGUSD` (серебро), `XPTUSD` (платина) и `XPDUSD` (палладий).

---

## Что рассчитывается

**По каждому таймфрейму**

- Тренд по EMA(20/50) с шумовым порогом, масштабированным по ATR, чтобы сжатые средние
  отмечались как *боковик*, а не как ложный тренд
- RSI(14) по Уайлдеру
- MACD(12/26/9)
- ATR(14) плюс процентиль режима волатильности (сжатие / норма / расширение)
- Каналы Bollinger и Donchian
- Положение внутри недавнего диапазона и ширина диапазона в пипсах

**Между таймфреймами**

Явный вердикт о совпадении — `up`, `down`, `sideways` или `conflicted` — с уровнем
уверенности. Согласие между таймфреймами — самый полезный структурный сигнал в
дискреционном анализе форекса, поэтому он рассчитывается и указывается прямо, а не
оставляется модели на догадки.

Любое расстояние выражается в пипсах согласно соглашению самого инструмента.

---

## Планирование запусков

**Cron** — каждый рабочий день в 07:00 UTC, после открытия Лондона:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — рабочий процесс включён в комплект по пути
`.github/workflows/daily.yml` (`workflow_dispatch` плюс ежедневное расписание). Добавьте
свои ключи в секреты репозитория, чтобы включить шаги с LLM и Telegram; отсутствующие
секреты просто отключают эти функции.

---

## Архитектура

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

`analysis.py` — чистый модуль: на входе DataFrame, на выходе числа. Ни сети, ни
конфигурации, ни LLM. Именно поэтому тесты индикаторов выполняются полностью офлайн на
синтетических рядах.

**Изоляция сбоев — одна из целей проектирования.** Одна сломавшаяся пара попадает в
раздел отчёта Failures, а не обрывает весь запуск. Неудачный вызов LLM или отправка в
Telegram никогда не приводят к потере уже рассчитанного отчёта.

### Добавление поставщика данных

Создайте подкласс `CandleProvider`, реализуйте два метода и добавьте его в
`build_providers()`. Больше ничего в коде менять не нужно.

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

## Тесты

```bash
python -m pytest          # 178 tests
```

Ни один тест не обращается к сети. Поставщики подменяются заглушками, свечи
синтетические и с фиксированным сидом, а индикаторы проверяются на случаях, считаемых
вручную: монотонный рост должен давать RSI 100, истинный диапазон свечи с гэпом вверх
должен использовать предыдущее закрытие, тот же ATR на кроссе с JPY должен быть в 100
раз меньше в пипсах.

> [!NOTE]
> Входящий в комплект CI-процесс не может запуститься, пока в репозитории не включены
> GitHub Actions; на заблокированном аккаунте или аккаунте без оплаты каждый запуск
> падает ещё до старта. Приведённые выше показатели получены из локальных запусков на
> Python 3.14 и из чистой editable-установки в отдельном виртуальном окружении.

---

## Коды выхода

| Код | Значение |
| --- | --- |
| `0` | Проанализирована хотя бы одна пара |
| `1` | Все пары завершились ошибкой |
| `2` | Некорректный аргумент символа |

---

## Как внести вклад

Issues и pull request'ы приветствуются. Полезный вклад — это новые поставщики данных,
дополнительные индикаторы, каналы уведомлений и переводы README.

Пожалуйста, сохраняйте `analysis.py` чистым и без сетевых вызовов и добавляйте тесты,
которые работают офлайн.

---

## Отказ от ответственности

Этот проект формирует технические показания на основе публичных рыночных данных
**в образовательных целях**. Он не говорит вам, что покупать или продавать, и не
заменяет ни ваш собственный анализ, ни лицензированного финансового консультанта.
Бесплатные источники данных могут отставать или ошибаться — сверяйте цены с вашим
брокером, прежде чем что-либо предпринимать на основе этих данных. Торговля на рынке
иностранной валюты сопряжена со значительным риском убытков.

---

## Лицензия

[MIT](LICENSE)

Идея структуры конвейера вдохновлена проектом
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis).
Это независимая реализация для форекса, не содержащая его кода.
