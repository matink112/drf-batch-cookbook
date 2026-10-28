"""7. Custom keys: a field subclass overriding prepare_key."""

from __future__ import annotations

from _support import client, queries, reads
from shop.models import Product, Reservation, Warehouse

URL = "/sku-reservations/batch/"


def seed() -> None:
    Warehouse.objects.create(code="AMS", city="Amsterdam")
    Product.objects.create(sku="AB-1", name="Kettle")


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    response = api.post(
        URL,
        [
            {"warehouse": "AMS", "product": " ab_1 ", "quantity": 1},
            {"warehouse": "AMS", "product": "Ab-1", "quantity": 2},
        ],
    )
    assert response.status_code == 201
    assert Reservation.objects.filter(product__sku="AB-1").count() == 2
    # --8<-- [end:post]

    # --8<-- [start:miss]
    response = api.post(URL, [{"warehouse": "AMS", "product": "zz_9", "quantity": 1}])
    assert response.status_code == 400
    assert response.json() == [{"product": ["Unknown SKU 'ZZ-9'."]}]  # normalised
    # --8<-- [end:miss]

    # --8<-- [start:malformed]
    with queries() as captured:
        response = api.post(
            URL, [{"warehouse": "AMS", "product": {"sku": "AB-1"}, "quantity": 1}]
        )
    assert response.status_code == 400
    assert response.json() == [
        {"product": ["Invalid value for 'product': expected a string, got dict."]}
    ]
    assert reads(captured, "shop_product") == 0  # rejected before any fetch
    # --8<-- [end:malformed]
