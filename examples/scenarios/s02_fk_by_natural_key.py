"""2. FK by natural key: lookup= and error=."""

from __future__ import annotations

from _support import client
from trading.models import Customer, Order, Ticker

URL = "/orders/batch/"


def seed() -> None:
    Ticker.objects.create(isin="1101", name="Alpha Corp")
    Ticker.objects.create(isin="1102", name="Beta Corp")
    Customer.objects.create(isin="CUST-1", name="Acme Trading")


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    response = api.post(
        URL,
        [
            {
                "ticker": "1101",
                "customer": "CUST-1",
                "volume": 10,
                "reference_id": "R1",
            },
            # A number is coerced to the isin column's type (a string).
            {"ticker": 1102, "customer": "CUST-1", "volume": 5, "reference_id": "R2"},
        ],
    )
    assert response.status_code == 201
    assert Order.objects.get(reference_id="R2").ticker.isin == "1102"
    # --8<-- [end:post]

    # --8<-- [start:miss]
    response = api.post(
        URL,
        [{"ticker": "9999", "customer": "CUST-404", "volume": 1, "reference_id": "R3"}],
    )
    assert response.status_code == 400
    assert response.json() == [
        {
            "ticker": ["Ticker '9999' not found."],
            "customer": ["Customer 'CUST-404' not found."],
        }
    ]
    # --8<-- [end:miss]

    # --8<-- [start:malformed]
    response = api.post(
        URL,
        [{"ticker": ["1101"], "customer": "CUST-1", "volume": 1, "reference_id": "R4"}],
    )
    assert response.status_code == 400
    assert response.json() == [
        {"ticker": ["Invalid value for 'ticker': expected a string, got list."]}
    ]
    # --8<-- [end:malformed]
