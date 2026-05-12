"""Mock GPU Node Manager - Simulates a multi-node GPU cluster."""
import os
import time
import random
from typing import Dict, List
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="GPU Node Manager")

NUM_NODES = int(os.getenv("NUM_NODES", "4"))
GPUS_PER_NODE = int(os.getenv("GPUS_PER_NODE", "2"))
GPU_TYPES = os.getenv("GPU_TYPES", "T4,A100,V100,T4").split(",")

GPU_SPECS = {
    "T4": {"memory_gb": 16, "tflops_fp16": 65, "tdp_watts": 70},
    "A100": {"memory_gb": 80, "tflops_fp16": 312, "tdp_watts": 300},
    "V100": {"memory_gb": 32, "tflops_fp16": 125, "tdp_watts": 300},
}


class GPUState(BaseModel):
    node_id: str
    gpu_id: int
    gpu_type: str
    utilization: float  # 0-100
    memory_used_gb: float
    memory_total_gb: float
    power_draw_watts: float
    temperature_c: float
    status: str  # "idle", "running", "preempted", "offline"
    workload_id: str | None = None


class WorkloadRequest(BaseModel):
    workload_id: str
    gpu_type_preferred: str = "T4"
    gpu_count: int = 1
    duration_seconds: int = 60


# Global cluster state
cluster: Dict[str, List[GPUState]] = {}
workloads: Dict[str, dict] = {}


def init_cluster():
    """Initialize mock cluster state."""
    for i in range(NUM_NODES):
        gpu_type = GPU_TYPES[i % len(GPU_TYPES)]
        specs = GPU_SPECS.get(gpu_type, GPU_SPECS["T4"])
        node_id = f"node-{i:02d}"
        cluster[node_id] = []
        for g in range(GPUS_PER_NODE):
            cluster[node_id].append(GPUState(
                node_id=node_id,
                gpu_id=g,
                gpu_type=gpu_type,
                utilization=random.uniform(0, 15),
                memory_used_gb=random.uniform(0.5, 2.0),
                memory_total_gb=specs["memory_gb"],
                power_draw_watts=random.uniform(20, 50),
                temperature_c=random.uniform(30, 45),
                status="idle",
            ))


init_cluster()


@app.get("/nodes")
def get_nodes():
    """Get all nodes and their GPU states."""
    return cluster


@app.get("/nodes/{node_id}")
def get_node(node_id: str):
    """Get specific node GPU states."""
    if node_id in cluster:
        return cluster[node_id]
    return {"error": "Node not found"}


@app.get("/metrics")
def get_metrics():
    """Get aggregated cluster metrics."""
    total_gpus = 0
    busy_gpus = 0
    total_util = 0.0
    total_memory_used = 0.0
    total_memory_cap = 0.0
    total_power = 0.0

    for node_id, gpus in cluster.items():
        for gpu in gpus:
            total_gpus += 1
            total_util += gpu.utilization
            total_memory_used += gpu.memory_used_gb
            total_memory_cap += gpu.memory_total_gb
            total_power += gpu.power_draw_watts
            if gpu.status == "running":
                busy_gpus += 1

    return {
        "total_gpus": total_gpus,
        "busy_gpus": busy_gpus,
        "idle_gpus": total_gpus - busy_gpus,
        "avg_utilization": total_util / max(total_gpus, 1),
        "total_memory_used_gb": round(total_memory_used, 2),
        "total_memory_capacity_gb": round(total_memory_cap, 2),
        "total_power_draw_watts": round(total_power, 2),
        "node_count": len(cluster),
    }


