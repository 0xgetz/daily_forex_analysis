<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**Analyse technique assistée par LLM pour le Forex spot et les métaux.**

Indicateurs multi-unités de temps mesurés en pips · prise en compte des sessions 24/5 · fournisseurs de données interchangeables · vos propres clés d'API

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-214%20passing-brightgreen.svg)](#tests)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#tests)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#contribuer)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) ·
[한국어](README.ko.md) ·
[Bahasa Indonesia](README.id.md) ·
[Español](README.es.md) ·
[Português](README.pt-BR.md) ·
**Français** ·
[Deutsch](README.de.md) ·
[Русский](README.ru.md)

</div>

---

## Vue d'ensemble

`daily_forex_analysis` récupère les chandeliers auprès du fournisseur de données de
marché auquel vous avez accès, calcule un tableau technique multi-unités de temps,
demande éventuellement à un modèle de langage de l'interpréter, puis produit un rapport
que vous pouvez lire dans votre terminal, enregistrer sur disque ou envoyer sur Telegram.

Il fonctionne **sans aucune configuration ni clé d'API** grâce à Yahoo Finance. Toutes
les autres fonctionnalités — données premium, commentaire du LLM, notifications — ne
s'activent que si vous fournissez vos propres identifiants.

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

## Pourquoi ce n'est pas un analyseur d'actions dont on a changé les étiquettes

Le Forex obéit à des conventions qui n'ont aucun équivalent sur les actions. Les
comprendre de travers rend chaque chiffre de la page dénué de sens.

| | Actions | Forex spot | Comment ce projet le traite |
| --- | --- | --- | --- |
| **Unité de mouvement** | 1 centime vaut 1 centime | un pip vaut 0,0001 sur EUR/USD mais 0,01 sur USD/JPY | `instruments.py` détient la taille de pip de chaque paire ; rien ne code en dur `0.0001` |
| **Heures de cotation** | ouverture et clôture de la place | continu, du dimanche 21:00 au vendredi 21:00 UTC | `sessions.py` indique la session en cours et signale le chevauchement Londres–New York |
| **Valorisation** | PER, bénéfices, valeur comptable | une devise n'a pas de bénéfices | aucune donnée fondamentale n'est inventée |
| **Identité de l'instrument** | code opaque (`AAPL`) | une *paire* de devises | les symboles se décomposent en devise de base et devise de cotation, avec leurs conventions propres |

Un mouvement de 0,0010 vaut **10 pips** sur EUR/USD et **0,1 pip** sur USD/JPY. Chaque
distance de ce code est dérivée de la convention propre à l'instrument.

---

## Installation

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Nécessite Python 3.9 ou une version plus récente.

---

## Démarrage rapide

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

### Référence de la ligne de commande

| Option | Description |
| --- | --- |
| `--symbols` | Paires séparées par des virgules, par ex. `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | Sous-ensemble de `H1,H4,D1` |
| `--bars` | Nombre de chandeliers demandés par unité de temps (par défaut `300`) |
| `--provider` | Impose `twelvedata`, `alphavantage` ou `yfinance` |
| `--format` | `markdown` (par défaut) ou `json` |
| `--output-dir` | Répertoire de destination des rapports |
| `--dry-run` | Analyse et affiche seulement : aucun appel au LLM, aucun fichier, aucune notification |
| `--no-push` | Ignore les notifications |
| `--stdout` | Affiche le rapport en plus de l'écrire |
| `--check` | Affiche la configuration et l'état des fournisseurs, puis quitte |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Configuration

Copiez `.env.example` vers `.env` et ne renseignez que ce dont vous avez besoin. Chaque
valeur peut également être fournie sous forme de variable d'environnement.

### Fournisseurs de données

Les fournisseurs sont essayés dans l'ordre jusqu'à ce que l'un d'eux couvre **toutes**
les unités de temps demandées : ainsi un même rapport ne mélange jamais des sources aux
conventions différentes. Un fournisseur sans identifiants est ignoré silencieusement.

| Fournisseur | Identifiant | Remarques |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Chandeliers 4 heures natifs ; offre gratuite disponible |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | Forex uniquement, pas de métaux ; offre gratuite à débit limité |
| Yahoo Finance | *aucun* | Solution de repli par défaut, aucune clé requise |

Imposez-en un avec `--provider twelvedata` ou `FOREX_PROVIDER`.

> [!NOTE]
> Deux réserves concernant Yahoo Finance qu'il vaut mieux connaître d'emblée :
> - Yahoo ne propose pas de chandelier 4 heures, donc `H4` est **rééchantillonné** à partir des données horaires.
> - Yahoo ne propose pas de cotation spot des métaux, donc `XAUUSD` est servi depuis les
>   **contrats à terme COMEX** (`GC=F`). Les contrats à terme comportent des effets de base
>   et de roulement, si bien que le niveau diffère légèrement du prix spot de votre courtier.
>   Suffisant pour lire la structure, pas pour exécuter.

### Commentaire du LLM (optionnel)

Tout point d'accès `/chat/completions` compatible OpenAI fonctionne.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

Pointez `LLM_BASE_URL` vers OpenRouter, DeepSeek, Groq, Together ou un serveur
llama.cpp / vLLM local et rien d'autre ne change. `OPENAI_API_KEY`,
`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` et `GROQ_API_KEY` sont tous acceptés, vous
n'avez donc pas besoin de renommer une clé que vous possédez déjà.

> [!IMPORTANT]
> Le modèle ne voit jamais les chandeliers bruts et ne produit jamais de chiffres. Il
> reçoit les mesures déjà calculées et il lui est demandé de les interpréter, ce qui rend
> chaque prix et chaque niveau déterministe et vérifiable. Sans clé, le rapport est tout
> de même produit à partir de la seule analyse calculée.

### Envoi sur Telegram (optionnel)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Créez un bot avec [@BotFather](https://t.me/BotFather) et récupérez votre identifiant de
conversation auprès de [@userinfobot](https://t.me/userinfobot). Désactivez l'envoi avec
`--no-push`. Un envoi qui échoue ne fait jamais perdre un rapport déjà écrit.

### Tous les réglages

| Variable | Valeur par défaut | Signification |
| --- | --- | --- |
| `FOREX_SYMBOLS` | paires majeures + `XAUUSD` | Paires séparées par des virgules |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Sous-ensemble de H1, H4, D1 |
| `FOREX_BARS` | `300` | Nombre de chandeliers demandés par unité de temps |
| `FOREX_PROVIDER` | *auto* | Nom du fournisseur préféré |
| `FOREX_OUTPUT_DIR` | `reports` | Emplacement d'écriture des rapports |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` ou `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Symboles

Toutes ces écritures désignent le même instrument :

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

Pris en charge : les croisements de devises majeurs et mineurs, ainsi que `XAUUSD` (or),
`XAGUSD` (argent), `XPTUSD` (platine) et `XPDUSD` (palladium).

---

## Ce qui est calculé

**Par unité de temps**

- Tendance EMA(20/50), avec un seuil de bruit proportionnel à l'ATR afin que des moyennes
  comprimées soient signalées comme *sans direction* plutôt que comme une fausse tendance
- RSI(14) de Wilder
- MACD(12/26/9)
- ATR(14) plus un percentile de régime de volatilité (contraction / normal / expansion)
- Canaux de Bollinger et de Donchian
- Position dans le range récent, et largeur du range en pips

**Toutes unités de temps confondues**

Un verdict de confluence explicite — `up`, `down`, `sideways` ou `conflicted` — assorti
d'un niveau de confiance. La concordance entre unités de temps est le signal structurel
le plus utile en analyse Forex discrétionnaire : elle est donc calculée et énoncée
clairement, au lieu d'être laissée à la déduction du modèle.

Chaque distance est exprimée en pips selon la convention propre à l'instrument.

---

## Planification

**Cron** — chaque jour ouvré à 07:00 UTC, après l'ouverture de Londres :

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — un workflow est fourni dans `.github/workflows/daily.yml`
(`workflow_dispatch` plus une planification quotidienne). Ajoutez vos clés comme secrets
du dépôt pour activer les étapes LLM et Telegram ; l'absence de secrets désactive
simplement ces fonctionnalités.

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

`analysis.py` est pur : un DataFrame entre, des chiffres sortent. Pas de réseau, pas de
configuration, pas de LLM. C'est pourquoi les tests d'indicateurs s'exécutent
entièrement hors ligne sur des séries synthétiques.

**L'isolation des défaillances est un objectif de conception.** Une paire en échec est
consignée dans la section Failures du rapport au lieu d'interrompre l'exécution. Un appel
au LLM ou un envoi Telegram qui échoue ne fait jamais perdre un rapport déjà calculé.

### Ajouter un fournisseur de données

Dérivez `CandleProvider`, implémentez deux méthodes et ajoutez-le à `build_providers()`.
Rien d'autre dans le code n'a besoin de changer.

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

Aucun test ne touche au réseau. Les fournisseurs sont simulés, les chandeliers sont
synthétiques et générés à partir d'une graine fixe, et les indicateurs sont vérifiés
face à des cas calculables à la main : une hausse monotone doit donner un RSI de 100, le
true range d'un chandelier en gap haussier doit utiliser la clôture précédente, un même
ATR doit se lire 100× plus petit en pips sur un croisement en JPY.

> [!NOTE]
> Le workflow CI fourni ne peut pas s'exécuter tant que GitHub Actions n'est pas activé
> sur le dépôt ; sur un compte bloqué ou sans facturation, chaque exécution échoue avant
> même de démarrer. Les chiffres ci-dessus proviennent d'exécutions locales sur Python
> 3.14 et d'une installation éditable propre dans un environnement virtuel distinct.

---

## Codes de sortie

| Code | Signification |
| --- | --- |
| `0` | Au moins une paire a été analysée |
| `1` | Toutes les paires ont échoué |
| `2` | Argument de symbole invalide |

---

## Contribuer

Les issues et les pull requests sont bienvenues. Parmi les contributions utiles :
nouveaux fournisseurs de données, indicateurs supplémentaires, canaux de notification et
traductions du README.

Merci de garder `analysis.py` pur et exempt d'appels réseau, et d'ajouter des tests qui
s'exécutent hors ligne.

---

## Avertissement

Ce projet produit des mesures techniques à partir de données de marché publiques, à des
**fins éducatives**. Il ne vous dit pas quoi acheter ou vendre, et ne remplace ni votre
propre analyse ni un conseiller financier agréé. Les sources de données gratuites peuvent
être retardées ou erronées — vérifiez les prix auprès de votre courtier avant d'agir sur
quoi que ce soit ici. Le trading sur devises comporte un risque de perte substantiel.

---

## Licence

[MIT](LICENSE)

Inspiré de la structure de pipeline de
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis).
Il s'agit d'une implémentation indépendante pour le Forex, qui ne partage aucun code avec ce projet.
