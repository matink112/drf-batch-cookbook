"""13. Chains: a key derived from another derived key, plus depends_on."""

from __future__ import annotations

from _support import client
from logistics.models import Country, Region, Shipment

URL = "/rated-shipments/batch/"


def seed() -> None:
    eu = Region.objects.create(code="EU")
    na = Region.objects.create(code="NA")
    Country.objects.create(code="NL", name="Netherlands", region=eu)
    Country.objects.create(code="US", name="United States", region=na)
    Shipment.objects.create(id=1, country_code="US", weight_kg="0.80")


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    # Rates: EU 0-1kg, EU 1-5kg, NA 0-1kg.
    response = api.post(
        URL,
        [
            {"country_code": "NL", "weight_kg": "0.40"},  # (NL, 0-1kg) -> EU rate
            {"country_code": "NL", "weight_kg": "3.00"},  # (NL, 1-5kg) -> EU rate
            {"country_code": "US", "weight_kg": "3.00"},  # (US, 1-5kg) -> none
        ],
    )
    assert response.status_code == 400
    assert response.json() == [
        {},
        {},
        {"weight_kg": ["No rate for this weight to that region."]},
    ]
    # --8<-- [end:post]

    # --8<-- [start:patch]
    # The weight only: band from the sent weight, country from the stored row.
    response = api.patch(URL, [{"id": 1, "weight_kg": "2.00"}])
    assert response.status_code == 400  # (US, 1-5kg)
    response = api.patch(URL, [{"id": 1, "weight_kg": "0.95"}])
    assert response.status_code == 200  # (US, 0-1kg)
    # --8<-- [end:patch]
