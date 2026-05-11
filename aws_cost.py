"""
aws_cost.py
AWS Cost Explorer API integration using boto3.
Falls back to mock data automatically if credentials are not configured.
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed. Running in mock mode.")

from mock_data import (
    get_aws_overview,
    get_aws_daily_trends,
    get_aws_monthly_trends,
    get_aws_region_costs,
)


def _is_configured():
    """Check if AWS credentials are configured."""
    if not BOTO3_AVAILABLE:
        return False
    key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    return bool(key_id and secret and key_id != "your_access_key_here")


def _get_client():
    """Create and return a Cost Explorer boto3 client."""
    return boto3.client(
        "ce",
        region_name="us-east-1",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


# ─────────────────────────────────────────────
# Public API Functions
# ─────────────────────────────────────────────

def fetch_overview():
    """
    Fetch monthly cost overview from AWS Cost Explorer.
    Returns mock data if credentials are not configured.
    """
    if not _is_configured():
        logger.info("AWS not configured — using mock data.")
        return get_aws_overview()

    try:
        client = _get_client()
        today = datetime.utcnow()
        start = today.replace(day=1).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        response = client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        services = []
        total = 0.0
        for result in response["ResultsByTime"]:
            for group in result["Groups"]:
                svc = group["Keys"][0]
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                services.append({"service": svc, "cost": round(cost, 2)})
                total += cost

        services.sort(key=lambda x: x["cost"], reverse=True)
        return {
            "total_monthly_cost": round(total, 2),
            "services": services,
            "source": "live",
        }

    except (NoCredentialsError, ClientError) as e:
        logger.error("AWS API error: %s — falling back to mock data.", e)
        return get_aws_overview()


def fetch_daily_trends(days=30):
    """Fetch daily cost trends from AWS Cost Explorer."""
    if not _is_configured():
        return get_aws_daily_trends(days)

    try:
        client = _get_client()
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        response = client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        results = []
        for result in response["ResultsByTime"]:
            date = result["TimePeriod"]["Start"]
            daily_total = 0.0
            services = {}
            for group in result["Groups"]:
                svc = group["Keys"][0]
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                services[svc] = round(cost, 2)
                daily_total += cost
            results.append(
                {"date": date, "total": round(daily_total, 2), "services": services}
            )
        return results

    except (NoCredentialsError, ClientError) as e:
        logger.error("AWS API error: %s — falling back to mock data.", e)
        return get_aws_daily_trends(days)


def fetch_monthly_trends(months=6):
    """Fetch monthly cost trends from AWS Cost Explorer."""
    if not _is_configured():
        return get_aws_monthly_trends(months)

    try:
        client = _get_client()
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=30 * months)).strftime("%Y-%m-%d")

        response = client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )

        results = []
        for result in response["ResultsByTime"]:
            month = result["TimePeriod"]["Start"][:7]
            cost = float(result["Total"]["UnblendedCost"]["Amount"])
            results.append({"month": month, "total": round(cost, 2)})
        return results

    except (NoCredentialsError, ClientError) as e:
        logger.error("AWS API error: %s — falling back to mock data.", e)
        return get_aws_monthly_trends(months)


def fetch_region_costs():
    """Fetch cost breakdown by AWS region."""
    if not _is_configured():
        return get_aws_region_costs()

    try:
        client = _get_client()
        today = datetime.utcnow()
        start = today.replace(day=1).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        response = client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "REGION"}],
        )

        results = []
        for result in response["ResultsByTime"]:
            for group in result["Groups"]:
                region = group["Keys"][0]
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                results.append({"region": region, "cost": round(cost, 2)})
        return sorted(results, key=lambda x: x["cost"], reverse=True)

    except (NoCredentialsError, ClientError) as e:
        logger.error("AWS API error: %s — falling back to mock data.", e)
        return get_aws_region_costs()
