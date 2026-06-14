# 💱 Currency Exchange Rate Tracker

A production-quality Python CLI tool for tracking live foreign exchange rates, viewing historical trends, and setting automated rate alerts — built to demonstrate real-world fintech skills for a software engineering portfolio.

---

## Why I Built This

[Revolut](https://www.revolut.com) is one of the world's leading fintech platforms, processing currency exchanges for over 40 million users daily. As a CS student applying for Revolut's Software Engineer (Python) internship, I wanted to build something that directly mirrors their core product domain: **real-time currency data, historical analysis, and threshold-based alerting**.

This project shows I can:
- Work with financial APIs and handle real-world data reliably
- Design clean, modular Python architecture (not just scripts)
- Persist and query time-series data using SQLite
- Write production-quality code with tests, error handling, and documentation

---

## Features

| Feature | Description |
|---|---|
| 📈 **Live Rates** | Pull real-time exchange rates for any base currency vs. multiple targets |
| 📊 **Rate History** | View an ASCII sparkline chart of rate trends over the past 30 days |
| 🔔 **Rate Alerts** | Set a target rate and get notified when a currency crosses your threshold |
| 💾 **Local Storage** | Rate history and alerts persist in a local SQLite database |
| ⚡ **CLI + Menu** | Interactive menu for exploratory use; subcommands for scripting/automation |

---

## Tech Stack

| Technology | Role |
|---|---|
| **Python 3.12** | Core language |
| **`requests`** | HTTP client for API calls |
| **SQLite (stdlib)** | Persistent storage — no external DB server needed |
| **`pytest`** | Unit testing with mocks |
| **Frankfurter API** | Free, open-source ECB-backed exchange rate data — no API key required |

---

## Project Structure

```
currency-tracker/
├── main.py              # Entry point — CLI menu and subcommands
├── src/
│   ├── api_client.py    # Frankfurter API client with error handling
│   ├── database.py      # SQLite layer: rate history + alerts
│   ├── alerts.py        # Alert evaluation engine
│   └── display.py       # ANSI-coloured terminal output helpers
├── tests/
│   └── test_core.py     # 16 unit tests (DB, alerts, edge cases)
├── data/                # Auto-created: rates.db lives here
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/currency-tracker.git
cd currency-tracker
pip install -r requirements.txt
```

### Run the interactive menu

```bash
python main.py
```

You'll see:

```
  ╔═══════════════════════════════════════════╗
  ║   💱  Currency Exchange Rate Tracker      ║
  ║   Built for fintech portfolio — Revolut   ║
  ╚═══════════════════════════════════════════╝

  Main Menu
  ──────────────────────────────────────────────────
  [1] View live exchange rates
  [2] View rate history (chart)
  [3] Set a rate alert
  [4] Manage alerts
  [5] Check alerts now
  [q] Quit
```

### Quick commands (for scripting / cron jobs)

```bash
# Show live USD rates against 9 major currencies
python main.py rates USD

# Show rates for a custom set of targets
python main.py rates AED USD EUR GBP

# Show 30-day history chart for USD/EUR
python main.py history USD EUR

# Check all pending alerts against live rates
python main.py check-alerts
```

### Run tests

```bash
pytest tests/ -v
```

All 16 tests should pass in under a second — no network required (API calls are mocked).

---

## How Alerts Work

1. You set an alert: e.g. *"notify me when USD/EUR goes above 0.95"*
2. Rate and direction are saved to SQLite
3. Run `python main.py check-alerts` (or schedule it with cron) — the tool fetches live rates and fires any matching alerts
4. Triggered alerts are marked as done so they don't fire twice

**Example cron job** (check every hour):
```cron
0 * * * * cd /path/to/currency-tracker && python main.py check-alerts >> data/alert.log 2>&1
```

---

## API: Frankfurter

This project uses [Frankfurter](https://www.frankfurter.app) — a free, open-source API backed by European Central Bank data. It requires no API key and has generous rate limits, making it ideal for portfolio projects and prototyping.

The `RateAPIClient` class in `src/api_client.py` wraps it with:
- Connection/timeout error handling
- Clean `APIError` exceptions (no raw `requests` exceptions leaking into the UI)
- Session reuse for connection pooling
- Polite `User-Agent` headers

---

## What I'd Add in a Production System

- **WebSocket streaming** for real-time tick-by-tick rates (Revolut-style)
- **Redis cache** to avoid hitting the rate API on every request
- **REST API layer** (FastAPI) so alerts can be managed from a mobile app
- **Push notifications** (email / Telegram bot) when alerts fire
- **Forex spread modelling** to simulate real exchange margins

---

## Author

**Rania** — CS student at NYU Abu Dhabi  
Building for the Revolut Software Engineer (Python) Internship — Summer 2027

---

## License

MIT — free to use, fork, and learn from.
