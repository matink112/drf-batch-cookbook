"""9. A read-only field derived from one field: checks on POST and PATCH."""

from __future__ import annotations

from _support import client
from trading.models import Customer, Order, Ticker

URL = "/listed-orders/batch/"


def seed() -> None:
    alpha = Ticker.objects.create(isin="1101", name="Alpha Corp")  # band A
    beta = Ticker.objects.create(isin="1102", name="Beta Corp")  # band B
    Ticker.objects.create(isin="1103", name="Gamma Corp")  # not listed
    acme = Customer.objects.create(isin="CUST-1", name="Acme Trading")
    Order.objects.create(
        id=1, ticker=alpha, customer=acme, volume=10, reference_id="OLD-1"
    )
    Order.objects.create(
        id=2, ticker=beta, customer=acme, volume=10, reference_id="OLD-2"
    )


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    response = api.post(
        URL,
        [
            {"ticker": "1103", "customer": "CUST-1", "volume": 1, "reference_id": "N1"},
            {"ticker": "1102", "customer": "CUST-1", "volume": 1, "reference_id": "N2"},
        ],
    )
    assert response.status_code == 400
    assert response.json() == [
        {"ticker": ["Ticker is not listed."]},
        {"ticker": ["Ticker is suspended."]},
    ]
    # --8<-- [end:post]

    # --8<-- [start:patch]
    # Neither row sends a ticker: band is keyed by the stored one.
    response = api.patch(URL, [{"id": 1, "volume": 20}, {"id": 2, "volume": 20}])
    assert response.status_code == 400
    assert response.json() == [{}, {"ticker": ["Ticker is suspended."]}]
    # --8<-- [end:patch]

    # --8<-- [start:body_ignored]
    # band is read-only: claiming band "A" in the row changes nothing.
    response = api.patch(URL, [{"id": 2, "volume": 20, "band": "A"}])
    assert response.status_code == 400
    # --8<-- [end:body_ignored]

    response = api.patch(URL, [{"id": 1, "volume": 20}])
    assert response.status_code == 200
