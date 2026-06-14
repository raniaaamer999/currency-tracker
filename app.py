"""
app.py
------
Flask web interface for the Currency Exchange Rate Tracker.

Run with:  python app.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
from src.api_client import RateAPIClient, APIError, SUPPORTED_CURRENCIES
from src.database import Database
from src.alerts import AlertChecker

app = Flask(__name__)
db = Database()
client = RateAPIClient()
checker = AlertChecker(db, client)

DEFAULT_TARGETS = ["EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "INR", "SGD", "HKD"]

@app.route("/")
def index():
    return render_template("index.html", currencies=SUPPORTED_CURRENCIES)


@app.route("/api/rates")
def get_rates():
    base = request.args.get("base", "USD").upper()
    try:
        data = client.get_latest_rates(base, targets=DEFAULT_TARGETS)
        db.save_rates(base, data["rates"], data["date"])
        return jsonify({"success": True, "base": base, "date": data["date"], "rates": data["rates"]})
    except APIError as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history")
def get_history():
    base = request.args.get("base", "USD").upper()
    target = request.args.get("target", "EUR").upper()
    history = db.get_rate_history(base, target, days=30)

    if len(history) < 5:
        try:
            from datetime import date, timedelta
            start = date.today() - timedelta(days=30)
            data = client.get_historical_rates(base, start_date=start)
            for date_str, day_rates in data.get("rates", {}).items():
                if target in day_rates:
                    db.save_rates(base, day_rates, date_str)
            history = db.get_rate_history(base, target, days=30)
        except APIError as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # Reverse to chronological order for the chart
    history = list(reversed(history))
    return jsonify({"success": True, "history": history})


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    alerts = db.get_all_alerts()
    return jsonify({"success": True, "alerts": alerts})


@app.route("/api/alerts", methods=["POST"])
def add_alert():
    data = request.json
    base = data.get("base", "").upper()
    target = data.get("target", "").upper()
    direction = data.get("direction", "")
    try:
        target_rate = float(data.get("target_rate", 0))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid rate"}), 400

    if not base or not target or not direction:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    alert_id = db.add_alert(base, target, target_rate, direction)
    return jsonify({"success": True, "id": alert_id})


@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    deleted = db.delete_alert(alert_id)
    return jsonify({"success": deleted})


@app.route("/api/alerts/check", methods=["POST"])
def check_alerts():
    fired = checker.check_all()
    return jsonify({
        "success": True,
        "fired": [{"id": f.alert_id, "summary": f.summary()} for f in fired]
    })


if __name__ == "__main__":
    print("\n  💱 Currency Tracker is running!")
    print("  Open this in your browser: http://localhost:5000\n")
    app.run(debug=True)
