<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**Análise técnica assistida por LLM para forex spot e metais.**

Indicadores multi-timeframe medidos em pips · consciência das sessões 24/5 · provedores de dados plugáveis · use suas próprias chaves de API

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-178%20passing-brightgreen.svg)](#testes)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#testes)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#contribuindo)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) ·
[한국어](README.ko.md) ·
[Bahasa Indonesia](README.id.md) ·
[Español](README.es.md) ·
**Português** ·
[Français](README.fr.md) ·
[Deutsch](README.de.md) ·
[Русский](README.ru.md)

</div>

---

## Visão geral

`daily_forex_analysis` busca candles em qualquer provedor de dados de mercado a que você
tenha acesso, calcula um panorama técnico multi-timeframe, opcionalmente pede a um
modelo de linguagem que o interprete e escreve um relatório que você pode ler no
terminal, versionar em disco ou enviar para o Telegram.

Ele funciona com **zero configuração e sem nenhuma chave de API** usando o Yahoo
Finance. Todos os outros recursos — dados premium, comentários do LLM, notificações — só
são ativados quando você fornece as suas próprias credenciais.

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

## Por que isto não é um analisador de ações com os rótulos trocados

O forex tem convenções que não possuem equivalente no mercado de ações. Errar nelas
torna sem sentido todos os números da página.

| | Ações | Forex spot | Como este projeto lida com isso |
| --- | --- | --- | --- |
| **Unidade de movimento** | 1 centavo é 1 centavo | um pip é 0,0001 no EUR/USD, mas 0,01 no USD/JPY | `instruments.py` é responsável pelo tamanho do pip de cada par; nada deixa `0.0001` fixo no código |
| **Horário de negociação** | abertura e fechamento da bolsa | contínuo, domingo 21:00 → sexta 21:00 UTC | `sessions.py` informa a sessão ativa e sinaliza a sobreposição Londres–Nova York |
| **Valuation** | P/L, lucros, valor patrimonial | uma moeda não tem lucros | nenhum fundamento é inventado |
| **Identidade do instrumento** | ticker opaco (`AAPL`) | um *par* de moedas | os símbolos são analisados em base e cotação, cada um com suas convenções |

Um movimento de 0,0010 equivale a **10 pips** no EUR/USD e a **0,1 pip** no USD/JPY.
Toda distância nesta base de código é derivada da convenção do próprio instrumento.

---

## Instalação

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Requer Python 3.9 ou mais recente.

---

## Início rápido

```bash
# Mostra a configuração e quais provedores estão utilizáveis — sem precisar de rede
python main.py --check

# Analisa a watchlist padrão, imprime no stdout, não escreve nada
python main.py --dry-run

# Seus pares, seus timeframes, escritos em reports/
python main.py --symbols EURUSD,GBPUSD,XAUUSD --timeframes H1,H4,D1

# Saída legível por máquina
python main.py --symbols EURUSD --format json
```

### Referência da CLI

| Flag | Descrição |
| --- | --- |
| `--symbols` | Pares separados por vírgula, por exemplo `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | Subconjunto de `H1,H4,D1` |
| `--bars` | Candles solicitados por timeframe (padrão `300`) |
| `--provider` | Força `twelvedata`, `alphavantage` ou `yfinance` |
| `--format` | `markdown` (padrão) ou `json` |
| `--output-dir` | Diretório de destino dos relatórios |
| `--dry-run` | Apenas analisa e imprime: sem chamada ao LLM, sem arquivo, sem notificação |
| `--no-push` | Ignora as notificações |
| `--stdout` | Imprime o relatório além de gravá-lo |
| `--check` | Imprime a configuração e o status dos provedores, então encerra |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Configuração

Copie `.env.example` para `.env` e preencha apenas o que você precisa. Todo valor também
pode ser fornecido como variável de ambiente.

### Provedores de dados

Os provedores são testados em ordem até que um atenda a **todos** os timeframes
solicitados, de modo que um único relatório nunca mistura fontes com convenções
diferentes. Um provedor sem credenciais é ignorado silenciosamente.

| Provedor | Credencial | Observações |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Candles nativos de 4 horas; há camada gratuita |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | Apenas forex, sem metais; camada gratuita com limite de requisições |
| Yahoo Finance | *nenhuma* | Fallback padrão, não exige chave |

Force um deles com `--provider twelvedata` ou `FOREX_PROVIDER`.

> [!NOTE]
> Duas ressalvas sobre o Yahoo Finance que vale conhecer desde já:
> - O Yahoo não tem candle de 4 horas, então `H4` é **reamostrado** a partir dos dados horários.
> - O Yahoo não tem cotação spot de metais, então `XAUUSD` é servido a partir dos
>   **futuros da COMEX** (`GC=F`). Futuros carregam efeitos de base e rolagem, por isso o
>   nível difere levemente do preço spot da sua corretora. Serve para ler estrutura, não
>   para execução.

### Comentários do LLM (opcional)

Qualquer endpoint `/chat/completions` compatível com a OpenAI funciona.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

Aponte `LLM_BASE_URL` para OpenRouter, DeepSeek, Groq, Together ou um servidor local
llama.cpp / vLLM e nada mais muda. `OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
`DEEPSEEK_API_KEY` e `GROQ_API_KEY` são todas aceitas, então você não precisa renomear
uma chave que já possui.

> [!IMPORTANT]
> O modelo nunca vê candles brutos e nunca produz números. Ele recebe as leituras já
> calculadas e é solicitado a interpretá-las, o que mantém todo preço e nível
> determinístico e auditável. Sem uma chave, o relatório continua sendo produzido apenas
> a partir da análise calculada.

### Envio para o Telegram (opcional)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Crie um bot com o [@BotFather](https://t.me/BotFather) e obtenha o seu chat id com o
[@userinfobot](https://t.me/userinfobot). Pule o envio com `--no-push`. Um envio que
falha nunca descarta um relatório que já foi escrito.

### Todas as configurações

| Variável | Padrão | Significado |
| --- | --- | --- |
| `FOREX_SYMBOLS` | majors + `XAUUSD` | Pares separados por vírgula |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Subconjunto de H1, H4, D1 |
| `FOREX_BARS` | `300` | Candles solicitados por timeframe |
| `FOREX_PROVIDER` | *automático* | Nome do provedor preferido |
| `FOREX_OUTPUT_DIR` | `reports` | Onde os relatórios são escritos |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` ou `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Símbolos

Todas estas grafias resolvem para o mesmo instrumento:

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

Suportados: os pares de moedas majors e minors, além de `XAUUSD` (ouro), `XAGUSD`
(prata), `XPTUSD` (platina) e `XPDUSD` (paládio).

---

## O que é calculado

**Por timeframe**

- Tendência de EMA(20/50), com um piso de ruído escalado por ATR, para que médias
  comprimidas sejam reportadas como *sideways* em vez de como uma tendência falsa
- Wilder RSI(14)
- MACD(12/26/9)
- ATR(14) mais um percentil de regime de volatilidade (contraindo / normal / expandindo)
- Canais de Bollinger e Donchian
- Posição dentro do range recente e largura do range em pips

**Entre timeframes**

Um veredito explícito de confluência — `up`, `down`, `sideways` ou `conflicted` — com um
nível de confiança. A concordância entre timeframes é o sinal estrutural mais útil na
análise discricionária de forex, por isso ela é calculada e declarada de forma direta em
vez de ser deixada para o modelo inferir.

Toda distância é expressa em pips usando a convenção do próprio instrumento.

---

## Agendamento

**Cron** — todo dia útil às 07:00 UTC, após a abertura de Londres:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — um workflow está incluído em `.github/workflows/daily.yml`
(`workflow_dispatch` mais um agendamento diário). Adicione suas chaves como repository
secrets para habilitar as etapas de LLM e Telegram; secrets ausentes simplesmente
desativam esses recursos.

---

## Arquitetura

```
forex/
├── instruments.py   parsing de símbolos, convenções de pip
├── sessions.py      horário de mercado 24/5, sessões Tóquio/Londres/Nova York
├── providers.py     fontes de dados com fallback ordenado
├── analysis.py      indicadores e estrutura (funções puras)
├── llm.py           comentários opcionais sobre as leituras calculadas
├── report.py        renderização em Markdown e JSON
├── notify.py        envio opcional para o Telegram
├── config.py        configuração por ambiente / .env
└── pipeline.py      buscar → analisar → interpretar → renderizar → notificar
main.py              CLI
```

`analysis.py` é puro: entra um DataFrame, saem números. Sem rede, sem configuração, sem
LLM. É por isso que os testes de indicadores rodam inteiramente offline contra séries
sintéticas.

**Isolamento de falhas é um objetivo de design.** Um par com problema é registrado na
seção de Falhas do relatório em vez de abortar a execução. Uma chamada ao LLM ou um envio
ao Telegram que falhe nunca descarta um relatório que já foi calculado.

### Adicionando um provedor de dados

Crie uma subclasse de `CandleProvider`, implemente dois métodos e adicione-a a
`build_providers()`. Nada mais na base de código precisa mudar.

```python
from forex.providers import CandleProvider

class MyProvider(CandleProvider):
    name = "myprovider"

    def is_available(self) -> bool:
        return bool(os.getenv("MY_API_KEY"))

    def fetch(self, instrument, timeframe, bars):
        ...  # retorne um DataFrame com open/high/low/close
```

---

## Testes

```bash
python -m pytest          # 178 testes
```

Nenhum teste toca a rede. Os provedores são substituídos por stubs, os candles são
sintéticos e com seed, e os indicadores são verificados contra casos calculáveis à mão —
uma alta monotônica precisa dar RSI 100, o true range de um candle com gap de alta precisa
usar o fechamento anterior, e o mesmo ATR precisa ser lido 100× menor em pips em um par
com JPY.

> [!NOTE]
> O workflow de CI incluído não pode rodar até que o GitHub Actions seja habilitado no
> repositório; em uma conta bloqueada ou sem faturamento, toda execução falha antes de
> começar. Os números acima vêm de execuções locais no Python 3.14 e de uma instalação
> editable limpa em um ambiente virtual separado.

---

## Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Pelo menos um par foi analisado |
| `1` | Todos os pares falharam |
| `2` | Argumento de símbolo inválido |

---

## Contribuindo

Issues e pull requests são bem-vindos. Contribuições úteis incluem novos provedores de
dados, indicadores adicionais, canais de notificação e traduções do README.

Por favor, mantenha `analysis.py` puro e livre de chamadas de rede, e adicione testes que
rodem offline.

---

## Aviso legal

Este projeto produz leituras técnicas a partir de dados públicos de mercado com
**finalidade educacional**. Ele não diz o que você deve comprar ou vender, e não
substitui a sua própria análise nem um consultor financeiro licenciado. Fontes de dados
gratuitas podem estar atrasadas ou erradas — verifique os preços com a sua corretora
antes de agir com base em qualquer coisa daqui. Operar câmbio envolve risco substancial
de perda.

---

## Licença

[MIT](LICENSE)

Inspirado na estrutura de pipeline de
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis).
Esta é uma implementação independente para forex e não compartilha código com ela.
