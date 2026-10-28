"""11. A key built by a callable: key=."""

from __future__ import annotations

from _support import client
from ledger.models import Expense

URL = "/expenses/batch/"


def seed() -> None:
    # September 2026 is closed in the accounting system; October is open.
    Expense.objects.create(
        id=1, booked_on="2026-09-28", amount="80.00", category="travel"
    )
    Expense.objects.create(
        id=2, booked_on="2026-10-02", amount="12.50", category="food"
    )


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    response = api.post(
        URL,
        [
            {"booked_on": "2026-10-03", "amount": "45.00", "category": "travel"},
            {"booked_on": "2026-09-30", "amount": "45.00", "category": "travel"},
        ],
    )
    assert response.status_code == 400
    assert response.json() == [
        {},
        {"booked_on": ["The books for this month are closed."]},
    ]
    # --8<-- [end:post]

    # --8<-- [start:patch]
    # The amount only: the period comes from the stored booked_on.
    response = api.patch(
        URL, [{"id": 1, "amount": "90.00"}, {"id": 2, "amount": "15.00"}]
    )
    assert response.status_code == 400
    assert response.json() == [
        {"booked_on": ["The books for this month are closed."]},
        {},
    ]

    # Moving it out of the closed month is allowed: the sent date wins.
    response = api.patch(URL, [{"id": 1, "booked_on": "2026-10-01"}])
    assert response.status_code == 200
    # --8<-- [end:patch]

    # --8<-- [start:invalid]
    # An invalid date gives no key (None); the field reports the error.
    response = api.post(
        URL, [{"booked_on": "yesterday", "amount": "1.00", "category": "misc"}]
    )
    assert response.status_code == 400
    assert list(response.json()[0]) == ["booked_on"]
    # --8<-- [end:invalid]
