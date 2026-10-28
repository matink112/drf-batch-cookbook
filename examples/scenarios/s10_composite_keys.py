"""10. Composite keys: derived_from=("warehouse", "product")."""

from __future__ import annotations

from _support import client, joins, queries, reads
from shop.models import Product, Reservation, Warehouse

URL = "/stocked-reservations/batch/"


def seed() -> None:
    ams = Warehouse.objects.create(code="AMS", city="Amsterdam")
    Warehouse.objects.create(code="BER", city="Berlin")
    kettle = Product.objects.create(sku="AB-1", name="Kettle")
    Product.objects.create(sku="CD-2", name="Toaster")
    Reservation.objects.create(id=1, warehouse=ams, product=kettle, quantity=2)


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    # Stock: AMS/AB-1 = 5, AMS/CD-2 = 0, BER/AB-1 = 20.
    response = api.post(
        URL,
        [
            {"warehouse": "BER", "product": "AB-1", "quantity": 12},
            {"warehouse": "AMS", "product": "CD-2", "quantity": 1},
        ],
    )
    assert response.status_code == 400
    assert response.json() == [{}, {"quantity": ["Only 0 in stock."]}]
    # --8<-- [end:post]

    # --8<-- [start:patch]
    # Only the quantity: the pair comes from the stored row (AMS, AB-1).
    with queries() as captured:
        response = api.patch(URL, [{"id": 1, "quantity": 9}])
    assert response.status_code == 400
    assert response.json() == [{"quantity": ["Only 5 in stock."]}]
    # The target query joins warehouse and product for their codes:
    assert joins(captured, "shop_warehouse") == 1
    assert joins(captured, "shop_product") == 1
    # --8<-- [end:patch]
    assert reads(captured, "shop_warehouse") == 1  # the warehouse lookup

    # --8<-- [start:patch_half]
    # Half the pair sent, half stored: (BER, AB-1).
    response = api.patch(URL, [{"id": 1, "warehouse": "BER", "quantity": 9}])
    assert response.status_code == 200
    # --8<-- [end:patch_half]
    assert Reservation.objects.get(id=1).warehouse.code == "BER"
