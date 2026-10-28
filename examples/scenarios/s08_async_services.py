"""8. Async services: concurrent fetches, run_sync for the ORM, timeouts."""

from __future__ import annotations

import time

from django.test import override_settings

from _support import client
from logistics import services
from logistics.models import Country, Region

URL = "/quoted-shipments/batch/"


def seed() -> None:
    eu = Region.objects.create(code="EU")
    na = Region.objects.create(code="NA")
    Country.objects.create(code="NL", name="Netherlands", region=eu)
    Country.objects.create(code="DE", name="Germany", region=eu)
    Country.objects.create(code="US", name="United States", region=na)


def walk() -> None:
    api = client()

    # --8<-- [start:post]
    started = time.perf_counter()
    response = api.post(
        URL,
        [
            {"country_code": "NL", "weight_kg": "1.00", "carrier": "POSTNL"},
            {"country_code": "DE", "weight_kg": "2.00", "carrier": "DHL"},
            {"country_code": "NL", "weight_kg": "0.50", "carrier": "DHL"},
        ],
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 201
    # quote and customs each take LATENCY (0.3s) and run at the same time.
    assert elapsed < 2 * services.LATENCY
    # --8<-- [end:post]

    # --8<-- [start:miss]
    response = api.post(
        URL, [{"country_code": "DE", "weight_kg": "1.00", "carrier": "POSTNL"}]
    )
    assert response.status_code == 400
    assert response.json() == [
        {"carrier": ["This carrier does not serve that country."]}
    ]
    # --8<-- [end:miss]

    # --8<-- [start:timeout]
    with override_settings(DRF_BATCH={"COLLECT_TIMEOUT": 1.0}):
        response = api.post(
            URL, [{"country_code": "US", "weight_kg": "1.00", "carrier": "SLOWPOST"}]
        )
    assert response.status_code == 504
    assert response.json()["detail"]
    # --8<-- [end:timeout]
