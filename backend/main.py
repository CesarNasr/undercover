"""The UnderCover backend."""

from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI
from pydantic import JsonValue

from backend.runs import execute, progress, recover, start
from backend.store import database, get, initialize, listing, record
from backend.workflow import (
    Decision,
    Event,
    Payment,
    RunRequest,
    SignOff,
    decide,
    pay,
    sign_off,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize persistent business data."""
    initialize()
    recover()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def claims() -> list[JsonValue]:
    """List the claims queue."""
    with database() as db:
        queue = listing(db, "claims")
        for item in queue:
            if isinstance(item, dict):
                customer = record(db, "customers", str(item["customer_id"]))
                item["customer_name"] = customer["name"]
        return queue


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def claim(claim_id: str) -> JsonValue:
    """Read a full claim."""
    with database() as db:
        return get(db, "claims", claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def policy(policy_id: str) -> JsonValue:
    """Read a policy."""
    with database() as db:
        return get(db, "policies", policy_id)


@app.get("/api/customers/{customer_id}", operation_id="get_customer")
def customer(customer_id: str) -> JsonValue:
    """Read a customer and claim history."""
    with database() as db:
        return get(db, "customers", customer_id)


@app.get("/api/plans", operation_id="get_plans")
def plans() -> JsonValue:
    """Read plan limits and add-ons."""
    with database() as db:
        return get(db, "plans", "plans")


@app.get("/api/handlers", operation_id="list_handlers")
def handlers() -> list[JsonValue]:
    """List handlers eligible for sign-off."""
    with database() as db:
        return listing(db, "handlers")


@app.get("/api/policy-wording", operation_id="get_wording")
def wording() -> JsonValue:
    """Read the policy wording."""
    with database() as db:
        return get(db, "text", "wording")


@app.get("/api/instructions", operation_id="get_instructions")
def instructions() -> JsonValue:
    """Read the agent instructions."""
    with database() as db:
        return get(db, "text", "instructions")


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def decision(claim_id: str, body: Decision) -> dict[str, JsonValue]:
    """Record the agent's coverage decision."""
    return decide(claim_id, body)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def approval(claim_id: str, body: SignOff) -> dict[str, JsonValue]:
    """Record a handler's sign-off."""
    return sign_off(claim_id, body)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def payment(claim_id: str, body: Payment) -> dict[str, JsonValue]:
    """Request an exact simulated payment."""
    return pay(claim_id, body)


@app.post("/api/claims/{claim_id}/runs", operation_id="start_run", status_code=202)
def start_run(
    claim_id: str, body: RunRequest, tasks: BackgroundTasks
) -> dict[str, JsonValue]:
    """Start background processing of a waiting claim."""
    result = start(claim_id, body.thread_id)
    tasks.add_task(execute, claim_id, body.thread_id)
    return result


@app.get("/api/claims/{claim_id}/events", operation_id="get_events")
def events(claim_id: str) -> JsonValue:
    """Read operational progress for a claim."""
    with database() as db:
        return record(db, "claims", claim_id)["events"]


@app.post("/api/claims/{claim_id}/events", operation_id="record_event")
def add_event(claim_id: str, body: Event) -> dict[str, JsonValue]:
    """Record a tool activity event."""
    return progress(claim_id, body)