@app.post("/workloads/submit")
def submit_workload(req: WorkloadRequest):
    """Submit a workload to the cluster - finds available GPU and assigns."""
    # Find available GPU matching preference
    assigned = []
    for node_id, gpus in cluster.items():
        for gpu in gpus:
            if gpu.status == "idle" and gpu.gpu_type == req.gpu_type_preferred:
                gpu.status = "running"
                gpu.workload_id = req.workload_id
                gpu.utilization = random.uniform(60, 95)
                gpu.memory_used_gb = gpu.memory_total_gb * random.uniform(0.5, 0.9)
                gpu.power_draw_watts = GPU_SPECS[gpu.gpu_type]["tdp_watts"] * random.uniform(0.6, 0.95)
                gpu.temperature_c = random.uniform(55, 82)
                assigned.append({"node_id": node_id, "gpu_id": gpu.gpu_id})
                if len(assigned) >= req.gpu_count:
                    break
        if len(assigned) >= req.gpu_count:
            break

    # Fallback: assign any available GPU
    if len(assigned) < req.gpu_count:
        for node_id, gpus in cluster.items():
            for gpu in gpus:
                if gpu.status == "idle":
                    gpu.status = "running"
                    gpu.workload_id = req.workload_id
                    gpu.utilization = random.uniform(60, 95)
                    gpu.memory_used_gb = gpu.memory_total_gb * random.uniform(0.5, 0.9)
                    gpu.power_draw_watts = GPU_SPECS[gpu.gpu_type]["tdp_watts"] * random.uniform(0.6, 0.95)
                    gpu.temperature_c = random.uniform(55, 82)
                    assigned.append({"node_id": node_id, "gpu_id": gpu.gpu_id})
                    if len(assigned) >= req.gpu_count:
                        break
            if len(assigned) >= req.gpu_count:
                break

    if not assigned:
        return {"status": "queued", "message": "No GPUs available, workload queued"}

    workloads[req.workload_id] = {
        "workload_id": req.workload_id,
        "assigned_gpus": assigned,
        "start_time": time.time(),
        "duration_seconds": req.duration_seconds,
        "status": "running",
    }

    return {"status": "running", "assigned": assigned, "workload_id": req.workload_id}


@app.post("/workloads/{workload_id}/complete")
def complete_workload(workload_id: str):
    """Mark a workload as complete and free GPUs."""
    if workload_id not in workloads:
        return {"error": "Workload not found"}

    wl = workloads[workload_id]
    for assignment in wl["assigned_gpus"]:
        node_id = assignment["node_id"]
        gpu_id = assignment["gpu_id"]
        if node_id in cluster:
            gpu = cluster[node_id][gpu_id]
            gpu.status = "idle"
            gpu.workload_id = None
            gpu.utilization = random.uniform(0, 10)
            gpu.memory_used_gb = random.uniform(0.5, 2.0)
            gpu.power_draw_watts = random.uniform(20, 50)
            gpu.temperature_c = random.uniform(30, 45)

    wl["status"] = "completed"
    wl["end_time"] = time.time()
    return wl


@app.get("/workloads")
def list_workloads():
    """List all workloads."""
    return workloads


@app.post("/nodes/scale-up")
def scale_up(gpu_type: str = "T4", count: int = 1):
    """Add new nodes to cluster (simulates autoscaling)."""
    added = []
    for _ in range(count):
        node_id = f"node-{len(cluster):02d}"
        specs = GPU_SPECS.get(gpu_type, GPU_SPECS["T4"])
        cluster[node_id] = []
        for g in range(GPUS_PER_NODE):
            cluster[node_id].append(GPUState(
                node_id=node_id,
                gpu_id=g,
                gpu_type=gpu_type,
                utilization=0,
                memory_used_gb=0.5,
                memory_total_gb=specs["memory_gb"],
                power_draw_watts=20,
                temperature_c=30,
                status="idle",
            ))
        added.append(node_id)
    return {"added_nodes": added, "total_nodes": len(cluster)}


@app.post("/nodes/{node_id}/remove")
def remove_node(node_id: str):
    """Remove a node (scale down)."""
    if node_id in cluster:
        # Check if any GPU is running
        running = [g for g in cluster[node_id] if g.status == "running"]
        if running:
            return {"error": "Node has running workloads, cannot remove"}
        del cluster[node_id]
        return {"removed": node_id, "total_nodes": len(cluster)}
    return {"error": "Node not found"}
