"""19. Write options: bulk vs per-row, retries, the response body."""

from __future__ import annotations

from _support import client
from shop import signals
from shop.models import Product, Reservation, ReservationEvent, Warehouse

ROWS = [
    {"warehouse": "AMS", "product": "AB-1", "quantity": 1},
    {"warehouse": "AMS", "product": "CD-2", "quantity": 2},
]


def seed() -> None:
    Warehouse.objects.create(code="AMS", city="Amsterdam")
    Product.objects.create(sku="AB-1", name="Kettle")
    Product.objects.create(sku="CD-2", name="Toaster")


def walk() -> None:
    api = client()

    # --8<-- [start:bulk]
    response = api.post("/reservations/batch/", ROWS)
    assert response.status_code == 201
    assert response.json() == {"count": 2}
    assert ReservationEvent.objects.count() == 0  # bulk_create: no signals
    # --8<-- [end:bulk]
    Reservation.objects.all().delete()

    # --8<-- [start:per_row]
    signals.TRANSIENT_FAILURES["remaining"] = 1  # the first write attempt fails
    response = api.post("/audited-reservations/batch/", ROWS)
    assert response.status_code == 201
    assert signals.TRANSIENT_FAILURES["remaining"] == 0  # it did fail once
    # batch_response = "data": the rows as the serializer renders them.
    body = response.json()
    assert [row.pop("id") > 0 for row in body] == [True, True]
    assert body == ROWS
    # The retry ran the whole write again in a fresh transaction: one event
    # per row, nothing left over from the failed attempt.
    assert ReservationEvent.objects.filter(kind="created").count() == 2
    # --8<-- [end:per_row]
