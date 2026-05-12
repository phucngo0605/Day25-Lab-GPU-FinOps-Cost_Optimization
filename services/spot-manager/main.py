"""Mock Spot Instance Manager - Simulates spot/preemptible GPU instances."""
import os
import time
import random
from typing import Dict, List
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Spot Instance Manager")

PREEMPTION_PROBABILITY = float(os.getenv("PREEMPTION_PROBABILITY", "0.15"))
SPOT_DISCOUNT = float(os.getenv("SPOT_DISCOUNT", "0.70"))

# Track spot instances
spot_instances: Dict[str, dict] = {}
preemption_history: List[dict] = []


class SpotRequest(BaseModel):
    instance_id: str
    gpu_type: str = "T4"
    gpu_count: int = 1
    max_price_per_hour: float = 0.20  # bid price
    workload_id: str = ""


class SpotBid(BaseModel):
    gpu_type: str
    bid_price: float


@app.get("/spot/pricing")
def get_spot_pricing():
    """Get current spot prices (fluctuates)."""
    base_prices = {"T4": 0.35, "A100": 3.67, "V100": 2.48}
    # Simulate price fluctuation
    spot_prices = {}
    for gpu, base in base_prices.items():
        fluctuation = random.uniform(0.2, 0.45)  # 55-80% discount
        spot_prices[gpu] = {
            "on_demand_price": base,
            "current_spot_price": round(base * (1 - fluctuation), 4),
            "discount_pct": round(fluctuation * 100, 1),
            "availability": random.choice(["high", "medium", "low"]),
        }
    return spot_prices


@app.post("/spot/request")
def request_spot_instance(req: SpotRequest):
    """Request a spot instance."""
    base_prices = {"T4": 0.35, "A100": 3.67, "V100": 2.48}
    current_spot = base_prices.get(req.gpu_type, 0.35) * (1 - SPOT_DISCOUNT)

    if req.max_price_per_hour < current_spot:
        return {
            "status": "rejected",
            "reason": f"Bid ${req.max_price_per_hour}/hr below current spot ${current_spot:.4f}/hr",
        }

    spot_instances[req.instance_id] = {
        "instance_id": req.instance_id,
        "gpu_type": req.gpu_type,
        "gpu_count": req.gpu_count,
        "bid_price": req.max_price_per_hour,
        "actual_price": current_spot,
        "workload_id": req.workload_id,
        "status": "running",
        "start_time": time.time(),
        "preempted": False,
    }

    return {"status": "granted", "instance": spot_instances[req.instance_id]}


@app.get("/spot/instances")
def list_spot_instances():
    """List all spot instances."""
    return spot_instances


@app.post("/spot/simulate-preemption")
def simulate_preemption():
    """Simulate spot preemption event (cloud reclaiming instances)."""
    preempted = []
    for inst_id, inst in spot_instances.items():
        if inst["status"] == "running" and random.random() < PREEMPTION_PROBABILITY:
            inst["status"] = "preempted"
            inst["preempted"] = True
            inst["preemption_time"] = time.time()
            event = {
                "instance_id": inst_id,
                "gpu_type": inst["gpu_type"],
                "workload_id": inst["workload_id"],
                "runtime_seconds": time.time() - inst["start_time"],
                "timestamp": time.time(),
                "notice_seconds": random.choice([30, 60, 120]),  # warning time
            }
            preemption_history.append(event)
            preempted.append(event)

    return {
        "preempted_count": len(preempted),
        "preempted_instances": preempted,
        "total_active": sum(1 for i in spot_instances.values() if i["status"] == "running"),
    }


@app.get("/spot/preemption-history")
def get_preemption_history():
    """Get history of preemption events."""
    return preemption_history


@app.post("/spot/{instance_id}/terminate")
def terminate_spot(instance_id: str):
    """Terminate a spot instance."""
    if instance_id in spot_instances:
        inst = spot_instances[instance_id]
        inst["status"] = "terminated"
        inst["end_time"] = time.time()
        runtime = inst["end_time"] - inst["start_time"]
        cost = (runtime / 3600) * inst["actual_price"] * inst["gpu_count"]
        inst["total_cost"] = round(cost, 4)
        return inst
    return {"error": "Instance not found"}


@app.get("/spot/savings-report")
def savings_report():
    """Calculate total savings from using spot vs on-demand."""
    base_prices = {"T4": 0.35, "A100": 3.67, "V100": 2.48}
    total_spot_cost = 0
    total_on_demand_equivalent = 0

    for inst in spot_instances.values():
        if inst.get("end_time") or inst["status"] == "running":
            end = inst.get("end_time", time.time())
            runtime_hours = (end - inst["start_time"]) / 3600
            spot_cost = runtime_hours * inst["actual_price"] * inst["gpu_count"]
            od_cost = runtime_hours * base_prices.get(inst["gpu_type"], 0.35) * inst["gpu_count"]
            total_spot_cost += spot_cost
            total_on_demand_equivalent += od_cost

    return {
        "total_spot_cost": round(total_spot_cost, 4),
        "on_demand_equivalent": round(total_on_demand_equivalent, 4),
        "total_savings": round(total_on_demand_equivalent - total_spot_cost, 4),
        "savings_pct": round(
            ((total_on_demand_equivalent - total_spot_cost) / max(total_on_demand_equivalent, 0.001)) * 100, 2
        ),
        "preemption_count": len(preemption_history),
        "active_instances": sum(1 for i in spot_instances.values() if i["status"] == "running"),
    }
