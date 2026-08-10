<div align="center">

<img src="assets/logo.svg" alt="daily_forex_analysis" width="128" height="128">

# daily_forex_analysis

**Analisis teknikal untuk spot forex dan logam, dibantu LLM.**

Indikator multi-timeframe dalam satuan pip · sadar sesi pasar 24/5 · penyedia data yang bisa ditukar · pakai API key milikmu sendiri

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-214%20passing-brightgreen.svg)](#pengujian)
[![Offline tests](https://img.shields.io/badge/network%20calls%20in%20tests-0-blue.svg)](#pengujian)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#kontribusi)

[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) ·
[한국어](README.ko.md) ·
**Bahasa Indonesia** ·
[Español](README.es.md) ·
[Português](README.pt-BR.md) ·
[Français](README.fr.md) ·
[Deutsch](README.de.md) ·
[Русский](README.ru.md)

</div>

---

## Ringkasan

`daily_forex_analysis` mengambil data candle dari penyedia data pasar mana pun yang
kamu punya aksesnya, menghitung gambaran teknikal multi-timeframe, secara opsional
meminta model bahasa untuk menafsirkannya, lalu menulis laporan yang bisa kamu baca di
terminal, simpan ke disk, atau kirim ke Telegram.

Program ini jalan **tanpa konfigurasi dan tanpa API key** menggunakan Yahoo Finance.
Setiap kemampuan lain — data premium, komentar LLM, notifikasi — baru aktif kalau kamu
memasukkan kredensialmu sendiri.

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

## Kenapa ini bukan penganalisis saham yang cuma diganti label

Forex punya konvensi yang tidak ada padanannya di saham. Salah menanganinya membuat
setiap angka di halaman jadi tidak bermakna.

| | Saham | Spot Forex | Cara proyek ini menanganinya |
| --- | --- | --- | --- |
| **Satuan pergerakan** | 1 sen tetap 1 sen | satu pip adalah 0,0001 di EUR/USD tapi 0,01 di USD/JPY | `instruments.py` memegang ukuran pip tiap pasangan; tidak ada yang menuliskan `0.0001` secara kaku |
| **Jam perdagangan** | ada pembukaan dan penutupan bursa | berjalan terus, Minggu 21:00 → Jumat 21:00 UTC | `sessions.py` melaporkan sesi yang sedang aktif dan menandai overlap London–New York |
| **Valuasi** | P/E, laba, nilai buku | mata uang tidak punya laba | tidak ada data fundamental yang dikarang |
| **Identitas instrumen** | kode ticker buram (`AAPL`) | sebuah *pasangan* mata uang | simbol diurai menjadi base dan quote dengan konvensinya masing-masing |

Pergerakan 0,0010 sama dengan **10 pip** di EUR/USD dan **0,1 pip** di USD/JPY. Setiap
jarak di basis kode ini diturunkan dari konvensi instrumennya sendiri.

---

## Instalasi

```bash
git clone https://github.com/0xgetz/daily_forex_analysis.git
cd daily_forex_analysis

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Membutuhkan Python 3.9 atau lebih baru.

---

## Mulai cepat

```bash
# Tampilkan konfigurasi dan penyedia mana yang bisa dipakai — tanpa perlu jaringan
python main.py --check

# Analisis watchlist bawaan, cetak ke stdout, tidak menulis apa pun
python main.py --dry-run

# Pasangan pilihanmu, timeframe pilihanmu, ditulis ke reports/
python main.py --symbols EURUSD,GBPUSD,XAUUSD --timeframes H1,H4,D1

# Keluaran yang bisa dibaca mesin
python main.py --symbols EURUSD --format json
```

### Referensi CLI

| Flag | Keterangan |
| --- | --- |
| `--symbols` | Pasangan dipisah koma, misal `EURUSD,GBPUSD,XAUUSD` |
| `--timeframes` | Bagian dari `H1,H4,D1` |
| `--bars` | Jumlah candle per timeframe (bawaan `300`) |
| `--provider` | Paksa `twelvedata`, `alphavantage`, atau `yfinance` |
| `--format` | `markdown` (bawaan) atau `json` |
| `--output-dir` | Direktori tujuan laporan |
| `--dry-run` | Hanya analisis dan cetak: tanpa panggilan LLM, tanpa file, tanpa notifikasi |
| `--no-push` | Lewati notifikasi |
| `--stdout` | Cetak laporan sekaligus menuliskannya |
| `--check` | Cetak konfigurasi dan status penyedia, lalu keluar |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Konfigurasi

Salin `.env.example` menjadi `.env` dan isi hanya yang kamu butuhkan. Setiap nilai juga
bisa diberikan sebagai variabel lingkungan.

### Penyedia data

Penyedia dicoba berurutan sampai ada satu yang memenuhi **semua** timeframe yang
diminta, sehingga satu laporan tidak pernah mencampur sumber dengan konvensi berbeda.
Penyedia tanpa kredensial dilewati tanpa keluhan.

| Penyedia | Kredensial | Catatan |
| --- | --- | --- |
| Twelve Data | `TWELVEDATA_API_KEY` | Candle 4 jam native; tersedia tier gratis |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | Hanya forex, tanpa logam; tier gratis dibatasi rate |
| Yahoo Finance | *tidak ada* | Fallback bawaan, tidak perlu key |

Paksa satu penyedia dengan `--provider twelvedata` atau `FOREX_PROVIDER`.

> [!NOTE]
> Dua catatan penting soal Yahoo Finance yang sebaiknya kamu tahu sejak awal:
> - Yahoo tidak punya candle 4 jam, jadi `H4` **di-resample** dari data per jam.
> - Yahoo tidak punya kuotasi spot untuk logam, jadi `XAUUSD` diambil dari **futures
>   COMEX** (`GC=F`). Futures membawa efek basis dan roll, sehingga levelnya sedikit
>   berbeda dari harga spot brokermu. Cukup untuk membaca struktur, bukan untuk eksekusi.

### Komentar LLM (opsional)

Endpoint `/chat/completions` apa pun yang kompatibel dengan OpenAI bisa dipakai.

```bash
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

Arahkan `LLM_BASE_URL` ke OpenRouter, DeepSeek, Groq, Together, atau server
llama.cpp / vLLM lokal dan tidak ada lagi yang perlu diubah. `OPENAI_API_KEY`,
`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` dan `GROQ_API_KEY` semuanya diterima, jadi kamu
tidak perlu mengganti nama key yang sudah kamu miliki.

> [!IMPORTANT]
> Model tidak pernah melihat candle mentah dan tidak pernah menghasilkan angka. Ia
> menerima hasil perhitungan yang sudah jadi lalu diminta menafsirkannya, sehingga setiap
> harga dan level tetap deterministik dan bisa diaudit. Tanpa API key, laporan tetap
> dihasilkan murni dari analisis terhitung.

### Kirim ke Telegram (opsional)

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
```

Buat bot lewat [@BotFather](https://t.me/BotFather) dan ambil chat id-mu dari
[@userinfobot](https://t.me/userinfobot). Lewati pengiriman dengan `--no-push`.
Pengiriman yang gagal tidak pernah membuang laporan yang sudah ditulis.

### Semua pengaturan

| Variabel | Bawaan | Arti |
| --- | --- | --- |
| `FOREX_SYMBOLS` | major + `XAUUSD` | Pasangan dipisah koma |
| `FOREX_TIMEFRAMES` | `H1,H4,D1` | Bagian dari H1, H4, D1 |
| `FOREX_BARS` | `300` | Jumlah candle per timeframe |
| `FOREX_PROVIDER` | *otomatis* | Nama penyedia yang diutamakan |
| `FOREX_OUTPUT_DIR` | `reports` | Lokasi penulisan laporan |
| `FOREX_REPORT_FORMAT` | `markdown` | `markdown` atau `json` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Simbol

Semua penulisan berikut mengarah ke instrumen yang sama:

```
EURUSD    eur/usd    EUR-USD    EUR_USD    EURUSD=X
```

Didukung: pasangan mata uang major dan minor, ditambah `XAUUSD` (emas), `XAGUSD`
(perak), `XPTUSD` (platinum) dan `XPDUSD` (paladium).

---

## Apa yang dihitung

**Per timeframe**

- Tren EMA(20/50), dengan batas kebisingan berskala ATR sehingga rata-rata yang
  berhimpitan dilaporkan sebagai *sideways*, bukan sebagai tren palsu
- Wilder RSI(14)
- MACD(12/26/9)
- ATR(14) plus persentil rezim volatilitas (menyempit / normal / melebar)
- Kanal Bollinger dan Donchian
- Posisi di dalam rentang terkini, dan lebar rentang dalam pip

**Lintas timeframe**

Kesimpulan konfluensi yang eksplisit — `up`, `down`, `sideways` atau `conflicted` —
beserta tingkat keyakinannya. Kesepakatan antar timeframe adalah sinyal struktural
paling berguna dalam analisis forex diskresioner, jadi ia dihitung dan dinyatakan
terang-terangan alih-alih dibiarkan disimpulkan sendiri oleh model.

Setiap jarak dinyatakan dalam pip memakai konvensi instrumen yang bersangkutan.

---

## Penjadwalan

**Cron** — setiap hari kerja pukul 07:00 UTC, setelah pembukaan London:

```cron
0 7 * * 1-5 cd /path/to/daily_forex_analysis && .venv/bin/python main.py
```

**GitHub Actions** — sebuah workflow disertakan di `.github/workflows/daily.yml`
(`workflow_dispatch` plus jadwal harian). Tambahkan key-mu sebagai repository secret
untuk mengaktifkan langkah LLM dan Telegram; secret yang tidak ada cukup menonaktifkan
fitur tersebut.

---

## Arsitektur

```
forex/
├── instruments.py   parsing simbol, konvensi pip
├── sessions.py      jam pasar 24/5, sesi Tokyo/London/New York
├── providers.py     sumber data dengan fallback berurutan
├── analysis.py      indikator dan struktur (fungsi murni)
├── llm.py           komentar opsional atas hasil perhitungan
├── report.py        rendering Markdown dan JSON
├── notify.py        pengiriman Telegram opsional
├── config.py        konfigurasi environment / .env
└── pipeline.py      ambil → analisis → tafsir → render → kirim
main.py              CLI
```

`analysis.py` bersifat murni: DataFrame masuk, angka keluar. Tanpa jaringan, tanpa
konfigurasi, tanpa LLM. Itulah sebabnya pengujian indikator berjalan sepenuhnya offline
terhadap deret sintetis.

**Isolasi kegagalan adalah tujuan desain.** Satu pasangan yang rusak dicatat di bagian
Kegagalan pada laporan, bukan menggagalkan seluruh proses. Panggilan LLM atau
pengiriman Telegram yang gagal tidak pernah membuang laporan yang sudah dihitung.

### Menambahkan penyedia data

Turunkan `CandleProvider`, implementasikan dua metode, lalu tambahkan ke
`build_providers()`. Tidak ada bagian lain dari basis kode yang perlu diubah.

```python
from forex.providers import CandleProvider

class MyProvider(CandleProvider):
    name = "myprovider"

    def is_available(self) -> bool:
        return bool(os.getenv("MY_API_KEY"))

    def fetch(self, instrument, timeframe, bars):
        ...  # kembalikan DataFrame dengan open/high/low/close
```

---

## Pengujian

```bash
python -m pytest          # 214 pengujian
```

Tidak ada pengujian yang menyentuh jaringan. Penyedia data distub, candle bersifat
sintetis dan ber-seed, dan indikator diverifikasi terhadap kasus yang bisa dihitung
manual — kenaikan monoton harus menghasilkan RSI 100, true range sebuah candle yang
gap-up harus memakai harga penutupan sebelumnya, dan ATR yang sama harus terbaca 100×
lebih kecil dalam pip pada pasangan JPY.

> [!NOTE]
> Workflow CI yang disertakan belum bisa berjalan sampai GitHub Actions diaktifkan di
> repositori ini; pada akun yang terkunci atau belum ditagih, setiap run gagal sebelum
> mulai. Angka di atas berasal dari eksekusi lokal pada Python 3.14 dan dari instalasi
> editable yang bersih di virtual environment terpisah.

---

## Kode keluar

| Kode | Arti |
| --- | --- |
| `0` | Setidaknya satu pasangan berhasil dianalisis |
| `1` | Semua pasangan gagal |
| `2` | Argumen simbol tidak valid |

---

## Kontribusi

Issue dan pull request dipersilakan. Kontribusi yang berguna antara lain penyedia data
baru, indikator tambahan, kanal notifikasi, dan terjemahan README.

Mohon jaga `analysis.py` tetap murni dan bebas dari panggilan jaringan, serta sertakan
pengujian yang berjalan offline.

---

## Penafian

Proyek ini menghasilkan bacaan teknikal dari data pasar publik untuk **tujuan edukasi**.
Ia tidak memberi tahu kamu apa yang harus dibeli atau dijual, dan bukan pengganti
analisismu sendiri maupun penasihat keuangan berlisensi. Sumber data gratis bisa
tertunda atau salah — verifikasi harga dengan brokermu sebelum bertindak atas apa pun di
sini. Perdagangan valuta asing membawa risiko kerugian yang besar.

---

## Lisensi

[MIT](LICENSE)

Terinspirasi struktur pipeline dari
[ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis).
Ini adalah implementasi independen untuk forex dan tidak berbagi kode dengannya.
