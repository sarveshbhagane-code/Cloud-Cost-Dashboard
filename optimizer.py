"""
optimizer.py
Rule-based cloud cost optimization engine.
Analyzes mock/live cost data and generates actionable recommendations
with estimated savings amounts.
"""

from mock_data import SERVICE_BASE_COSTS


# ─────────────────────────────────────────────
# Optimization Rules
# ─────────────────────────────────────────────

OPTIMIZATION_RULES = [
    {
        "id": "ri-ec2",
        "service": "Amazon EC2",
        "category": "Reserved Instances",
        "severity": "high",
        "title": "Switch EC2 On-Demand to Reserved Instances",
        "description": (
            "Your EC2 fleet is running entirely on On-Demand pricing. "
            "Converting baseline workloads to 1-year Reserved Instances can save "
            "up to 40% compared to On-Demand rates."
        ),
        "action": "Purchase Reserved Instances for steady-state EC2 workloads.",
        "savings_pct": 0.38,
        "effort": "Medium",
        "icon": "💡",
    },
    {
        "id": "rightsizing-ec2",
        "service": "Amazon EC2",
        "category": "Right-Sizing",
        "severity": "high",
        "title": "Right-Size Underutilized EC2 Instances",
        "description": (
            "CloudWatch metrics indicate 6 EC2 instances with average CPU utilization "
            "below 10% over the past 14 days. Downsizing these to the next smaller "
            "instance type will reduce costs significantly."
        ),
        "action": "Review and downsize instances with CPU < 10% using AWS Compute Optimizer.",
        "savings_pct": 0.22,
        "effort": "Low",
        "icon": "📉",
    },
    {
        "id": "s3-lifecycle",
        "service": "Amazon S3",
        "category": "Storage Optimization",
        "severity": "medium",
        "title": "Enable S3 Intelligent-Tiering",
        "description": (
            "Your S3 buckets contain data that hasn't been accessed in over 30 days. "
            "Enabling Intelligent-Tiering or transitioning objects to S3-IA/Glacier "
            "could reduce storage costs by up to 58%."
        ),
        "action": "Add lifecycle rules to transition objects older than 30 days to S3-IA.",
        "savings_pct": 0.45,
        "effort": "Low",
        "icon": "🗄️",
    },
    {
        "id": "rds-multi-az",
        "service": "Amazon RDS",
        "category": "Architecture",
        "severity": "medium",
        "title": "Evaluate RDS Multi-AZ Necessity",
        "description": (
            "Non-production RDS instances are running in Multi-AZ mode, doubling "
            "the instance cost. Disabling Multi-AZ for dev/test environments and "
            "using automated snapshots instead is recommended."
        ),
        "action": "Disable Multi-AZ on dev/staging RDS instances.",
        "savings_pct": 0.50,
        "effort": "Low",
        "icon": "🔧",
    },
    {
        "id": "lambda-timeout",
        "service": "AWS Lambda",
        "category": "Performance Tuning",
        "severity": "low",
        "title": "Optimize Lambda Memory & Timeout Settings",
        "description": (
            "Several Lambda functions have over-provisioned memory allocations "
            "(2048 MB) but average under 256 MB usage. Right-sizing memory and "
            "reducing timeouts can lower costs by 18-25%."
        ),
        "action": "Use AWS Lambda Power Tuning tool to find optimal memory size.",
        "savings_pct": 0.20,
        "effort": "Low",
        "icon": "⚡",
    },
    {
        "id": "cloudfront-cache",
        "service": "Amazon CloudFront",
        "category": "Caching",
        "severity": "low",
        "title": "Improve CloudFront Cache Hit Ratio",
        "description": (
            "CloudFront cache hit rate is below 60%, causing excess origin requests. "
            "Tuning cache behaviors and TTL values can reduce data transfer costs "
            "by 25-35%."
        ),
        "action": "Review cache behaviors and increase default TTL for static assets.",
        "savings_pct": 0.28,
        "effort": "Medium",
        "icon": "🌐",
    },
    {
        "id": "eks-spot",
        "service": "Amazon EKS",
        "category": "Spot Instances",
        "severity": "high",
        "title": "Use Spot Instances for EKS Worker Nodes",
        "description": (
            "EKS worker nodes are running on On-Demand instances. Migrating "
            "non-critical workloads to Spot Instances can save up to 70%."
        ),
        "action": "Configure EKS managed node groups with Spot Instance types.",
        "savings_pct": 0.65,
        "effort": "High",
        "icon": "☁️",
    },
    {
        "id": "idle-ebs",
        "service": "Amazon EC2",
        "category": "Idle Resources",
        "severity": "medium",
        "title": "Delete Unattached EBS Volumes",
        "description": (
            "Detected 12 EBS volumes that are not attached to any running instance "
            "and have been idle for more than 30 days. These incur storage costs "
            "without providing value."
        ),
        "action": "Take a final snapshot, then delete unattached EBS volumes.",
        "savings_pct": 0.08,
        "effort": "Low",
        "icon": "🗑️",
    },
    {
        "id": "savings-plans",
        "service": "General",
        "category": "Savings Plans",
        "severity": "high",
        "title": "Purchase Compute Savings Plans",
        "description": (
            "Your compute usage pattern is consistent and predictable. Committing to "
            "a 1-year Compute Savings Plan would automatically apply up to 66% "
            "discount across EC2, Lambda, and Fargate."
        ),
        "action": "Purchase Compute Savings Plans in AWS Cost Explorer.",
        "savings_pct": 0.30,
        "effort": "Medium",
        "icon": "💰",
    },
]


def get_optimizations(cost_data: dict | None = None) -> list:
    """
    Returns optimization recommendations with estimated savings amounts.
    cost_data: dict mapping service name → monthly cost.
               Uses default mock costs if None.
    """
    if cost_data is None:
        cost_data = SERVICE_BASE_COSTS

    # Build a lookup: service name → cost
    service_cost_map = {}
    for item in (
        cost_data if isinstance(cost_data, list) else [
            {"service": k, "cost": v} for k, v in cost_data.items()
        ]
    ):
        service_cost_map[item.get("service", "")] = item.get("cost", 0)

    results = []
    for rule in OPTIMIZATION_RULES:
        base_cost = service_cost_map.get(rule["service"], 300.0)
        savings = round(base_cost * rule["savings_pct"], 2)
        results.append(
            {
                "id": rule["id"],
                "service": rule["service"],
                "category": rule["category"],
                "severity": rule["severity"],
                "title": rule["title"],
                "description": rule["description"],
                "action": rule["action"],
                "estimated_savings_usd": savings,
                "effort": rule["effort"],
                "icon": rule["icon"],
            }
        )

    # Sort: high severity first, then by savings descending
    severity_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(
        key=lambda x: (severity_order.get(x["severity"], 3), -x["estimated_savings_usd"])
    )
    return results


def get_total_potential_savings(cost_data=None) -> float:
    """Return total potential monthly savings across all recommendations."""
    recommendations = get_optimizations(cost_data)
    return round(sum(r["estimated_savings_usd"] for r in recommendations), 2)
