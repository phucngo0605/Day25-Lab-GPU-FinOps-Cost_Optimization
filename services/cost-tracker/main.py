"""OpenCost-like Cost Tracker - Aggregates and reports GPU cost allocation."""
import os
import time
from typing import Dict, List
from fastapi import FastAPI
from pydantic import BaseModel
import httpx

app = FastAPI(title="Cost Tracker (OpenCost-like)")

AGGREGATION_INTERVAL = int(os.getenv("AGGREGATION_INTERVAL", "10"))
GPU_NODE_URL = "http://gpu-node-manager:8000"
BILLING_URL = "http://billing-api:8000"
SPOT_URL = "http://spot-manager:8000"

# Cost allocation data
cost_allocations: List[dict] = []
recommendations: List[dict] = []


class CostWindow(BaseModel):
    start_time: float = 0
    end_time: float = 0


@app.post("/snapshot")
async def take_cost_snapshot():
    """Take a point-in-time cost snapshot of the cluster."""
    async with httpx.AsyncClient() as client:
        try:
            nodes_resp = await client.get(f"{GPU_NODE_URL}/nodes")
            nodes = nodes_resp.json()
        except Exception:
            nodes = {}

        try:
            billing_resp = await client.get(f"{BILLING_URL}/summary")
            billing = billing_resp.json()
        except Exception:
            billing = {"total_cost_usd": 0}

        try:
            spot_resp = await client.get(f"{SPOT_URL}/spot/savings-report")
            spot = spot_resp.json()
        except Exception:
            spot = {"total_savings": 0}

    # Calculate per-node costs
    pricing = {"T4": 0.35, "A100": 3.67, "V100": 2.48}
    node_costs = {}
    total_idle_cost = 0
    total_active_cost = 0

    for node_id, gpus in nodes.items():
        node_cost = 0
        node_idle_cost = 0
        for gpu in gpus:
            gpu_type = gpu.get("gpu_type", "T4") if isinstance(gpu, dict) else gpu.gpu_type
            status = gpu.get("status", "idle") if isinstance(gpu, dict) else gpu.status
            rate = pricing.get(gpu_type, 0.35) / 3600  # per second
            # Even idle GPUs cost money (you're paying for the instance)
            cost_per_interval = rate * AGGREGATION_INTERVAL
            node_cost += cost_per_interval
            if status == "idle":
                node_idle_cost += cost_per_interval
                total_idle_cost += cost_per_interval
            else:
                total_active_cost += cost_per_interval

        node_costs[node_id] = {
            "total_cost": round(node_cost, 6),
            "idle_cost": round(node_idle_cost, 6),
            "gpu_count": len(gpus),
        }

    snapshot = {
        "timestamp": time.time(),
        "node_costs": node_costs,
        "total_idle_cost_usd": round(total_idle_cost, 6),
        "total_active_cost_usd": round(total_active_cost, 6),
        "total_cost_usd": round(total_idle_cost + total_active_cost, 6),
        "waste_pct": round(
            (total_idle_cost / max(total_idle_cost + total_active_cost, 0.0001)) * 100, 2
        ),
        "cumulative_billing": billing,
        "spot_savings": spot,
    }
    cost_allocations.append(snapshot)
    return snapshot


@app.get("/allocations")
def get_allocations(last_n: int = 20):
    """Get recent cost allocation snapshots."""
    return cost_allocations[-last_n:]


@app.get("/waste-report")
def get_waste_report():
    """Analyze cost waste (idle GPUs, over-provisioned resources)."""
    if not cost_allocations:
        return {"message": "No data yet. Take a snapshot first."}

    recent = cost_allocations[-10:]
    avg_waste_pct = sum(s["waste_pct"] for s in recent) / len(recent)
    total_idle_cost = sum(s["total_idle_cost_usd"] for s in recent)
    total_cost = sum(s["total_cost_usd"] for s in recent)

    return {
        "analysis_window_snapshots": len(recent),
        "avg_waste_pct": round(avg_waste_pct, 2),
        "total_idle_cost_usd": round(total_idle_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "potential_monthly_savings": round(total_idle_cost * (30 * 24 * 3600 / AGGREGATION_INTERVAL / len(recent)), 2),
        "severity": "HIGH" if avg_waste_pct > 50 else ("MEDIUM" if avg_waste_pct > 30 else "LOW"),
    }


@app.post("/recommendations")
async def generate_recommendations():
    """Generate cost optimization recommendations."""
    recs = []

    async with httpx.AsyncClient() as client:
        try:
            metrics_resp = await client.get(f"{GPU_NODE_URL}/metrics")
            metrics = metrics_resp.json()
        except Exception:
            metrics = {"avg_utilization": 50, "idle_gpus": 2, "total_gpus": 8, "node_count": 4}

    # Low utilization → right-size
    if metrics["avg_utilization"] < 30:
        recs.append({
            "type": "RIGHT_SIZE",
            "priority": "HIGH",
            "description": f"Average GPU utilization is {metrics['avg_utilization']:.1f}%. Consider downsizing to fewer/smaller GPUs.",
            "estimated_savings_pct": round(50 - metrics["avg_utilization"], 1),
        })

    # Many idle GPUs → scale down
    if metrics["idle_gpus"] > metrics["total_gpus"] * 0.5:
        recs.append({
            "type": "SCALE_DOWN",
            "priority": "HIGH",
            "description": f"{metrics['idle_gpus']}/{metrics['total_gpus']} GPUs are idle. Scale down {metrics['idle_gpus'] // 2} nodes.",
            "estimated_savings_pct": round((metrics["idle_gpus"] / metrics["total_gpus"]) * 50, 1),
        })

    # Suggest spot instances
    recs.append({
        "type": "USE_SPOT",
        "priority": "MEDIUM",
        "description": "Switch fault-tolerant workloads to spot instances for 60-70% savings.",
        "estimated_savings_pct": 65.0,
    })

    # Suggest scheduling
    recs.append({
        "type": "SCHEDULING",
        "priority": "LOW",
        "description": "Schedule non-urgent training jobs during off-peak hours for lower spot prices.",
        "estimated_savings_pct": 20.0,
    })

    recommendations.clear()
    recommendations.extend(recs)
    return recs


@app.get("/recommendations")
def get_recommendations():
    """Get latest recommendations."""
    return recommendations


@app.get("/dashboard")
async def get_dashboard():
    """Get a unified dashboard view combining all metrics."""
    async with httpx.AsyncClient() as client:
        try:
            metrics = (await client.get(f"{GPU_NODE_URL}/metrics")).json()
        except Exception:
            metrics = {}
        try:
            billing = (await client.get(f"{BILLING_URL}/summary")).json()
        except Exception:
            billing = {}
        try:
            spot = (await client.get(f"{SPOT_URL}/spot/savings-report")).json()
        except Exception:
            spot = {}

    waste = get_waste_report() if cost_allocations else {}

    return {
        "cluster_metrics": metrics,
        "billing_summary": billing,
        "spot_savings": spot,
        "waste_analysis": waste,
        "snapshot_count": len(cost_allocations),
    }
