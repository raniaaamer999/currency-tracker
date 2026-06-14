# Currency Exchange Rate Tracker

Since currency exchange is one of the core functions of fintech applications, I built this project to better understand how applications handle real time exchange rate data, historical trends, and alerting systems. It started as a simple script but gradually evolved into a full web application with a database, live API integration, and alert functionality.

## Why I Built This

I am a CS student at NYU Abu Dhabi and I wanted my portfolio to show more than just coursework. I picked this idea because it sits at the intersection of things I wanted to get better at: working with external APIs, designing a backend that persists data properly, and thinking through edge cases like what happens when an API fails or when an alert should only fire once.

This project taught me how to structure a maintainable Python application, with clear separation of concerns, testing, and error handling.

## What It Does

The application includes a browser based dashboard for interacting with exchange rates and alerts.

Live Exchange Rates: pick any base currency and view exchange rates against supported currencies. Data comes from the European Central Bank via the Frankfurter API, updated daily.

Rate History Chart: select any currency pair and load a 30 day line chart showing how the rate has moved over time. Historical data is stored locally so repeat queries do not keep hitting the API.

Rate Alerts: set a target rate and a direction (above or below). The app fetches the live rate and evaluates whether your condition is met. Once an alert fires it is marked as triggered so it never fires twice.

By the numbers: supports 19 currencies, 16 unit tests with 100% pass rate, and historical rates are cached locally so repeated chart queries load instantly without hitting the API again.

## Engineering Decisions

I used SQLite because it is lightweight and sufficient for a single user application with no need for a separate database server.

I cached historical rates locally to reduce repeated API calls since the Frankfurter API only updates once per day anyway.

I marked alerts as triggered after they fire to prevent duplicate notifications, which is a real problem in production alerting systems.

I mocked all API requests in the test suite to ensure tests run deterministically and work offline without any network dependency.

I separated the API client, database layer, and alert engine into distinct modules so each can be tested and changed independently.

## Tech Stack

Python 3.12 is the core language. Flask powers the web server and REST API. The frontend is plain HTML, CSS and JavaScript with Chart.js for the history graph. Exchange rate data comes from the Frankfurter API which is free, open source and requires no API key. All rate history and alerts are stored locally in SQLite using Python's built in sqlite3 module. Tests are written with pytest and all API calls are mocked so the test suite runs offline in under a second.

## Project Structure

```
currency-tracker/
├── app.py               # Flask web server and API routes
├── main.py              # CLI entry point (also works without the browser)
├── src/
│   ├── api_client.py    # Frankfurter API client with error handling
│   ├── database.py      # SQLite layer for rate history and alerts
│   ├── alerts.py        # Alert evaluation engine
│   └── display.py       # Terminal output helpers for the CLI
├── templates/
│   └── index.html       # Web dashboard
├── tests/
│   └── test_core.py     # 16 unit tests covering DB, alerts, and edge cases
├── data/                # SQLite database lives here (auto created on first run)
└── requirements.txt
```

## How to Run It

You need Python 3.10 or higher and pip.

```bash
git clone https://github.com/raniaaamer999/currency-tracker.git
cd currency-tracker
pip install -r requirements.txt
python app.py
```

Then open your browser and go to http://127.0.0.1:5000.

If you prefer the terminal version just run python main.py instead and you will get an interactive menu.

## Running the Tests

```bash
pytest tests/ -v
```

All 16 tests pass with no network connection needed since every API call is mocked.

## What I Would Add Next

WebSocket streaming so rates update in real time without refreshing the page. A Redis cache layer so the app is not making an API call on every single request. Email or Telegram notifications so alerts actually reach you instead of requiring a manual check. And user accounts so multiple people could each track their own currency pairs and alerts independently.

## Author

Rania, CS and Finance student at NYU Abu Dhabi.
