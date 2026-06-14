#!/usr/bin/env python3
"""
main.py — Currency Exchange Rate Tracker
-----------------------------------------
Entry point for the command-line interface.

Built for Rania's Revolut internship portfolio.
Revolut processes millions of currency exchanges daily; this project
demonstrates the same core capability at a portfolio scale.

Usage:
    python main.py                  # Interactive menu
    python main.py rates USD        # Quick: show USD rates
    python main.py history USD EUR  # Quick: show USD/EUR history
    python main.py check-alerts     # Quick: check all pending alerts
"""

import sys
import argparse
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent))

from src.api_client import RateAPIClient, APIError, SUPPORTED_CURRENCIES
from src.database import Database
from src.alerts import AlertChecker
from src import display as ui


# Default set of target currencies shown in the rates view
DEFAULT_TARGETS = ["EUR", "GBP", "AED", "JPY", "CHF", "CAD", "AUD", "INR", "SGD"]


def build_dependencies():
    """Construct shared service objects."""
    db = Database()
    client = RateAPIClient()
    checker = AlertChecker(db, client)
    return db, client, checker


# ─── Feature: Show live rates ────────────────────────────────────────────────

def cmd_rates(base: str, targets: list[str], db: Database, client: RateAPIClient):
    """Fetch live rates and persist to history."""
    base = base.upper()
    if base not in SUPPORTED_CURRENCIES:
        ui.error(f"Unsupported base currency: {base}")
        return

    targets = [t.upper() for t in targets if t.upper() != base]

    ui.info(f"Fetching live rates for {base}…")
    try:
        data = client.get_latest_rates(base, targets=targets)
    except APIError as e:
        ui.error(str(e))
        return

    rates = data["rates"]
    rate_date = data.get("date", "unknown")

    # Persist to history so the user can see trends later
    db.save_rates(base, rates, rate_date)

    ui.print_rates_table(base, rates, SUPPORTED_CURRENCIES)
    ui.info(f"Rates from {rate_date}. Saved to local history.")


# ─── Feature: Rate history ───────────────────────────────────────────────────

def cmd_history(base: str, target: str, db: Database, client: RateAPIClient):
    """Show stored rate history for a currency pair, fetching from API if sparse."""
    base, target = base.upper(), target.upper()

    # If we have fewer than 5 data points, proactively fetch 30 days of history
    stored = db.get_rate_history(base, target, days=30)
    if len(stored) < 5:
        ui.info("Sparse local history — fetching 30 days from API…")
        try:
            from datetime import date, timedelta
            start = date.today() - timedelta(days=30)
            data = client.get_historical_rates(base, start_date=start)
            # Historical API returns: {"rates": {"2024-01-01": {"EUR": 0.92, ...}}}
            for date_str, day_rates in data.get("rates", {}).items():
                if target in day_rates:
                    db.save_rates(base, day_rates, date_str)
            stored = db.get_rate_history(base, target, days=30)
        except APIError as e:
            ui.error(f"Could not fetch history: {e}")

    ui.print_history_chart(stored, base, target)


# ─── Feature: Set alert ──────────────────────────────────────────────────────

def cmd_set_alert(db: Database, client: RateAPIClient):
    """Interactive prompt to set a new rate alert."""
    ui.header("Set a Rate Alert")
    print("  You'll be notified when a currency hits your target rate.\n")

    base = input("  Base currency (e.g. USD): ").strip().upper()
    target = input("  Target currency (e.g. EUR): ").strip().upper()

    for code in (base, target):
        if code not in SUPPORTED_CURRENCIES:
            ui.error(f"Unsupported currency: {code}")
            return

    # Show the current rate as a reference
    try:
        current = client.get_single_rate(base, target)
        ui.info(f"Current {base}/{target} rate: {current:.4f}")
    except APIError as e:
        ui.error(f"Could not fetch current rate: {e}. Continuing anyway.")
        current = None

    try:
        target_rate = float(input("  Target rate: ").strip())
    except ValueError:
        ui.error("Invalid rate — please enter a number.")
        return

    direction = input("  Alert when rate goes [above/below] target? ").strip().lower()
    if direction not in ("above", "below"):
        ui.error("Direction must be 'above' or 'below'.")
        return

    alert_id = db.add_alert(base, target, target_rate, direction)
    ui.success(f"Alert #{alert_id} set: notify when {base}/{target} goes {direction} {target_rate:.4f}")

    if current:
        already = (direction == "above" and current >= target_rate) or \
                  (direction == "below" and current <= target_rate)
        if already:
            ui.info(f"FYI: the current rate ({current:.4f}) already satisfies this condition.")


# ─── Feature: Check alerts ───────────────────────────────────────────────────

