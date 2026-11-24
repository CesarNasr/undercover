"""Run waiting claims sequentially through the backend's agent workflow."""

import argparse
import time
from decimal import Decimal
from uuid import uuid4

import httpx
from pydantic import BaseModel, TypeAdapter

from agent.main import backend

WAIT_SECONDS = 600


class Decision(BaseModel):
    """The saved decision printed by the command."""

    outcome: str
    payout: Decimal
    explanation: str
    calculation: str
    policy_references: list[str]


class Event(BaseModel):
    """A run activity message."""

    thread_id: str
    message: str


class Claim(BaseModel):
    """The API state needed by the command."""

    claim_id: str
    status: str
    thread_id: str
    decision: Decision | None
    events: list[Event]


def read_claim(client: httpx.Client, claim_id: str) -> Claim:
    """Read the current state of one claim."""
    response = client.get(f"/api/claims/{claim_id}")
    response.raise_for_status()
    return Claim.model_validate(response.json())


def process_claim(client: httpx.Client, claim: Claim) -> bool:
    """Start a claim, wait for completion and print its saved decision."""
    thread_id = str(uuid4())
    response = client.post(
        f"/api/claims/{claim.claim_id}/runs", json={"thread_id": thread_id}
    )
    response.raise_for_status()
    print(f"{claim.claim_id}: running", flush=True)
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        current = read_claim(client, claim.claim_id)
        completed = any(
            item.thread_id == thread_id
            and item.message.startswith(
                ("Run finished", "Run failed", "Run interrupted")
            )
            for item in current.events
        )
        if completed:
            return print_result(current)
        time.sleep(1)
    print(f"{claim.claim_id}: timed out waiting; check dashboard activity.", flush=True)
    return False


def print_result(claim: Claim) -> bool:
    """Print a decision or identify a run that did not produce one."""
    decision = claim.decision
    if decision is None:
        print(f"{claim.claim_id}: no decision; check dashboard activity.", flush=True)
        return False
    print(
        f"{claim.claim_id}: {decision.outcome} | ${decision.payout:,.2f} "
        f"| {claim.status.replace('_', ' ')}\n"
        f"{decision.explanation}\n"
        f"Calculation: {decision.calculation}\n"
        f"Policy sections: {', '.join(decision.policy_references)}\n",
        flush=True,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    """Process one claim or the waiting queue using the configured real model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "claim_id", nargs="?", help="Claim ID; omit for all waiting claims"
    )
    args = parser.parse_args(argv)
    try:
        with backend() as client:
            if args.claim_id:
                queue = [read_claim(client, args.claim_id)]
            else:
                response = client.get("/api/claims")
                response.raise_for_status()
                queue = TypeAdapter(list[Claim]).validate_python(response.json())
            waiting = [claim for claim in queue if claim.status == "waiting"]
            print(f"{len(waiting)} waiting claim(s).", flush=True)
            decided = 0
            for claim in waiting:
                if process_claim(client, claim):
                    decided += 1
                else:
                    print(
                        "Stopping after an incomplete run; "
                        "check activity before retrying."
                    )
                    break
            print(
                f"Decisions: {decided}/{len(waiting)}; "
                f"skipped: {len(queue) - len(waiting)}."
            )
            return int(decided != len(waiting))
    except httpx.HTTPStatusError as exc:
        print(
            f"Backend returned HTTP {exc.response.status_code}; "
            "check the claim ID and state."
        )
        return 1
    except httpx.RequestError:
        print("Cannot reach the backend. Start npm run dev and check BACKEND_URL.")
        return 1
