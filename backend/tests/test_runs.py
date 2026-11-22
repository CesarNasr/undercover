from backend import runs
from backend.store import initialize


def test_runs(client, monkeypatch):
    monkeypatch.setattr(runs, "run", lambda *_: None)
    base = "/api/claims/CLM-1001"
    assert client.post(base + "/runs", json={"thread_id": "one"}).status_code == 202
    assert client.get(base).json()["status"] == "waiting"
    runs.start("CLM-1001", "two")
    assert client.post(base + "/runs", json={"thread_id": "three"}).status_code == 409
    assert (
        client.post(
            base + "/events", json={"thread_id": "bad", "message": "test"}
        ).status_code
        == 409
    )
    runs.recover()
    assert client.get(base).json()["status"] == "waiting"
    initialize()
    runs.start("CLM-1001", "four")

    def fail(*_):
        raise RuntimeError("test")

    monkeypatch.setattr(runs, "run", fail)
    runs.execute("CLM-1001", "four")
    assert "failed" in client.get(base + "/events").json()[-1]["message"]
