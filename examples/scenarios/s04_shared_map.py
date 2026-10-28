"""4. Two fields, one map: map=."""

from __future__ import annotations

from _support import client, queries, reads
from ledger.models import Currency, Transfer

URL = "/transfers/batch/"


def seed() -> None:
    for code, name in [("EUR", "Euro"), ("USD", "US dollar"), ("GBP", "Pound")]:
        Currency.objects.create(code=code, name=name)


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    with queries() as captured:
        response = api.post(
            URL,
            [
                {"from_currency": "EUR", "to_currency": "USD", "amount": "100.00"},
                {"from_currency": "USD", "to_currency": "GBP", "amount": "50.00"},
            ],
        )
    assert response.status_code == 201
    # EUR, USD and GBP from both fields: one query.
    assert reads(captured, "ledger_currency") == 1
    # --8<-- [end:post]

    # --8<-- [start:invalid]
    response = api.post(
        URL,
        [
            {"from_currency": "EUR", "to_currency": "EUR", "amount": "1.00"},
            {"from_currency": "EUR", "to_currency": "XXX", "amount": "1.00"},
        ],
    )
    assert response.status_code == 400
    assert response.json() == [
        {"non_field_errors": ["A transfer needs two currencies."]},
        {"to_currency": ["Unknown currency 'XXX'."]},
    ]
    # --8<-- [end:invalid]

    # --8<-- [start:patch]
    transfer = Transfer.objects.get(amount="100.00")  # EUR -> USD
    response = api.patch(URL, [{"id": transfer.pk, "to_currency": "EUR"}])
    assert response.status_code == 400  # the stored from_currency is EUR too
    # --8<-- [end:patch]
