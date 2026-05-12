"""KEDA-like Autoscaler Simulator - Scales GPU nodes based on metrics."""
import os
import time
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
import httpx

app = FastAPI(title="GPU Autoscaler (KEDA-like)")

SCALE_UP_THRESHOLD = float(os.getenv("SCALE_UP_THRESHOLD", "80"))
SCALE_DOWN_THRESHOLD = float(os.getenv("SCALE_DOWN_THRESHOLD", "20"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "60"))
MAX_NODES = int(os.getenv("MAX_NODES", "8"))
MIN_NODES = int(os.getenv("MIN_NODES", "1"))

GPU_NODE_URL = "http://gpu-node-manager:8000"
BILLING_URL = "http://billing-api:8000"

# Autoscaler state
scaling_history: List[dict] = []
last_scale_time = 0
current_policy = {
    "scale_up_threshold": SCALE_UP_THRESHOLD,
    "scale_down_threshold": SCALE_DOWN_THRESHOLD,
    "cooldown_seconds": COOLDOWN_SECONDS,
    "max_nodes": MAX_NODES,
    "min_nodes": MIN_NODES,
    "preferred_gpu_type": "T4",
    "cost_aware": True,  # prefer cheaper GPUs when scaling
}


class ScalingPolicy(BaseModel):
    scale_up_threshold: float = 80
    scale_down_threshold: float = 20
    cooldown_seconds: int = 60
    max_nodes: int = 8
    min_nodes: int = 1
    preferred_gpu_type: str = "T4"
    cost_aware: bool = True


class ScaleDecision(BaseModel):
    action: str  # "scale_up", "scale_down", "no_action"
    reason: str
    current_utilization: float
    node_count: int
    target_node_count: int


@app.get("/policy")
def get_policy():
    """Get current autoscaling policy."""
    return current_policy


@app.post("/policy")
def update_policy(policy: ScalingPolicy):
    """Update autoscaling policy."""
    global current_policy
    current_policy = policy.model_dump()
    return current_policy


@app.post("/evaluate")
async def evaluate_scaling():
    """Evaluate current metrics and decide whether to scale."""
    global last_scale_time

    # Get cluster metrics
    async with httpx.AsyncClient() as client:
        try:
            metrics_resp = await client.get(f"{GPU_NODE_URL}/metrics")
            metrics = metrics_resp.json()
        except Exception:
            # Fallback mock metrics
            metrics = {
                "avg_utilization": 50,
                "node_count": 4,
                "total_gpus": 8,
                "busy_gpus": 4,
                "idle_gpus": 4,
            }

    avg_util = metrics["avg_utilization"]
    node_count = metrics["node_count"]
    now = time.time()

    # Cooldown check
    if now - last_scale_time < current_policy["cooldown_seconds"]:
        decision = ScaleDecision(
            action="no_action",
            reason=f"Cooldown active ({int(current_policy['cooldown_seconds'] - (now - last_scale_time))}s remaining)",
            current_utilization=avg_util,
            node_count=node_count,
            target_node_count=node_count,
        )
        scaling_history.append({"decision": decision.model_dump(), "timestamp": now})
        return decision

    # Scale up decision
    if avg_util > current_policy["scale_up_threshold"] and node_count < current_policy["max_nodes"]:
        target = min(node_count + 1, current_policy["max_nodes"])

        # Actually scale up
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"{GPU_NODE_URL}/nodes/scale-up",
                    params={"gpu_type": current_policy["preferred_gpu_type"], "count": 1},
                )
            except Exception:
                pass

        last_scale_time = now
        decision = ScaleDecision(
            action="scale_up",
            reason=f"Utilization {avg_util:.1f}% > threshold {current_policy['scale_up_threshold']}%",
            current_utilization=avg_util,
            node_count=node_count,
            target_node_count=target,
        )
        scaling_history.append({"decision": decision.model_dump(), "timestamp": now})
        return decision

    # Scale down decision
    if avg_util < current_policy["scale_down_threshold"] and node_count > current_policy["min_nodes"]:
        target = max(node_count - 1, current_policy["min_nodes"])
        last_scale_time = now
        decision = ScaleDecision(
            action="scale_down",
            reason=f"Utilization {avg_util:.1f}% < threshold {current_policy['scale_down_threshold']}%",
            current_utilization=avg_util,
            node_count=node_count,
            target_node_count=target,
        )
        scaling_history.append({"decision": decision.model_dump(), "timestamp": now})
        return decision

    # No action needed
    decision = ScaleDecision(
        action="no_action",
        reason=f"Utilization {avg_util:.1f}% within thresholds [{current_policy['scale_down_threshold']}-{current_policy['scale_up_threshold']}%]",
        current_utilization=avg_util,
        node_count=node_count,
        target_node_count=node_count,
    )
    scaling_history.append({"decision": decision.model_dump(), "timestamp": now})
    return decision


@app.get("/history")
def get_scaling_history():
    """Get scaling decision history."""
    return scaling_history


@app.get("/metrics")
async def get_autoscaler_metrics():
    """Get autoscaler's own metrics."""
    scale_ups = sum(1 for h in scaling_history if h["decision"]["action"] == "scale_up")
    scale_downs = sum(1 for h in scaling_history if h["decision"]["action"] == "scale_down")
    return {
        "total_evaluations": len(scaling_history),
        "scale_up_events": scale_ups,
        "scale_down_events": scale_downs,
        "no_action_events": len(scaling_history) - scale_ups - scale_downs,
        "current_policy": current_policy,
        "last_scale_time": last_scale_time,
    }
