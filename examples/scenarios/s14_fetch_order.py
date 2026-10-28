"""14. Fetch order with depends_on: service-after-DB and DB-after-service."""

from __future__ import annotations

from _support import client
from trading import services
from trading.models import Customer, Ticker

ROWS = [
    {"ticker": "1101", "customer": "CUST-1", "volume": 5, "reference_id": "X1"},
    {"ticker": "1104", "customer": "CUST-1", "volume": 5, "reference_id": "X2"},
    {"ticker": "1101", "customer": "CUST-2", "volume": 5, "reference_id": "X3"},
]


def seed() -> None:
    Ticker.objects.create(isin="1101", name="Alpha Corp")  # band A
    Ticker.objects.create(isin="1104", name="Delta Corp")  # band A
    Customer.objects.create(isin="CUST-1", name="Acme Trading")  # verified
    Customer.objects.create(isin="CUST-2", name="Bolt Capital")  # pending


def before(calls: list[str], first: str, second: str) -> bool:
    return calls.index(first) < calls.index(second)


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    services.CALLS.clear()
    response = api.post("/exchange-orders/batch/", ROWS)
    assert response.status_code == 400
    assert response.json() == [
        {},
        {},
        {"customer": ["Customer is not KYC-verified."]},
    ]
    # band waits for the tickers; primary_listing waits for band.
    assert before(services.CALLS, "band", "primary_listing")
    # --8<-- [end:post]

    # --8<-- [start:sequential]
    services.CALLS.clear()
    response = api.post("/exchange-orders-sequential/batch/", ROWS[:2])
    assert response.status_code == 201
    # One at a time, in plan order (dependencies first, then declaration).
    assert services.CALLS == ["band", "kyc", "primary_listing"]
    # --8<-- [end:sequential]
