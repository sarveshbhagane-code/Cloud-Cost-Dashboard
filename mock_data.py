"""
mock_data.py
Generates realistic mock data for AWS and Azure cloud costs.
Used in DEMO mode when real credentials are not configured.
"""

import random
from datetime import datetime, timedelta


# ─────────────────────────────────────────────
# AWS Mock Data
# ─────────────────────────────────────────────

AWS_SERVICES = [
    "Amazon EC2",
    "Amazon S3",
    "Amazon RDS",
    "AWS Lambda",
    "Amazon CloudFront",
    "Amazon DynamoDB",
    "Amazon EKS",
    "AWS Glue",
    "Amazon SageMaker",
    "AWS Data Transfer",
]

AWS_REGIONS = [
    "us-east-1",
    "us-west-2",
    "eu-west-1",
    "ap-southeast-1",
    "ap-south-1",
    "ca-central-1",
]

# Base monthly spend per service (USD)
SERVICE_BASE_COSTS = {
    "Amazon EC2": 1240.50,
    "Amazon S3": 380.75,
    "Amazon RDS": 620.30,
    "AWS Lambda": 145.20,
    "Amazon CloudFront": 210.80,
    "Amazon DynamoDB": 95.60,
    "Amazon EKS": 485.90,
    "AWS Glue": 175.40,
    "Amazon SageMaker": 340.10,
    "AWS Data Transfer": 88.25,
}

REGION_WEIGHTS = {
    "us-east-1": 0.40,
    "us-west-2": 0.22,
    "eu-west-1": 0.18,
    "ap-southeast-1": 0.10,
    "ap-south-1": 0.07,
    "ca-central-1": 0.03,
}


def _jitter(value, pct=0.12):
    """Add ±pct% random noise to a value."""
    return round(value * (1 + random.uniform(-pct, pct)), 2)


def get_aws_overview():
    """Return high-level monthly overview data."""
    total = sum(_jitter(v) for v in SERVICE_BASE_COSTS.values())
    prev_total = sum(_jitter(v, 0.08) for v in SERVICE_BASE_COSTS.values())
    change_pct = round(((total - prev_total) / prev_total) * 100, 1)

    services = [
        {"service": svc, "cost": _jitter(cost)}
        for svc, cost in SERVICE_BASE_COSTS.items()
    ]
    services.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "total_monthly_cost": round(total, 2),
        "previous_month_cost": round(prev_total, 2),
        "change_pct": change_pct,
        "forecasted_cost": round(total * 1.04, 2),
        "active_resources": random.randint(138, 165),
        "budget_utilization": round(random.uniform(72, 91), 1),
        "services": services,
        "top_service": services[0]["service"],
    }


def get_aws_daily_trends(days=30):
    """Return daily cost trends for the past N days."""
    end_date = datetime.utcnow()
    result = []
    for i in range(days - 1, -1, -1):
        day = end_date - timedelta(days=i)
        daily_total = 0
        services_day = {}
        for svc, base in SERVICE_BASE_COSTS.items():
            daily_cost = _jitter(base / 30, 0.20)
            services_day[svc] = round(daily_cost, 2)
            daily_total += daily_cost
        result.append(
            {
                "date": day.strftime("%Y-%m-%d"),
                "total": round(daily_total, 2),
                "services": services_day,
            }
        )
    return result


def get_aws_monthly_trends(months=6):
    """Return monthly cost trends for the past N months."""
    end_date = datetime.utcnow()
    result = []
    for i in range(months - 1, -1, -1):
        month_date = end_date - timedelta(days=30 * i)
        monthly_total = sum(_jitter(v, 0.15) for v in SERVICE_BASE_COSTS.values())
        result.append(
            {
                "month": month_date.strftime("%b %Y"),
                "total": round(monthly_total, 2),
            }
        )
    return result


def get_aws_region_costs():
    """Return cost breakdown per AWS region."""
    total = sum(SERVICE_BASE_COSTS.values())
    return [
        {"region": region, "cost": round(total * weight, 2)}
        for region, weight in REGION_WEIGHTS.items()
    ]


# ─────────────────────────────────────────────
# Azure Mock Data
# ─────────────────────────────────────────────

AZURE_SERVICES = [
    "Azure Virtual Machines",
    "Azure Blob Storage",
    "Azure SQL Database",
    "Azure Functions",
    "Azure CDN",
    "Azure Cosmos DB",
    "Azure Kubernetes Service",
    "Azure Machine Learning",
    "Azure Cognitive Services",
    "Azure Bandwidth",
]

AZURE_SERVICE_BASE_COSTS = {
    "Azure Virtual Machines": 1080.00,
    "Azure Blob Storage": 295.50,
    "Azure SQL Database": 540.80,
    "Azure Functions": 120.30,
    "Azure CDN": 185.60,
    "Azure Cosmos DB": 310.40,
    "Azure Kubernetes Service": 420.70,
    "Azure Machine Learning": 290.20,
    "Azure Cognitive Services": 155.90,
    "Azure Bandwidth": 75.10,
}


def get_azure_overview():
    """Return Azure high-level monthly overview."""
    total = sum(_jitter(v) for v in AZURE_SERVICE_BASE_COSTS.values())
    services = [
        {"service": svc, "cost": _jitter(cost)}
        for svc, cost in AZURE_SERVICE_BASE_COSTS.items()
    ]
    services.sort(key=lambda x: x["cost"], reverse=True)
    return {
        "total_monthly_cost": round(total, 2),
        "services": services,
    }


def get_azure_monthly_trends(months=6):
    """Return Azure monthly cost trends."""
    end_date = datetime.utcnow()
    result = []
    for i in range(months - 1, -1, -1):
        month_date = end_date - timedelta(days=30 * i)
        monthly_total = sum(_jitter(v, 0.15) for v in AZURE_SERVICE_BASE_COSTS.values())
        result.append(
            {
                "month": month_date.strftime("%b %Y"),
                "total": round(monthly_total, 2),
            }
        )
    return result
