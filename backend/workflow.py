"""Transactional claim decisions and payments."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, Self

from fastapi import HTTPException
from pydantic import BaseModel, Field, JsonValue, model_validator

from backend.store import database, record, save

Money = Decimal


class Payment(BaseModel):
    """An exact USD payment request."""

    amount: Decimal = Field(ge=0, decimal_places=2, max_digits=12)


class Decision(BaseModel):
    """A policy-based coverage decision."""

    outcome: Literal["approve", "decline", "refer"]
    payout: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    calculation: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    policy_references: list[str] = Field(min_length=1)
    thread_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_payout(self) -> Self:
        """Reject payments for non-approved outcomes."""
        if self.outcome != "approve" and self.payout != 0:
            raise ValueError("Only approvals have a payout")
        return self


class SignOff(BaseModel):
    """Handler attribution for an approval."""

    handler_id: str


class RunRequest(BaseModel):
    """A caller-assigned run identifier."""

    thread_id: str = Field(min_length=1)


class Event(BaseModel):
    """An operational progress message."""

    thread_id: str
    message: str = Field(min_length=1)


def require(condition: bool, message: str) -> None:
    """Reject a conflicting workflow action."""
    if not condition:
        raise HTTPException(409, message)


def now() -> str:
    """Return a UTC timestamp."""
    return datetime.now(UTC).isoformat()


def event(claim: dict[str, JsonValue], message: str) -> None:
    """Append a progress event to a claim."""
    events = claim["events"]
    if isinstance(events, list):
        events.append(
            {"timestamp": now(), "thread_id": claim["thread_id"], "message": message}
        )


def decide(claim_id: str, body: Decision) -> dict[str, JsonValue]:
    """Store a decision for the active claim run."""
    with database() as db:
        claim = record(db, "claims", claim_id)
        require(
            claim["status"] == "in_progress" and claim["decision"] is None,
            "Claim is not awaiting a decision",
        )
        require(claim["thread_id"] == body.thread_id, "Wrong run")
        claim["decision"] = body.model_dump(mode="json")
        company = record(db, "company", "company")
        over_limit = body.payout > Decimal(str(company["payout_approval_limit"]))
        claim["status"] = "waiting_for_sign_off" if over_limit else "decided"
        event(claim, f"Decision recorded: {body.outcome}")
        save(db, claim)
        return claim


def sign_off(claim_id: str, body: SignOff) -> dict[str, JsonValue]:
    """Sign off the stored over-limit approval."""
    with database() as db:
        claim = record(db, "claims", claim_id)
        handler = record(db, "handlers", body.handler_id)
        require(
            claim["status"] == "waiting_for_sign_off" and claim["sign_off"] is None,
            "Sign-off not available",
        )
        require(handler["can_approve_over_limit"] is True, "Handler cannot sign off")
        claim["sign_off"] = {"handler_id": body.handler_id, "timestamp": now()}
        event(claim, "Handler sign-off recorded")
        save(db, claim)
        return claim


def pay(claim_id: str, body: Payment) -> dict[str, JsonValue]:
    """Record one simulated payment after enforcing the approval limit."""
    with database() as db:
        claim = record(db, "claims", claim_id)
        decision = claim["decision"]
        require(isinstance(decision, dict), "No approved decision")
        if not isinstance(decision, dict):
            raise HTTPException(409, "No decision")
        require(decision["outcome"] == "approve", "Claim is not approved")
        require(
            body.amount == Decimal(str(decision["payout"])),
            "Amount must equal the full approved payout",
        )
        require(claim["payment"] is None, "Already paid")
        company = record(db, "company", "company")
        require(
            body.amount <= Decimal(str(company["payout_approval_limit"]))
            or claim["sign_off"] is not None,
            "Handler sign-off required",
        )
        claim["payment"] = {
            "amount": str(body.amount),
            "timestamp": now(),
            "simulated": True,
        }
        claim["status"] = "decided"
        event(claim, "Simulated payment recorded")
        save(db, claim)
        return claim
