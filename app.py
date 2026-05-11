"""
app.py
Flask REST API server for the Cloud Cost Optimization Dashboard.

Endpoints:
  GET  /api/overview          - Monthly cost summary (AWS)
  GET  /api/trends/daily      - Daily cost trends (AWS)
  GET  /api/trends/monthly    - Monthly cost trends (AWS)
  GET  /api/regions           - Cost by AWS region
  GET  /api/alerts            - Budget alert status
  GET  /api/optimizations     - Optimization recommendations
  GET  /api/azure/overview    - Azure monthly cost summary
  GET  /api/azure/trends      - Azure monthly trends
  GET  /api/multicloud        - Combined AWS + Azure view
  POST /api/budgets/update    - Update a budget threshold
"""

import os
import sys
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# ── Ensure local modules are importable ──────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import aws_cost
import azure_cost
from alerts import get_budget_alerts, update_budget, DEFAULT_BUDGETS
from optimizer import get_optimizations, get_total_potential_savings

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory budget store (resets on restart; use a DB for production)
_budgets = dict(DEFAULT_BUDGETS)


# ── Helpers ──────────────────────────────────────────────────────────────────
def success(data: dict, status: int = 200):
    return jsonify({"status": "ok", "data": data}), status


def error(message: str, status: int = 400):
    return jsonify({"status": "error", "message": message}), status


# ── Health check ─────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return success({"message": "Cloud Cost Optimization Dashboard API is running ✅"})


# ── AWS Endpoints ─────────────────────────────────────────────────────────────
@app.route("/api/overview", methods=["GET"])
def overview():
    """Monthly AWS cost summary with service breakdown."""
    try:
        data = aws_cost.fetch_overview()
        return success(data)
    except Exception as e:
        logger.exception("Error in /api/overview")
        return error(str(e), 500)


@app.route("/api/trends/daily", methods=["GET"])
def daily_trends():
    """Daily cost trends for the past N days (default 30)."""
    try:
        days = int(request.args.get("days", 30))
        days = max(7, min(days, 90))
        data = aws_cost.fetch_daily_trends(days)
        return success({"days": days, "trends": data})
    except Exception as e:
        logger.exception("Error in /api/trends/daily")
        return error(str(e), 500)


@app.route("/api/trends/monthly", methods=["GET"])
def monthly_trends():
    """Monthly cost trends for the past N months (default 6)."""
    try:
        months = int(request.args.get("months", 6))
        months = max(3, min(months, 12))
        data = aws_cost.fetch_monthly_trends(months)
        return success({"months": months, "trends": data})
    except Exception as e:
        logger.exception("Error in /api/trends/monthly")
        return error(str(e), 500)


@app.route("/api/regions", methods=["GET"])
def regions():
    """Cost breakdown by AWS region."""
    try:
        data = aws_cost.fetch_region_costs()
        return success({"regions": data})
    except Exception as e:
        logger.exception("Error in /api/regions")
        return error(str(e), 500)


# ── Budget Alerts ─────────────────────────────────────────────────────────────
@app.route("/api/alerts", methods=["GET"])
def alerts():
    """Budget alert status for all services."""
    try:
        overview_data = aws_cost.fetch_overview()
        current_costs = overview_data.get("services", [])
        data = get_budget_alerts(current_costs, _budgets)
        return success(data)
    except Exception as e:
        logger.exception("Error in /api/alerts")
        return error(str(e), 500)


@app.route("/api/budgets/update", methods=["POST"])
def update_budget_endpoint():
    """Update a budget threshold for a service."""
    try:
        body = request.get_json(force=True)
        service = body.get("service")
        amount = body.get("budget")
        if not service or amount is None:
            return error("Both 'service' and 'budget' fields are required.")
        result = update_budget(service, float(amount), _budgets)
        if not result["success"]:
            return error(result.get("error", "Unknown error"), 400)
        return success(result)
    except Exception as e:
        logger.exception("Error in /api/budgets/update")
        return error(str(e), 500)


# ── Optimizations ─────────────────────────────────────────────────────────────
@app.route("/api/optimizations", methods=["GET"])
def optimizations():
    """Cost optimization recommendations with estimated savings."""
    try:
        overview_data = aws_cost.fetch_overview()
        current_costs = overview_data.get("services", [])
        recommendations = get_optimizations(current_costs)
        total_savings = get_total_potential_savings(current_costs)
        return success(
            {
                "recommendations": recommendations,
                "total_potential_savings_usd": total_savings,
                "count": len(recommendations),
            }
        )
    except Exception as e:
        logger.exception("Error in /api/optimizations")
        return error(str(e), 500)


# ── Azure Endpoints ───────────────────────────────────────────────────────────
@app.route("/api/azure/overview", methods=["GET"])
def azure_overview():
    """Azure monthly cost summary."""
    try:
        data = azure_cost.fetch_overview()
        return success(data)
    except Exception as e:
        logger.exception("Error in /api/azure/overview")
        return error(str(e), 500)


@app.route("/api/azure/trends", methods=["GET"])
def azure_trends():
    """Azure monthly cost trends."""
    try:
        months = int(request.args.get("months", 6))
        data = azure_cost.fetch_monthly_trends(months)
        return success({"trends": data})
    except Exception as e:
        logger.exception("Error in /api/azure/trends")
        return error(str(e), 500)


# ── Multi-Cloud ───────────────────────────────────────────────────────────────
@app.route("/api/multicloud", methods=["GET"])
def multicloud():
    """Combined AWS + Azure cost comparison."""
    try:
        aws_data = aws_cost.fetch_overview()
        az_data = azure_cost.fetch_overview()
        aws_trends = aws_cost.fetch_monthly_trends(6)
        az_trends = azure_cost.fetch_monthly_trends(6)

        return success(
            {
                "aws": {
                    "total": aws_data.get("total_monthly_cost", 0),
                    "services": aws_data.get("services", [])[:5],
                    "trends": aws_trends,
                },
                "azure": {
                    "total": az_data.get("total_monthly_cost", 0),
                    "services": az_data.get("services", [])[:5],
                    "trends": az_trends,
                },
                "combined_total": round(
                    aws_data.get("total_monthly_cost", 0)
                    + az_data.get("total_monthly_cost", 0),
                    2,
                ),
            }
        )
    except Exception as e:
        logger.exception("Error in /api/multicloud")
        return error(str(e), 500)


# ── Serve Frontend ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    from flask import send_from_directory
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    return send_from_directory(frontend_dir, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    from flask import send_from_directory
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    return send_from_directory(frontend_dir, filename)


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    logger.info("🚀 Starting Cloud Cost Dashboard API on http://localhost:%d", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
