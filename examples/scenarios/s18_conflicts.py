"""18. Cross-row conflicts: model constraints and batch_unique_together."""

from __future__ import annotations

from _support import client
from trading.models import Customer, Order, Ticker

URL = "/unique-orders/batch/"


def seed() -> None:
    alpha = Ticker.objects.create(isin="1101", name="Alpha Corp")
    Ticker.objects.create(isin="1102", name="Beta Corp")
    Ticker.objects.create(isin="1103", name="Gamma Corp")
    acme = Customer.objects.create(isin="CUST-1", name="Acme Trading")
    Customer.objects.create(isin="CUST-2", name="Bolt Capital")
    Order.objects.create(
        id=1, ticker=alpha, customer=acme, volume=1, reference_id="REF-1"
    )


def walk() -> None:
    api = client()

    # --8<-- [start:in_batch]
    response = api.post(
        URL,
        [
            {
                "ticker": "1102",
                "customer": "CUST-1",
                "volume": 1,
                "reference_id": "DUP",
            },
            {
                "ticker": "1103",
                "customer": "CUST-1",
                "volume": 1,
                "reference_id": "DUP",
            },
        ],
    )
    assert response.status_code == 409
    assert response.json() == [
        {"reference_id": ["Conflicts with another row in this batch."]},
        {"reference_id": ["Conflicts with another row in this batch."]},
    ]
    # --8<-- [end:in_batch]

    # --8<-- [start:existing]
    response = api.post(
        URL,
        [
            # The model's UniqueConstraint(ticker, customer), against order 1:
            {"ticker": "1101", "customer": "CUST-1", "volume": 1, "reference_id": "N1"},
            # batch_unique_together = ("reference_id",), against order 1:
            {
                "ticker": "1102",
                "customer": "CUST-2",
                "volume": 1,
                "reference_id": "REF-1",
            },
        ],
    )
    assert response.status_code == 409
    assert response.json() == [
        {
            "ticker": ["Conflicts with an existing record."],
            "customer": ["Conflicts with an existing record."],
        },
        {"reference_id": ["Conflicts with an existing record."]},
    ]
    # --8<-- [end:existing]

    # --8<-- [start:update]
    # An update may keep its own values: a row never conflicts with itself.
    response = api.patch(URL, [{"id": 1, "reference_id": "REF-1", "volume": 2}])
    assert response.status_code == 200
    # --8<-- [end:update]
