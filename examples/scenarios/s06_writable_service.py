"""6. A writable service field: sent keys checked, stored keys re-checked."""

from __future__ import annotations

from _support import client
from shop import services
from shop.models import Product, Reservation, Warehouse

URL = "/coupon-reservations/batch/"


def seed() -> None:
    services.COUPONS.update({"WELCOME10": "active", "SPRING": "active"})
    Warehouse.objects.create(code="AMS", city="Amsterdam")
    Product.objects.create(sku="AB-1", name="Kettle")
    Product.objects.create(sku="CD-2", name="Toaster")


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    response = api.post(
        URL,
        [
            {
                "warehouse": "AMS",
                "product": "AB-1",
                "quantity": 1,
                "coupon_code": "SPRING",
            },
            {
                "warehouse": "AMS",
                "product": "CD-2",
                "quantity": 2,
                "coupon_code": "WINTER",
            },
        ],
    )
    assert response.status_code == 400
    assert response.json() == [{}, {"coupon_code": ["Coupon 'WINTER' is not active."]}]
    # --8<-- [end:post]

    response = api.post(
        URL,
        [
            {
                "warehouse": "AMS",
                "product": "AB-1",
                "quantity": 1,
                "coupon_code": "SPRING",
            }
        ],
    )
    assert response.status_code == 201
    reservation = Reservation.objects.get()

    # --8<-- [start:patch]
    services.COUPONS["SPRING"] = "ended"  # marketing ends the campaign

    # The PATCH only changes the quantity, yet the service still sees the
    # stored "SPRING": validate() rejects it.
    response = api.patch(URL, [{"id": reservation.pk, "quantity": 3}])
    assert response.status_code == 400
    assert response.json() == [
        {"coupon_code": ["Coupon 'SPRING' has ended; send a new one."]}
    ]

    # Sending a new code replaces the stored one.
    response = api.patch(
        URL, [{"id": reservation.pk, "quantity": 3, "coupon_code": "WELCOME10"}]
    )
    assert response.status_code == 200
    # --8<-- [end:patch]
    reservation.refresh_from_db()
    assert (reservation.quantity, reservation.coupon_code) == (3, "WELCOME10")
