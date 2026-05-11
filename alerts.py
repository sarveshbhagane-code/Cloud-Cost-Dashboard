"""
alerts.py
Budget alert management system.
Compares current spend against user-defined thresholds and returns alert states.
"""

from mock_data import SERVICE_BASE_COSTS

# Default budget thresholds per service (USD/month)
DEFAULT_BUDGETS = {
    "Amazon EC2": 1500.00,
    "Amazon S3": 500.00,
    "Amazon RDS": 700.00,
    "AWS Lambda": 200.00,
    "Amazon CloudFront": 300.00,
    "Amazon DynamoDB": 150.00,
    "Amazon EKS": 600.00,
    "AWS Glue": 250.00,
    "Amazon SageMaker": 400.00,
    "AWS Data Transfer": 150.00,
    "Total": 5000.00,
}

SEVERITY_THRESHOLDS = {
    "critical": 95,   # >= 95% of budget
    "warning": 80,    # >= 80% of budget
    "moderate": 60,   # >= 60% of budget
    "safe": 0,        # < 60%
}


def _get_severity(pct: float) -> str:
    if pct >= SEVERITY_THRESHOLDS["critical"]:
        return "critical"
    elif pct >= SEVERITY_THRESHOLDS["warning"]:
        return "warning"
    elif pct >= SEVERITY_THRESHOLDS["moderate"]:
        return "moderate"
    return "safe"


def get_budget_alerts(current_costs: dict | None = None, budgets: dict | None = None) -> dict:
    """
    Compare current costs against budget thresholds.

    Args:
        current_costs: dict mapping service name → current monthly cost
        budgets: dict mapping service name → budget threshold (uses defaults if None)

    Returns:
        dict with per-service alert states and summary
    """
    if current_costs is None:
        current_costs = SERVICE_BASE_COSTS
    if budgets is None:
        budgets = DEFAULT_BUDGETS

    # Handle list input (from API responses)
    if isinstance(current_costs, list):
        current_costs = {item["service"]: item["cost"] for item in current_costs}

    alerts = []
    total_spent = sum(current_costs.values())
    total_budget = budgets.get("Total", 5000.0)

    # Per-service alerts
    for service, budget in budgets.items():
        if service == "Total":
            continue
        spent = current_costs.get(service, 0.0)
        pct = round((spent / budget) * 100, 1) if budget > 0 else 0
        severity = _get_severity(pct)
        remaining = round(budget - spent, 2)
        alerts.append(
            {
                "service": service,
                "budget": budget,
                "spent": round(spent, 2),
                "remaining": remaining,
                "utilization_pct": pct,
                "severity": severity,
                "message": _build_message(service, pct, severity, remaining),
            }
        )

    # Total budget alert
    total_pct = round((total_spent / total_budget) * 100, 1)
    total_severity = _get_severity(total_pct)
    alerts.sort(key=lambda x: x["utilization_pct"], reverse=True)

    critical_count = sum(1 for a in alerts if a["severity"] == "critical")
    warning_count = sum(1 for a in alerts if a["severity"] == "warning")

    return {
        "alerts": alerts,
        "summary": {
            "total_budget": total_budget,
            "total_spent": round(total_spent, 2),
            "total_utilization_pct": total_pct,
            "total_severity": total_severity,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "total_remaining": round(total_budget - total_spent, 2),
        },
        "default_budgets": DEFAULT_BUDGETS,
    }


def _build_message(service: str, pct: float, severity: str, remaining: float) -> str:
    if severity == "critical":
        return f"🚨 CRITICAL: {service} has consumed {pct}% of its budget! Only ${remaining:.2f} remaining."
    elif severity == "warning":
        return f"⚠️ WARNING: {service} is at {pct}% of budget. ${remaining:.2f} remaining this month."
    elif severity == "moderate":
        return f"📊 MODERATE: {service} is at {pct}% of budget. Monitor closely."
    return f"✅ {service} is within budget at {pct}% utilization."


def update_budget(service: str, new_budget: float, budgets: dict) -> dict:
    """Update a service budget threshold (in-memory for demo)."""
    if service not in budgets and service != "Total":
        return {"success": False, "error": f"Unknown service: {service}"}
    budgets[service] = new_budget
    return {"success": True, "service": service, "new_budget": new_budget}
