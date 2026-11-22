from backend.store import database, get, initialize


def test_records(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    for claim in claims:
        assert claim["status"] == "waiting"
        assert client.get(f"/api/policies/{claim['policy_id']}").status_code == 200
        assert client.get(f"/api/customers/{claim['customer_id']}").status_code == 200
    for route in (
        "claims/CLM-1001",
        "plans",
        "handlers",
        "policy-wording",
        "instructions",
    ):
        assert client.get(f"/api/{route}").status_code == 200
    assert client.get("/api/claims/missing").status_code == 404
    initialize()
    assert len(client.get("/api/claims").json()) == 25
    with database() as db:
        assert get(db, "company", "company")
    schema = client.get("/openapi.json").json()
    operations = [op for path in schema["paths"].values() for op in path.values()]
    assert len({op["operationId"] for op in operations}) == len(operations)
    assert all(p["required"] for op in operations for p in op.get("parameters", []))
