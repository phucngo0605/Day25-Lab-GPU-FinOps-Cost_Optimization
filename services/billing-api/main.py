"""Mock Billing API - Simulates cloud provider billing and cost tracking."""
import os
import time
from typing import Dict, List
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Billing API")

# Pricing per hour (USD)
PRICING = {
    "T4": float(os.getenv("T4_PRICE_PER_HOUR", "0.35")),
    "A100": float(os.getenv("A100_PRICE_PER_HOUR", "3.67")),
    "V100": float(os.getenv("V100_PRICE_PER_HOUR", "2.48")),
}
SPOT_DISCOUNT = float(os.getenv("SPOT_DISCOUNT", "0.70"))

# In-memory billing records
billing_records: List[dict] = []
budgets: Dict[str, float] = {"default": 100.0}  # project -> budget


class BillingEvent(BaseModel):
    workload_id: str
    gpu_type: str
    gpu_count: int
    duration_seconds: float
    is_spot: bool = False
    project: str = "default"


class BudgetRequest(BaseModel):
    project: str
    budget_usd: float


@app.get("/pricing")
def get_pricing():
    """Get current GPU pricing."""
    return {
        "on_demand": PRICING,
        "spot": {k: round(v * (1 - SPOT_DISCOUNT), 4) for k, v in PRICING.items()},
        "spot_discount_pct": SPOT_DISCOUNT * 100,
    }


@app.post("/record")
def record_billing(event: BillingEvent):
    """Record a billing event for a completed workload."""
    hours = event.duration_seconds / 3600
    base_rate = PRICING.get(event.gpu_type, PRICING["T4"])
    if event.is_spot:
        rate = base_rate * (1 - SPOT_DISCOUNT)
    else:
        rate = base_rate

    cost = rate * hours * event.gpu_count
    savings = (base_rate * hours * event.gpu_count) - cost if event.is_spot else 0

    record = {
        "workload_id": event.workload_id,
        "gpu_type": event.gpu_type,
        "gpu_count": event.gpu_count,
        "duration_seconds": event.duration_seconds,
        "is_spot": event.is_spot,
        "rate_per_hour": round(rate, 4),
        "total_cost_usd": round(cost, 4),
        "savings_usd": round(savings, 4),
        "project": event.project,
        "timestamp": time.time(),
    }
    billing_records.append(record)
    return record


@app.get("/records")
def get_records(project: str = None):
    """Get all billing records, optionally filtered by project."""
    if project:
        return [r for r in billing_records if r["project"] == project]
    return billing_records


@app.get("/summary")
def get_summary(project: str = "default"):
    """Get billing summary for a project."""
    project_records = [r for r in billing_records if r["project"] == project]
    total_cost = sum(r["total_cost_usd"] for r in project_records)
    total_savings = sum(r["savings_usd"] for r in project_records)
    budget = budgets.get(project, 100.0)

    by_gpu_type = {}
    for r in project_records:
        gt = r["gpu_type"]
        if gt not in by_gpu_type:
            by_gpu_type[gt] = {"cost": 0, "hours": 0, "workloads": 0}
        by_gpu_type[gt]["cost"] += r["total_cost_usd"]
        by_gpu_type[gt]["hours"] += r["duration_seconds"] / 3600
        by_gpu_type[gt]["workloads"] += 1

    return {
        "project": project,
        "total_cost_usd": round(total_cost, 4),
        "total_savings_usd": round(total_savings, 4),
        "budget_usd": budget,
        "budget_remaining_usd": round(budget - total_cost, 4),
        "budget_utilization_pct": round((total_cost / budget) * 100, 2) if budget > 0 else 0,
        "total_workloads": len(project_records),
        "cost_by_gpu_type": by_gpu_type,
        "alert": "OVER_BUDGET" if total_cost > budget else ("WARNING" if total_cost > budget * 0.8 else "OK"),
    }


@app.post("/budget")
def set_budget(req: BudgetRequest):
    """Set budget for a project."""
    budgets[req.project] = req.budget_usd
    return {"project": req.project, "budget_usd": req.budget_usd}


@app.get("/budget/{project}")
def get_budget(project: str):
    """Get budget for a project."""
    return {"project": project, "budget_usd": budgets.get(project, 100.0)}


@app.get("/forecast")
def get_forecast(project: str = "default", hours_ahead: int = 24):
    """Forecast cost based on recent burn rate."""
    project_records = [r for r in billing_records if r["project"] == project]
    if len(project_records) < 2:
        return {"forecast": "insufficient_data"}

    # Calculate burn rate from last N records
    recent = project_records[-10:]
    time_span = recent[-1]["timestamp"] - recent[0]["timestamp"]
    if time_span <= 0:
        return {"forecast": "insufficient_data"}

    cost_in_span = sum(r["total_cost_usd"] for r in recent)
    burn_rate_per_hour = cost_in_span / (time_span / 3600)

    budget = budgets.get(project, 100.0)
    current_total = sum(r["total_cost_usd"] for r in project_records)
    remaining = budget - current_total
    hours_to_exhaust = remaining / burn_rate_per_hour if burn_rate_per_hour > 0 else float("inf")

    return {
        "burn_rate_per_hour": round(burn_rate_per_hour, 4),
        "forecast_cost_next_hours": round(burn_rate_per_hour * hours_ahead, 4),
        "hours_until_budget_exhausted": round(hours_to_exhaust, 2),
        "current_total_cost": round(current_total, 4),
        "budget_remaining": round(remaining, 4),
    }
