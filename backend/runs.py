"""Background pilot runs and operational progress."""

from pydantic import JsonValue

from agent.main import run
from backend.store import database, listing, record, save
from backend.workflow import Event, event, require


def start(claim_id: str, thread_id: str) -> dict[str, JsonValue]:
    """Reserve a waiting claim before background execution."""
    with database() as db:
        claim = record(db, "claims", claim_id)
        require(claim["status"] == "waiting", "Claim is not waiting")
        claim.update(status="in_progress", thread_id=thread_id)
        event(claim, "Run started")
        save(db, claim)
        return claim


def progress(claim_id: str, body: Event) -> dict[str, JsonValue]:
    """Record progress for the current run."""
    with database() as db:
        claim = record(db, "claims", claim_id)
        require(claim["thread_id"] == body.thread_id, "Wrong run")
        event(claim, body.message)
        save(db, claim)
        return claim


def finish(claim_id: str, message: str) -> None:
    """Preserve decisions while releasing an unfinished claim."""
    with database() as db:
        claim = record(db, "claims", claim_id)
        if claim["decision"] is None:
            claim["status"] = "waiting"
        elif claim["status"] == "in_progress":
            claim["status"] = "decided"
        event(claim, message)
        save(db, claim)


def execute(claim_id: str, thread_id: str) -> None:
    """Run the agent and record failures without inventing decisions."""
    try:
        run(claim_id, thread_id)
    except Exception as exc:
        finish(
            claim_id, f"Run failed ({type(exc).__name__}). Retry the available action."
        )
    else:
        finish(claim_id, "Run finished")


def recover() -> None:
    """Release interrupted local runs on backend restart."""
    with database() as db:
        for value in listing(db, "claims"):
            if isinstance(value, dict) and value["status"] == "in_progress":
                value["status"] = "waiting" if value["decision"] is None else "decided"
                event(value, "Run interrupted by backend restart")
                save(db, value)
