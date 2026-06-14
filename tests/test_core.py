"""
tests/test_core.py
------------------
Unit tests for the core modules.

Run with:  pytest tests/ -v
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database
from src.api_client import RateAPIClient, APIError
from src.alerts import AlertChecker, AlertFired


# ─── Database tests ──────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Create a fresh in-memory-equivalent DB in a temp directory."""
    return Database(db_path=tmp_path / "test.db")


def test_save_and_retrieve_rates(tmp_db):
    rates = {"EUR": 0.92, "GBP": 0.79, "JPY": 149.5}
    tmp_db.save_rates("USD", rates, "2024-06-01")

    history = tmp_db.get_rate_history("USD", "EUR", days=30)
    assert len(history) == 1
    assert abs(history[0]["rate"] - 0.92) < 0.0001
    assert history[0]["rate_date"] == "2024-06-01"


def test_duplicate_rates_are_ignored(tmp_db):
    """The UNIQUE constraint on (rate_date, base, target) should prevent duplicates."""
    tmp_db.save_rates("USD", {"EUR": 0.92}, "2024-06-01")
    tmp_db.save_rates("USD", {"EUR": 0.93}, "2024-06-01")  # Same date — should be ignored
    history = tmp_db.get_rate_history("USD", "EUR", days=30)
    assert len(history) == 1
    assert abs(history[0]["rate"] - 0.92) < 0.0001  # First write wins


def test_add_and_retrieve_alerts(tmp_db):
    alert_id = tmp_db.add_alert("USD", "EUR", 0.95, "above")
    assert isinstance(alert_id, int)

    pending = tmp_db.get_pending_alerts()
    assert len(pending) == 1
    assert pending[0]["base"] == "USD"
    assert pending[0]["target"] == "EUR"
    assert pending[0]["direction"] == "above"


def test_alert_direction_validation(tmp_db):
    with pytest.raises(ValueError, match="direction must be"):
        tmp_db.add_alert("USD", "EUR", 0.95, "sideways")


def test_mark_alert_triggered(tmp_db):
    aid = tmp_db.add_alert("USD", "GBP", 0.80, "above")
    tmp_db.mark_alert_triggered(aid, 0.81)

    pending = tmp_db.get_pending_alerts()
    assert len(pending) == 0

    all_alerts = tmp_db.get_all_alerts()
    assert all_alerts[0]["triggered"] == 1
    assert abs(all_alerts[0]["triggered_rate"] - 0.81) < 0.0001


def test_delete_alert(tmp_db):
    aid = tmp_db.add_alert("USD", "EUR", 0.95, "below")
    deleted = tmp_db.delete_alert(aid)
    assert deleted is True
    assert len(tmp_db.get_all_alerts()) == 0


def test_delete_nonexistent_alert(tmp_db):
    assert tmp_db.delete_alert(999) is False


def test_clear_triggered_alerts(tmp_db):
    aid1 = tmp_db.add_alert("USD", "EUR", 0.95, "above")
    aid2 = tmp_db.add_alert("USD", "GBP", 0.80, "below")
    tmp_db.mark_alert_triggered(aid1, 0.96)

    count = tmp_db.delete_all_triggered_alerts()
    assert count == 1
    assert len(tmp_db.get_all_alerts()) == 1  # aid2 still pending


def test_get_latest_stored_rate(tmp_db):
    tmp_db.save_rates("USD", {"EUR": 0.91}, "2024-05-01")
    tmp_db.save_rates("USD", {"EUR": 0.92}, "2024-06-01")
    latest = tmp_db.get_latest_stored_rate("USD", "EUR")
    assert abs(latest["rate"] - 0.92) < 0.0001


# ─── Alert checker tests ─────────────────────────────────────────────────────

def make_mock_client(rates: dict):
    """Helper: create a mock API client returning the given rates."""
    client = MagicMock(spec=RateAPIClient)
    client.get_latest_rates.return_value = {"rates": rates, "date": "2024-06-01"}
    return client


def test_alert_fires_above(tmp_db):
    tmp_db.add_alert("USD", "EUR", 0.90, "above")
    client = make_mock_client({"EUR": 0.92})  # 0.92 > 0.90 → should fire
    checker = AlertChecker(tmp_db, client)

    fired = checker.check_all()
    assert len(fired) == 1
    assert fired[0].target == "EUR"
    assert abs(fired[0].current_rate - 0.92) < 0.0001


def test_alert_fires_below(tmp_db):
    tmp_db.add_alert("USD", "GBP", 0.80, "below")
    client = make_mock_client({"GBP": 0.78})  # 0.78 < 0.80 → should fire
    checker = AlertChecker(tmp_db, client)

    fired = checker.check_all()
    assert len(fired) == 1
    assert fired[0].target == "GBP"


def test_alert_does_not_fire_when_not_met(tmp_db):
    tmp_db.add_alert("USD", "EUR", 0.95, "above")
    client = make_mock_client({"EUR": 0.92})  # 0.92 < 0.95 → should NOT fire
    checker = AlertChecker(tmp_db, client)

    fired = checker.check_all()
    assert len(fired) == 0


def test_alert_fires_exactly_at_threshold(tmp_db):
    """Boundary condition: rate == threshold should trigger."""
    tmp_db.add_alert("USD", "EUR", 0.92, "above")
    client = make_mock_client({"EUR": 0.92})
    checker = AlertChecker(tmp_db, client)

    fired = checker.check_all()
    assert len(fired) == 1


def test_no_double_trigger(tmp_db):
    """Once triggered, the same alert should not fire again."""
    tmp_db.add_alert("USD", "EUR", 0.90, "above")
    client = make_mock_client({"EUR": 0.95})
    checker = AlertChecker(tmp_db, client)

    fired_1 = checker.check_all()
    fired_2 = checker.check_all()  # Alert is now marked triggered
    assert len(fired_1) == 1
    assert len(fired_2) == 0


def test_api_error_handled_gracefully(tmp_db):
    """If the API fails, check_all should return [] not crash."""
    tmp_db.add_alert("USD", "EUR", 0.90, "above")
    client = MagicMock(spec=RateAPIClient)
    client.get_latest_rates.side_effect = APIError("Network failure")
    checker = AlertChecker(tmp_db, client)

    fired = checker.check_all()
    assert fired == []  # Graceful degradation


def test_alert_fired_summary():
    f = AlertFired(
        alert_id=1, base="USD", target="EUR",
        direction="above", target_rate=0.90, current_rate=0.92
    )
    summary = f.summary()
    assert "risen above" in summary
    assert "0.9000" in summary
    assert "0.9200" in summary
