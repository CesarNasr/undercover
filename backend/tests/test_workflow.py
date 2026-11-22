from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.store import database, record, save


def active():
    with database() as db:
        claim = record(db, "claims", "CLM-1001")
        claim.update(status="in_progress", thread_id="test")
        save(db, claim)


def payload(amount="1250", outcome="approve"):
    return dict(
        outcome=outcome,
        payout=amount,
        calculation="Eligible cost",
        explanation="Covered delay. Section 3 applies.",
        policy_references=["3"],
        thread_id="test",
    )


BASE = "/api/claims/CLM-1001"


@pytest.mark.parametrize("amount", ["1000", "1000.01", "1250"])
def test_payment_barrier(client, amount):
    active()
    assert client.post(BASE + "/payment", json={"amount": amount}).status_code == 409
    assert client.post(BASE + "/decision", json=payload(amount)).status_code == 200
    assert client.post(BASE + "/decision", json=payload(amount)).status_code == 409
    for invalid in ("1", "99999"):
        assert (
            client.post(BASE + "/payment", json={"amount": invalid}).status_code == 409
        )
    if amount != "1000":
        assert (
            client.post(BASE + "/payment", json={"amount": amount}).status_code == 409
        )
        assert (
            client.post(BASE + "/sign-off", json={"handler_id": "missing"}).status_code
            == 404
        )
        assert (
            client.post(BASE + "/sign-off", json={"handler_id": "HND-01"}).status_code
            == 200
        )
    assert (
        client.post(BASE + "/sign-off", json={"handler_id": "HND-01"}).status_code
        == 409
    )
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda _: (
                    client.post(BASE + "/payment", json={"amount": amount}).status_code
                ),
                range(2),
            )
        )
    assert sorted(results) == [200, 409]
    assert client.get(BASE).json()["payment"]["simulated"]


@pytest.mark.parametrize("outcome", ["decline", "refer"])
def test_non_payment(client, outcome):
    active()
    assert (
        client.post(BASE + "/decision", json=payload("5", outcome)).status_code == 422
    )
    assert (
        client.post(BASE + "/decision", json=payload("0", outcome)).status_code == 200
    )
    assert client.post(BASE + "/payment", json={"amount": "0"}).status_code == 409
    assert client.post(BASE + "/payment", json={"amount": "-1"}).status_code == 422
