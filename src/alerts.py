"""
alerts.py
---------
Alert evaluation engine.

Compares live exchange rates against user-defined thresholds and
returns triggered alerts — keeping this logic separate from the UI
so it can be run headlessly (e.g. via cron) or from a web interface.
"""

from dataclasses import dataclass
from typing import Optional
from .database import Database
from .api_client import RateAPIClient, APIError


@dataclass
class AlertFired:
    """Represents an alert that just triggered."""
    alert_id: int
    base: str
    target: str
    direction: str
    target_rate: float
    current_rate: float

    def summary(self) -> str:
        direction_word = "risen above" if self.direction == "above" else "fallen below"
        return (
            f"🔔 Alert #{self.alert_id}: {self.base}/{self.target} has {direction_word} "
            f"your target of {self.target_rate:.4f} — current rate: {self.current_rate:.4f}"
        )


class AlertChecker:
    """
    Evaluates pending alerts against live rates.

    Design choice: we batch-fetch rates per unique base currency to minimise
    API calls — important for staying within free-tier rate limits.
    """

    def __init__(self, db: Database, client: RateAPIClient):
        self.db = db
        self.client = client

    def check_all(self) -> list[AlertFired]:
        """
        Check all pending alerts against current rates.

        Returns:
            List of AlertFired objects for every alert that triggered.
        """
        pending = self.db.get_pending_alerts()
        if not pending:
            return []

        # Group alerts by base currency to minimise API calls
        by_base: dict[str, list[dict]] = {}
        for alert in pending:
            by_base.setdefault(alert["base"], []).append(alert)

        fired: list[AlertFired] = []

        for base, alerts in by_base.items():
            targets = list({a["target"] for a in alerts})
            try:
                data = self.client.get_latest_rates(base, targets=targets)
                rates = data["rates"]
            except APIError:
                # Skip this batch if API is unreachable — don't crash everything
                continue

            for alert in alerts:
                current = rates.get(alert["target"])
                if current is None:
                    continue

                triggered = (
                    (alert["direction"] == "above" and current >= alert["target_rate"])
                    or
                    (alert["direction"] == "below" and current <= alert["target_rate"])
                )

                if triggered:
                    self.db.mark_alert_triggered(alert["id"], current)
                    fired.append(AlertFired(
                        alert_id=alert["id"],
                        base=base,
                        target=alert["target"],
                        direction=alert["direction"],
                        target_rate=alert["target_rate"],
                        current_rate=current,
                    ))

        return fired
