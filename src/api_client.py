"""
api_client.py
-------------
Handles all communication with the Frankfurter API (https://www.frankfurter.app).
Frankfurter is a free, open-source currency exchange rate API backed by the
European Central Bank — no API key required, making it ideal for portfolio projects.
"""

import requests
from datetime import date, timedelta
from typing import Optional

BASE_URL = "https://api.frankfurter.app"

# Supported currencies with friendly names for display
SUPPORTED_CURRENCIES = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "JPY": "Japanese Yen",
    "CHF": "Swiss Franc",
    "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar",
    "INR": "Indian Rupee",
    "SGD": "Singapore Dollar",
    "HKD": "Hong Kong Dollar",
    "NOK": "Norwegian Krone",
    "SEK": "Swedish Krona",
    "DKK": "Danish Krone",
    "NZD": "New Zealand Dollar",
    "MXN": "Mexican Peso",
    "BRL": "Brazilian Real",
    "ZAR": "South African Rand",
    "TRY": "Turkish Lira",
    "PLN": "Polish Zloty",
}


class APIError(Exception):
    """Raised when the exchange rate API returns an unexpected response."""
    pass


class RateAPIClient:
    """
    Client for the Frankfurter exchange rate API.

    All methods raise APIError on network failure or unexpected responses,
    so callers can handle errors gracefully without crashing.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        # Identify our client in request headers — good API citizenship
        self.session.headers.update({"User-Agent": "CurrencyTracker/1.0 (portfolio project)"})

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Internal GET helper with error handling."""
        url = f"{BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise APIError("Could not connect to the exchange rate API. Check your internet connection.")
        except requests.exceptions.Timeout:
            raise APIError(f"API request timed out after {self.timeout}s.")
        except requests.exceptions.HTTPError as e:
            raise APIError(f"API returned an error: {e.response.status_code} {e.response.reason}")
        except ValueError:
            raise APIError("API returned invalid JSON — this is likely a temporary outage.")

    def get_latest_rates(self, base: str, targets: Optional[list[str]] = None) -> dict:
        """
        Fetch the latest exchange rates for a base currency.

        Args:
            base: ISO 4217 currency code (e.g. "USD")
            targets: Optional list of target currency codes. If None, returns all available.

        Returns:
            Dict with keys: 'base', 'date', 'rates' (dict of currency → rate)
        """
        params = {"from": base.upper()}
        if targets:
            params["to"] = ",".join(t.upper() for t in targets)

        data = self._get("/latest", params=params)

        # Validate the response shape we depend on
        if "rates" not in data:
            raise APIError("Unexpected API response: missing 'rates' field.")

        return data

    def get_historical_rates(self, base: str, start_date: date, end_date: Optional[date] = None) -> dict:
        """
        Fetch historical rates between two dates (or from start_date to today).

        Args:
            base: Base currency code
            start_date: Start of the date range
            end_date: End of the date range (defaults to today)

        Returns:
            Dict with 'rates' keyed by date string → {currency: rate}
        """
        end = end_date or date.today()
        endpoint = f"/{start_date.isoformat()}..{end.isoformat()}"
        params = {"from": base.upper()}
        return self._get(endpoint, params=params)

    def get_single_rate(self, base: str, target: str) -> float:
        """
        Convenience method: get a single exchange rate between two currencies.

        Returns:
            The exchange rate as a float.
        """
        data = self.get_latest_rates(base, targets=[target])
        target_upper = target.upper()
        if target_upper not in data["rates"]:
            raise APIError(f"Currency '{target}' not found in API response.")
        return data["rates"][target_upper]

    def get_available_currencies(self) -> dict:
        """
        Fetch the full list of currencies supported by the API.

        Returns:
            Dict of {code: name}
        """
        return self._get("/currencies")
