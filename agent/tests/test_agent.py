from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main
from backend.main import app
from backend.runs import start
from backend.store import initialize


class StubModel(GenericFakeChatModel):
    """Scripted model with tool support."""

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.parametrize(
    ("outcome", "amount"),
    [("approve", "420"), ("approve", "1250"), ("decline", "0"), ("refer", "0")],
)
def test_run(tmp_path, monkeypatch, outcome, amount):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "agent.sqlite3"))
    initialize()
    start("CLM-1001", "thread-1")
    monkeypatch.setattr(main, "backend", lambda: nullcontext(TestClient(app)))
    calls = [
        ("read_context", {}),
        (
            "record_decision",
            dict(
                outcome=outcome,
                payout=amount,
                calculation="Eligible expenses",
                explanation="Policy section 3 applies. Evidence checked.",
                policy_references=["3"],
            ),
        ),
    ]
    if outcome == "approve":
        calls.append(("request_payment", {"amount": amount}))
    replies = [
        AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": str(i)}])
        for i, (name, args) in enumerate(calls)
    ]
    replies.append(AIMessage(content="Complete"))
    assert (
        main.run("CLM-1001", "thread-1", StubModel(messages=iter(replies)))
        == "Complete"
    )
    claim = TestClient(app).get("/api/claims/CLM-1001").json()
    assert claim["decision"]["outcome"] == outcome
    assert bool(claim["payment"]) == (outcome == "approve" and amount == "420")
    assert len(claim["events"]) >= 3


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
