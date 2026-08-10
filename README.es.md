<div align="center">

# daily_forex_analysis

**Análisis técnico asistido por LLM para forex spot y metales.**

Indicadores multi-timeframe medidos en pips · conciencia de las sesiones 24/5 · proveedores de datos intercambiables · usa tus propias API keys

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-178%20passing-brightgreen.svg)](#pruebas)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#pruebas)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#contribuciones)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) ·
[한국어](README.ko.md) ·
[Bahasa Indonesia](README.id.md) ·
**Español** ·
[Português](README.pt-BR.md) ·
[Français](README.fr.md) ·
[Deutsch](README.de.md) ·
[Русский](README.ru.md)

</div>

---

## Resumen

`daily_forex_analysis` obtiene velas del proveedor de datos de mercado al que se tenga
acceso, calcula un panorama técnico multi-timeframe, opcionalmente pide a un modelo de
lenguaje que lo interprete y escribe un informe que se puede leer en la terminal,
guardar en disco o enviar a Telegram.

Funciona **sin configuración y sin API keys** usando Yahoo Finance. Cualquier otra
capacidad — datos premium, comentario del LLM, notificaciones — se activa únicamente
al proporcionar credenciales propias.

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

## Por qué esto no es un analizador de acciones con las etiquetas cambiadas

El forex tiene convenciones que no tienen equivalente en renta variable. Manejarlas mal
vuelve carente de sentido cada número de la página.

| | Renta variable | Forex spot | Cómo lo maneja este proyecto |
| --- | --- | --- | --- |
| **Unidad de movimiento** | 1 centavo es 1 centavo | un pip es 0,0001 en EUR/USD pero 0,01 en USD/JPY | `instruments.py` define el tamaño de pip de cada par; nada codifica `0.0001` de forma rígida |
| **Horario de negociación** | apertura y cierre de la bolsa | continuo, domingo 21:00 → viernes 21:00 UTC | `sessions.py` informa la sesión activa y señala el solapamiento Londres–Nueva York |
| **Valoración** | P/E, beneficios, valor en libros | una divisa no tiene beneficios | no se inventan datos fundamentales |
| **Identidad del instrumento** | ticker opaco (`AAPL`) | un *par* de divisas | los símbolos se descomponen en base y cotizada, cada una con sus convenciones |

Un movimiento de 0,0010 son **10 pips** en EUR/USD y **0,1 pips** en USD/JPY. Cada
distancia en este código se deriva de la convención propia del instrumento.

---

## Instalación

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Requiere Python 3.9 o superior.

---

## Inicio rápido

```bash
# Muestra la configuración y qué proveedores se pueden usar — sin red
python main.py --check

# Analiza la watchlist por defecto, imprime en stdout, no escribe nada
python main.py --dry-run

# Tus pares, tus timeframes, escritos en reports/
python main.py --symbols EURUSD,GBPUSD,XAUUSD --timeframes H1,H4,D1

# Salida legible por máquina
python main.py --symbols EURUSD --format json
```

### Referencia de la CLI

| Flag | Descripción |
| --- | --- |
| `--symbols` | Pares separados por comas, por ejemplo `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | Subconjunto de `H1,H4,D1` |
| `--bars` | Velas solicitadas por timeframe (por defecto `300`) |
| `--provider` | Fuerza `twelvedata`, `alphavantage` o `yfinance` |
| `--format` | `markdown` (por defecto) o `json` |
| `--output-dir` | Directorio de destino de los informes |
| `--dry-run` | Solo analiza e imprime: sin llamada al LLM, sin archivo, sin notificación |
| `--no-push` | Omite las notificaciones |
| `--stdout` | Imprime el informe además de escribirlo |
| `--check` | Imprime la configuración y el estado de los proveedores, y termina |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Configuración

Copia `.env.example` a `.env` y completa solo lo necesario. Cada valor también puede
proporcionarse como variable de entorno.

### Proveedores de datos

Los proveedores se prueban en orden hasta que uno satisface **todos** los timeframes
solicitados, de modo que un informe nunca mezcla fuentes con convenciones distintas. Un
proveedor sin credenciales se omite en silencio.

| Proveedor | Credencial | Notas |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Velas de 4 horas nativas; hay plan gratuito |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | Solo forex, sin metales; plan gratuito con límite de peticiones |
| Yahoo Finance | *ninguna* | Fallback por defecto, no requiere key |

Se puede forzar uno con `--provider twelvedata` o `FOREX_PROVIDER`.

> [!NOTE]
> Dos advertencias sobre Yahoo Finance que conviene conocer de entrada:
> - Yahoo no tiene vela de 4 horas, así que `H4` se **remuestrea** a partir de datos horarios.
> - Yahoo no tiene cotización spot de metales, así que `XAUUSD` se sirve desde **futuros
>   de COMEX** (`GC=F`). Los futuros arrastran efectos de base y de roll, por lo que el
>   nivel difiere ligeramente del precio spot de tu bróker. Sirve para leer estructura,
>   no para ejecutar.

### Comentario del LLM (opcional)

Funciona con cualquier endpoint `/chat/completions` compatible con OpenAI.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

Apunta `LLM_BASE_URL` a OpenRouter, DeepSeek, Groq, Together o un servidor local de
llama.cpp / vLLM y no cambia nada más. `OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
`DEEPSEEK_API_KEY` y `GROQ_API_KEY` se aceptan todas, así que no hace falta renombrar
una key que ya se tenga.

> [!IMPORTANT]
> El modelo nunca ve velas crudas y nunca produce números. Recibe las lecturas ya
> calculadas y se le pide interpretarlas, lo que mantiene cada precio y cada nivel
> deterministas y auditables. Sin una key, el informe se genera igualmente solo a partir
> del análisis calculado.

### Envío a Telegram (opcional)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Crea un bot con [@BotFather](https://t.me/BotFather) y obtén tu chat id en
[@userinfobot](https://t.me/userinfobot). El envío se omite con `--no-push`. Un envío
fallido nunca descarta un informe que ya se había escrito.

### Todos los ajustes

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `FOREX_SYMBOLS` | majors + `XAUUSD` | Pares separados por comas |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Subconjunto de H1, H4, D1 |
| `FOREX_BARS` | `300` | Velas solicitadas por timeframe |
| `FOREX_PROVIDER` | *automático* | Nombre del proveedor preferido |
| `FOREX_OUTPUT_DIR` | `reports` | Dónde se escriben los informes |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` o `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Símbolos

Todas estas escrituras resuelven al mismo instrumento:

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

Soportados: los cruces de divisas mayores y menores, más `XAUUSD` (oro), `XAGUSD`
(plata), `XPTUSD` (platino) y `XPDUSD` (paladio).

---

## Qué se calcula

**Por timeframe**

- Tendencia por EMA(20/50), con un umbral de ruido escalado por ATR para que las medias
  comprimidas se informen como *sideways* en lugar de como una tendencia falsa
- Wilder RSI(14)
- MACD(12/26/9)
- ATR(14) más un percentil de régimen de volatilidad (contracción / normal / expansión)
- Canales de Bollinger y Donchian
- Posición dentro del rango reciente y anchura del rango en pips

**Entre timeframes**

Un veredicto de confluencia explícito — `up`, `down`, `sideways` o `conflicted` — con un
nivel de confianza. La coincidencia entre timeframes es la señal estructural más útil en
el análisis discrecional de forex, por lo que se calcula y se enuncia con claridad en
lugar de dejarla a la inferencia del modelo.

Cada distancia se expresa en pips usando la convención propia del instrumento.

---

## Programación

**Cron** — cada día laborable a las 07:00 UTC, después de la apertura de Londres:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — se incluye un workflow en `.github/workflows/daily.yml`
(`workflow_dispatch` más una programación diaria). Añade tus keys como secrets del
repositorio para habilitar los pasos de LLM y Telegram; los secrets ausentes simplemente
desactivan esas funciones.

---

## Arquitectura

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

`analysis.py` es puro: entra un DataFrame, salen números. Sin red, sin configuración,
sin LLM. Por eso las pruebas de indicadores se ejecutan íntegramente offline contra
series sintéticas.

**El aislamiento de fallos es un objetivo de diseño.** Un par roto se registra en la
sección de Fallos del informe en vez de abortar la ejecución. Una llamada al LLM o un
envío a Telegram fallidos nunca descartan un informe que ya se había calculado.

### Añadir un proveedor de datos

Hereda de `CandleProvider`, implementa dos métodos y añádelo a `build_providers()`.
Nada más en el código necesita cambiar.

```python
from forex.providers import CandleProvider

class MyProvider(CandleProvider):
    name = "myprovider"

    def is_available(self) -> bool:
        return bool(os.getenv("MY_API_KEY"))

    def fetch(self, instrument, timeframe, bars):
        ...  # devuelve un DataFrame con open/high/low/close
```

---

## Pruebas

```bash
python -m pytest          # 178 pruebas
```

Ninguna prueba toca la red. Los proveedores se sustituyen por stubs, las velas son
sintéticas y con semilla fija, y los indicadores se verifican contra casos calculables a
mano: una subida monótona debe dar RSI 100, el true range de una vela con gap al alza
debe usar el cierre anterior, y el mismo ATR debe leerse 100× más pequeño en pips en un
cruce con JPY.

> [!NOTE]
> El workflow de CI incluido no puede ejecutarse hasta que GitHub Actions esté habilitado
> en el repositorio; en una cuenta bloqueada o sin facturación, cada ejecución falla antes
> de comenzar. Los recuentos anteriores provienen de ejecuciones locales en Python 3.14 y
> de una instalación editable limpia en un entorno virtual aparte.

---

## Códigos de salida

| Código | Significado |
| --- | --- |
| `0` | Al menos un par se analizó |
| `1` | Todos los pares fallaron |
| `2` | Argumento de símbolo no válido |

---

## Contribuciones

Los issues y pull requests son bienvenidos. Entre las contribuciones útiles están nuevos
proveedores de datos, indicadores adicionales, canales de notificación y traducciones del
README.

Por favor, mantén `analysis.py` puro y libre de llamadas de red, y añade pruebas que se
ejecuten offline.

---

## Aviso legal

Este proyecto produce lecturas técnicas a partir de datos públicos de mercado con
**fines educativos**. No indica qué comprar o vender, y no sustituye tu propio análisis
ni a un asesor financiero autorizado. Las fuentes de datos gratuitas pueden estar
retrasadas o ser erróneas: verifica los precios con tu bróker antes de actuar en base a
cualquier cosa de aquí. Operar en el mercado de divisas conlleva un riesgo sustancial de
pérdida.

---

## Licencia

[MIT](LICENSE)

Inspirado en la estructura del pipeline de
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis).
Esta es una implementación independiente para forex y no comparte código con ella.
