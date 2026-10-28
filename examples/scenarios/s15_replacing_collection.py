"""15. Replacing collection: one BatchCollector answers every map."""

from __future__ import annotations

from _support import client
from ledger import services
from ledger.models import Currency, Transfer

URL = "/treasury-transfers/batch/"


def seed() -> None:
    eur = Currency.objects.create(code="EUR", name="Euro")
    usd = Currency.objects.create(code="USD", name="US dollar")
    Currency.objects.create(code="JPY", name="Yen")
    Transfer.objects.create(id=1, from_currency=usd, to_currency=eur, amount="10.00")


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    services.TREASURY_CALLS.clear()
    response = api.post(
        URL,
        [
            {"from_currency": "EUR", "to_currency": "USD", "amount": "100.00"},
            {"from_currency": "EUR", "to_currency": "JPY", "amount": "100.00"},
        ],
    )
    assert response.status_code == 400
    assert response.json() == [
        {},
        {"non_field_errors": ["The treasury does not quote this pair."]},
    ]
    # One call for the whole batch, with the derived (from, to) keys.
    assert [
        {
            "currencies": {"EUR", "USD", "JPY"},
            "pairs": {("EUR", "USD"), ("EUR", "JPY")},
        }
    ] == services.TREASURY_CALLS
    # --8<-- [end:post]

    # --8<-- [start:patch]
    services.TREASURY_CALLS.clear()
    response = api.patch(URL, [{"id": 1, "amount": "12.00"}])
    assert response.status_code == 200
    # The stored pair reached the collector too.
    assert services.TREASURY_CALLS[0]["pairs"] == {("USD", "EUR")}
    # --8<-- [end:patch]
