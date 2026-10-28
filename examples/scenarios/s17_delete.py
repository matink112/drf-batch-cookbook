"""17. DELETE: scoping (404), object permissions (403), duplicates, PROTECT."""

from __future__ import annotations

from _support import client, user
from trading.models import Customer, Order, OrderNote, Ticker

URL = "/my-orders/batch/"


def seed() -> None:
    alice, bob = user("alice"), user("bob")
    tickers = [Ticker.objects.create(isin=f"110{i}", name=f"T{i}") for i in range(1, 5)]
    acme = Customer.objects.create(isin="CUST-1", name="Acme Trading")

    def order(pk: int, ticker: Ticker, volume: int, owner: object) -> Order:
        return Order.objects.create(
            id=pk,
            ticker=ticker,
            customer=acme,
            volume=volume,
            reference_id=f"O{pk}",
            owner=owner,
        )

    order(1, tickers[0], 10, alice)
    order(2, tickers[1], 5000, alice)  # large: needs a manager
    order(3, tickers[2], 10, bob)
    noted = order(4, tickers[3], 10, alice)
    OrderNote.objects.create(order=noted, text="Keep for the audit.")


def walk() -> None:
    api = client("alice")

    # --8<-- [start:not_found]
    response = api.delete(URL, [1, 3, 999])
    assert response.status_code == 404  # 3 is Bob's: outside get_queryset()
    assert response.json() == [
        {},
        {"id": ["Object with id '3' not found."]},
        {"id": ["Object with id '999' not found."]},
    ]
    # --8<-- [end:not_found]

    # --8<-- [start:forbidden]
    response = api.delete(URL, [1, 2])
    assert response.status_code == 403
    assert response.json() == [
        {},
        {"non_field_errors": ["Orders of 1000 or more need a manager."]},
    ]
    # --8<-- [end:forbidden]

    # --8<-- [start:duplicate]
    response = api.delete(URL, [1, 1])
    assert response.status_code == 409
    assert response.json() == [
        {"id": ["Conflicts with another row in this batch."]},
        {"id": ["Conflicts with another row in this batch."]},
    ]
    # --8<-- [end:duplicate]

    # --8<-- [start:protected]
    response = api.delete(URL, [1, 4])  # 4 has a PROTECT-ed note
    assert response.status_code == 409
    assert response.json() == {
        "detail": "The batch violates a database constraint; nothing was written."
    }
    assert Order.objects.filter(id=1).exists()  # all-or-none: nothing deleted
    # --8<-- [end:protected]

    # --8<-- [start:ok]
    response = api.delete(URL, [1])
    assert response.status_code == 200
    assert response.json() == {"count": 1}
    # --8<-- [end:ok]
