import json
from contextlib import nullcontext

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from agent import cli
from agent import main as agent_main
from agent.tests.test_agent import StubModel
from backend import runs
from backend.main import app


def state(key, status="waiting", decision=None, events=None, thread_id=""):
    return dict(
        claim_id=key,
        status=status,
        decision=decision,
        events=events or [],
        thread_id=thread_id,
    )


DECISION = dict(
    outcome="approve",
    payout="1250",
    explanation="Covered. Policy section 3 applies.",
    calculation="Eligible costs",
    policy_references=["3"],
)


def test_queue_order_and_output(monkeypatch, capsys):
    started = []
    threads = {}
    polls = {}

    def handler(request):
        if request.url.path == "/api/claims":
            return httpx.Response(
                200,
                json=[
                    state("CLM-1002"),
                    state("CLM-1001"),
                    state("CLM-1003", "decided", DECISION),
                ],
            )
        key = request.url.path.split("/")[3]
        if request.method == "POST":
            started.append(key)
            threads[key] = json.loads(request.content)["thread_id"]
            return httpx.Response(202, json={})
        polls[key] = polls.get(key, 0) + 1
        events = (
            []
            if polls[key] == 1
            else [dict(thread_id=threads[key], message="Run finished")]
        )
        return httpx.Response(
            200, json=state(key, "waiting_for_sign_off", DECISION, events, threads[key])
        )

    monkeypatch.setattr(
        cli,
        "backend",
        lambda: httpx.Client(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ),
    )
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    assert cli.main([]) == 0
    assert started == ["CLM-1002", "CLM-1001"]
    output = capsys.readouterr().out
    assert "$1,250.00" in output
    assert "Policy sections: 3" in output
    assert "Decisions: 2/2; skipped: 1" in output


def test_single_claim_failure(monkeypatch, capsys):

    thread = ""

    def handler(request):
        nonlocal thread
        if request.method == "POST":
            thread = json.loads(request.content)["thread_id"]
        events = (
            [dict(thread_id=thread, message="Run failed (APIStatusError)")]
            if thread
            else []
        )
        return httpx.Response(
            200, json=state("CLM-1001", events=events, thread_id=thread)
        )

    monkeypatch.setattr(
        cli,
        "backend",
        lambda: httpx.Client(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ),
    )
    assert cli.main(["CLM-1001"]) == 1
    assert "no decision" in capsys.readouterr().out


@pytest.mark.parametrize("status", ["decided", "waiting_for_sign_off", "in_progress"])
def test_skip_existing_claim(monkeypatch, capsys, status):
    def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json=state("CLM-1001", status))

    monkeypatch.setattr(
        cli,
        "backend",
        lambda: httpx.Client(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ),
    )
    assert cli.main(["CLM-1001"]) == 0
    assert "Decisions: 0/0; skipped: 1" in capsys.readouterr().out


def test_timeout(monkeypatch, capsys):
    def handler(_request):
        return httpx.Response(200, json=state("CLM-1001"))

    monkeypatch.setattr(
        cli,
        "backend",
        lambda: httpx.Client(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ),
    )
    monkeypatch.setattr(cli, "WAIT_SECONDS", 0)
    assert cli.main(["CLM-1001"]) == 1
    assert "timed out" in capsys.readouterr().out


@pytest.mark.parametrize("status", [404, 409])
def test_http_error(monkeypatch, capsys, status):
    monkeypatch.setattr(
        cli,
        "backend",
        lambda: httpx.Client(
            base_url="http://test",
            transport=httpx.MockTransport(lambda _: httpx.Response(status)),
        ),
    )
    assert cli.main(["CLM-001"]) == 1
    assert f"HTTP {status}" in capsys.readouterr().out


def test_backend_offline(monkeypatch, capsys):
    def handler(_request):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(
        cli,
        "backend",
        lambda: httpx.Client(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ),
    )
    assert cli.main([]) == 1
    assert "Cannot reach the backend" in capsys.readouterr().out


def test_cli_uses_backend_agent_and_preserves_signoff(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "cli.sqlite3"))
    replies = [
        AIMessage(content="", tool_calls=[dict(name="read_context", args={}, id="1")]),
        AIMessage(
            content="", tool_calls=[dict(name="record_decision", args=DECISION, id="2")]
        ),
        AIMessage(
            content="",
            tool_calls=[dict(name="request_payment", args={"amount": "1250"}, id="3")],
        ),
        AIMessage(content="Waiting for sign-off"),
    ]
    with TestClient(app) as client:
        monkeypatch.setattr(cli, "backend", lambda: nullcontext(client))
        monkeypatch.setattr(agent_main, "backend", lambda: nullcontext(client))
        monkeypatch.setattr(
            runs,
            "run",
            lambda claim_id, thread_id: agent_main.run(
                claim_id, thread_id, StubModel(messages=iter(replies))
            ),
        )
        assert cli.main(["CLM-1001"]) == 0
        saved = client.get("/api/claims/CLM-1001").json()
        assert saved["status"] == "waiting_for_sign_off"
        assert saved["payment"] is None
    output = capsys.readouterr().out
    assert "approve | $1,250.00 | waiting for sign off" in output
    assert "Decisions: 1/1; skipped: 0" in output
