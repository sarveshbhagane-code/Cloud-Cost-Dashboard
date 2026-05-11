"""
azure_cost.py
Azure Cost Management REST API integration.
Falls back to mock data automatically if credentials are not configured.
"""

import os
import logging
import requests
from datetime import datetime, timedelta

from mock_data import get_azure_overview, get_azure_monthly_trends

logger = logging.getLogger(__name__)

AZURE_MGMT_URL = "https://management.azure.com"
AZURE_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/token"


def _is_configured():
    """Check if Azure credentials are configured."""
    tenant = os.getenv("AZURE_TENANT_ID", "")
    client = os.getenv("AZURE_CLIENT_ID", "")
    secret = os.getenv("AZURE_CLIENT_SECRET", "")
    sub = os.getenv("AZURE_SUBSCRIPTION_ID", "")
    return all(
        v and not v.startswith("your_")
        for v in [tenant, client, secret, sub]
    )


def _get_access_token():
    """Obtain an OAuth2 access token for Azure Management API."""
    tenant_id = os.getenv("AZURE_TENANT_ID")
    url = AZURE_TOKEN_URL.format(tenant_id=tenant_id)
    payload = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("AZURE_CLIENT_ID"),
        "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
        "resource": AZURE_MGMT_URL,
    }
    response = requests.post(url, data=payload, timeout=15)
    response.raise_for_status()
    return response.json()["access_token"]


# ─────────────────────────────────────────────
# Public API Functions
# ─────────────────────────────────────────────

def fetch_overview():
    """
    Fetch Azure monthly cost overview from Cost Management API.
    Falls back to mock data if credentials are not configured.
    """
    if not _is_configured():
        logger.info("Azure not configured — using mock data.")
        return get_azure_overview()

    try:
        token = _get_access_token()
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        today = datetime.utcnow()
        start = today.replace(day=1).strftime("%Y-%m-%dT00:00:00Z")
        end = today.strftime("%Y-%m-%dT23:59:59Z")

        url = (
            f"{AZURE_MGMT_URL}/subscriptions/{subscription_id}"
            f"/providers/Microsoft.CostManagement/query"
            f"?api-version=2023-03-01"
        )
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "timePeriod": {"from": start, "to": end},
            "dataset": {
                "granularity": "Monthly",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [{"type": "Dimension", "name": "ServiceName"}],
            },
        }

        resp = requests.post(url, json=body, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        services = []
        total = 0.0
        columns = [col["name"] for col in data["properties"]["columns"]]
        cost_idx = columns.index("Cost")
        svc_idx = columns.index("ServiceName")

        for row in data["properties"]["rows"]:
            svc = row[svc_idx]
            cost = float(row[cost_idx])
            services.append({"service": svc, "cost": round(cost, 2)})
            total += cost

        services.sort(key=lambda x: x["cost"], reverse=True)
        return {"total_monthly_cost": round(total, 2), "services": services, "source": "live"}

    except Exception as e:
        logger.error("Azure API error: %s — falling back to mock data.", e)
        return get_azure_overview()


def fetch_monthly_trends(months=6):
    """Fetch Azure monthly cost trends."""
    if not _is_configured():
        return get_azure_monthly_trends(months)

    try:
        token = _get_access_token()
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        end = datetime.utcnow()
        start = end - timedelta(days=30 * months)

        url = (
            f"{AZURE_MGMT_URL}/subscriptions/{subscription_id}"
            f"/providers/Microsoft.CostManagement/query"
            f"?api-version=2023-03-01"
        )
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "timePeriod": {
                "from": start.strftime("%Y-%m-%dT00:00:00Z"),
                "to": end.strftime("%Y-%m-%dT23:59:59Z"),
            },
            "dataset": {
                "granularity": "Monthly",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            },
        }

        resp = requests.post(url, json=body, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        columns = [col["name"] for col in data["properties"]["columns"]]
        cost_idx = columns.index("Cost")
        month_idx = columns.index("BillingMonth") if "BillingMonth" in columns else 0

        results = []
        for row in data["properties"]["rows"]:
            results.append(
                {"month": str(row[month_idx])[:7], "total": round(float(row[cost_idx]), 2)}
            )
        return results

    except Exception as e:
        logger.error("Azure API error: %s — falling back to mock data.", e)
        return get_azure_monthly_trends(months)
