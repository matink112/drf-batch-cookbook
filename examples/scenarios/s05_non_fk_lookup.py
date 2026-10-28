"""5. A lookup for a plain column: model=/queryset=, read_only, derived_from."""

from __future__ import annotations

from _support import client
from logistics.models import Country, Region, Shipment

URL = "/shipments/batch/"


def seed() -> None:
    eu = Region.objects.create(code="EU")
    Country.objects.create(code="NL", name="Netherlands", region=eu)
    Country.objects.create(code="DE", name="Germany", region=eu)


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    response = api.post(
        URL,
        [
            {"country_code": "NL", "weight_kg": "1.20"},
            {"country_code": "XX", "weight_kg": "2.00"},
        ],
    )
    assert response.status_code == 400
    assert response.json() == [{}, {"country_code": ["Unknown country 'XX'."]}]
    # --8<-- [end:post]

    # --8<-- [start:read_only]
    # "country" is read-only: a value in the row is ignored, not checked.
    response = api.post(
        URL, [{"country_code": "NL", "weight_kg": "1.20", "country": "nonsense"}]
    )
    assert response.status_code == 201
    # --8<-- [end:read_only]

    # --8<-- [start:patch]
    # A stored code that is no longer valid is caught on any PATCH.
    stale = Shipment.objects.create(country_code="YU", weight_kg="3.00")
    response = api.patch(URL, [{"id": stale.pk, "weight_kg": "2.50"}])
    assert response.status_code == 400
    assert response.json() == [{"country_code": ["Unknown country 'YU'."]}]
    # --8<-- [end:patch]
