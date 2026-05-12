"""API Gateway - Single entry point for Kaggle/Colab notebooks to interact with the lab."""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="GPU FinOps Lab Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GPU_NODE_URL = os.getenv("GPU_NODE_URL", "http://gpu-node-manager:8000")
BILLING_URL = os.getenv("BILLING_URL", "http://billing-api:8000")
SPOT_URL = os.getenv("SPOT_URL", "http://spot-manager:8000")
AUTOSCALER_URL = os.getenv("AUTOSCALER_URL", "http://autoscaler:8000")
COST_TRACKER_URL = os.getenv("COST_TRACKER_URL", "http://cost-tracker:8000")


@app.get("/")
def root():
    return {
        "service": "GPU FinOps Lab Gateway",
        "endpoints": {
            "cluster": "/cluster/*",
            "billing": "/billing/*",
            "spot": "/spot/*",
            "autoscaler": "/autoscaler/*",
            "cost": "/cost/*",
        },
    }


# --- Cluster/GPU Node endpoints ---
@app.get("/cluster/nodes")
async def cluster_nodes():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{GPU_NODE_URL}/nodes")
        return r.json()


@app.get("/cluster/metrics")
async def cluster_metrics():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{GPU_NODE_URL}/metrics")
        return r.json()


@app.post("/cluster/workloads/submit")
async def submit_workload(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GPU_NODE_URL}/workloads/submit", json=body)
        return r.json()


@app.post("/cluster/workloads/{workload_id}/complete")
async def complete_workload(workload_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GPU_NODE_URL}/workloads/{workload_id}/complete")
        return r.json()


@app.get("/cluster/workloads")
async def list_workloads():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{GPU_NODE_URL}/workloads")
        return r.json()


@app.post("/cluster/scale-up")
async def scale_up(gpu_type: str = "T4", count: int = 1):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GPU_NODE_URL}/nodes/scale-up", params={"gpu_type": gpu_type, "count": count})
        return r.json()


# --- Billing endpoints ---
@app.get("/billing/pricing")
async def billing_pricing():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BILLING_URL}/pricing")
        return r.json()


@app.post("/billing/record")
async def billing_record(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BILLING_URL}/record", json=body)
        return r.json()


@app.get("/billing/summary")
async def billing_summary(project: str = "default"):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BILLING_URL}/summary", params={"project": project})
        return r.json()


@app.get("/billing/forecast")
async def billing_forecast(project: str = "default", hours_ahead: int = 24):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BILLING_URL}/forecast", params={"project": project, "hours_ahead": hours_ahead})
        return r.json()


@app.post("/billing/budget")
async def set_budget(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BILLING_URL}/budget", json=body)
        return r.json()


# --- Spot Instance endpoints ---
@app.get("/spot/pricing")
async def spot_pricing():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SPOT_URL}/spot/pricing")
        return r.json()


@app.post("/spot/request")
async def spot_request(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SPOT_URL}/spot/request", json=body)
        return r.json()


@app.get("/spot/instances")
async def spot_instances():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SPOT_URL}/spot/instances")
        return r.json()


@app.post("/spot/simulate-preemption")
async def simulate_preemption():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SPOT_URL}/spot/simulate-preemption")
        return r.json()


@app.get("/spot/savings-report")
async def spot_savings():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SPOT_URL}/spot/savings-report")
        return r.json()


# --- Autoscaler endpoints ---
@app.get("/autoscaler/policy")
async def autoscaler_policy():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{AUTOSCALER_URL}/policy")
        return r.json()


@app.post("/autoscaler/policy")
async def update_autoscaler_policy(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AUTOSCALER_URL}/policy", json=body)
        return r.json()


@app.post("/autoscaler/evaluate")
async def autoscaler_evaluate():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AUTOSCALER_URL}/evaluate")
        return r.json()


@app.get("/autoscaler/history")
async def autoscaler_history():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{AUTOSCALER_URL}/history")
        return r.json()


# --- Cost Tracker (OpenCost-like) endpoints ---
@app.post("/cost/snapshot")
async def cost_snapshot():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{COST_TRACKER_URL}/snapshot")
        return r.json()


@app.get("/cost/allocations")
async def cost_allocations(last_n: int = 20):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{COST_TRACKER_URL}/allocations", params={"last_n": last_n})
        return r.json()


@app.get("/cost/waste-report")
async def cost_waste():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{COST_TRACKER_URL}/waste-report")
        return r.json()


@app.post("/cost/recommendations")
async def cost_recommendations():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{COST_TRACKER_URL}/recommendations")
        return r.json()


@app.get("/cost/dashboard")
async def cost_dashboard():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{COST_TRACKER_URL}/dashboard")
        return r.json()