def cmd_check_alerts(db: Database, checker: AlertChecker):
    """Check all pending alerts against live rates."""
    pending = db.get_pending_alerts()
    if not pending:
        ui.info("No pending alerts to check.")
        return

    ui.info(f"Checking {len(pending)} pending alert(s)…")
    fired = checker.check_all()

    if fired:
        print()
        for f in fired:
            print(f"  {f.summary()}")
        print()
        ui.success(f"{len(fired)} alert(s) triggered.")
    else:
        ui.info("No alerts triggered.")


# ─── Feature: Manage alerts ──────────────────────────────────────────────────

def cmd_manage_alerts(db: Database, checker: AlertChecker):
    """View and manage saved alerts."""
    alerts = db.get_all_alerts()
    ui.print_alerts_table(alerts)

    if not alerts:
        return

    print("\n  Options:")
    print("  [c] Check pending alerts now")
    print("  [d] Delete an alert by ID")
    print("  [x] Clear all triggered alerts")
    print("  [q] Back")
    choice = input("\n  Choice: ").strip().lower()

    if choice == "c":
        cmd_check_alerts(db, checker)
    elif choice == "d":
        try:
            aid = int(input("  Alert ID to delete: "))
            if db.delete_alert(aid):
                ui.success(f"Alert #{aid} deleted.")
            else:
                ui.error(f"No alert with ID {aid}.")
        except ValueError:
            ui.error("Please enter a valid integer ID.")
    elif choice == "x":
        count = db.delete_all_triggered_alerts()
        ui.success(f"Cleared {count} triggered alert(s).")


# ─── Interactive menu ────────────────────────────────────────────────────────

def interactive_menu(db: Database, client: RateAPIClient, checker: AlertChecker):
    BANNER = r"""
  ╔═══════════════════════════════════════════╗
  ║   💱  Currency Exchange Rate Tracker      ║
  ║   Built for fintech portfolio — Revolut   ║
  ╚═══════════════════════════════════════════╝
"""
    print(ui.cyan(BANNER))

    while True:
        print("\n  " + ui.bold("Main Menu"))
        ui.divider(50)
        print("  [1] View live exchange rates")
        print("  [2] View rate history (chart)")
        print("  [3] Set a rate alert")
        print("  [4] Manage alerts")
        print("  [5] Check alerts now")
        print("  [q] Quit")
        ui.divider(50)

        choice = input("\n  Select option: ").strip().lower()

        if choice == "1":
            base = input("  Base currency (default USD): ").strip().upper() or "USD"
            targets_input = input(
                f"  Target currencies, comma-separated (default: {','.join(DEFAULT_TARGETS)}): "
            ).strip()
            targets = [t.strip().upper() for t in targets_input.split(",") if t.strip()] or DEFAULT_TARGETS
            cmd_rates(base, targets, db, client)

        elif choice == "2":
            base   = input("  Base currency (default USD): ").strip().upper() or "USD"
            target = input("  Target currency (default EUR): ").strip().upper() or "EUR"
            cmd_history(base, target, db, client)

        elif choice == "3":
            cmd_set_alert(db, client)

        elif choice == "4":
            cmd_manage_alerts(db, checker)

        elif choice == "5":
            cmd_check_alerts(db, checker)

        elif choice == "q":
            print(ui.dim("\n  Goodbye! 👋\n"))
            break

        else:
            ui.error("Unknown option. Please try again.")


# ─── CLI argument parser ─────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="currency-tracker",
        description="Live currency exchange rate tracker with alerts and history.",
    )
    sub = parser.add_subparsers(dest="command")

    # `rates` subcommand
    p_rates = sub.add_parser("rates", help="Show live rates for a base currency")
    p_rates.add_argument("base", help="Base currency (e.g. USD)")
    p_rates.add_argument(
        "targets", nargs="*", default=DEFAULT_TARGETS,
        help="Target currencies (default: a curated set)",
    )

    # `history` subcommand
    p_hist = sub.add_parser("history", help="Show rate history for a currency pair")
    p_hist.add_argument("base", help="Base currency")
    p_hist.add_argument("target", help="Target currency")

    # `check-alerts` subcommand
    sub.add_parser("check-alerts", help="Check all pending alerts against live rates")

    return parser


def main():
    db, client, checker = build_dependencies()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "rates":
        cmd_rates(args.base, args.targets, db, client)
    elif args.command == "history":
        cmd_history(args.base, args.target, db, client)
    elif args.command == "check-alerts":
        cmd_check_alerts(db, checker)
    else:
        # No subcommand → launch interactive menu
        interactive_menu(db, client, checker)


if __name__ == "__main__":
    main()
