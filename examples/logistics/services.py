"""Mocked external systems for the logistics examples."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from drf_batch.loop import run_sync

from .models import Country

# The carriers' quote APIs: (country, carrier) -> price.
QUOTES = {
    ("NL", "POSTNL"): Decimal("6.95"),
    ("DE", "DHL"): Decimal("8.50"),
    ("NL", "DHL"): Decimal("7.40"),
    ("US", "SLOWPOST"): Decimal("21.00"),
}
LATENCY = 0.3  # seconds per remote call

# The pricing service: (region, weight band) -> rate.
RATES = {
    ("EU", "0-1kg"): Decimal("4.50"),
    ("EU", "1-5kg"): Decimal("8.00"),
    ("NA", "0-1kg"): Decimal("12.00"),
}
SURCHARGES = {"0-1kg": Decimal("0"), "1-5kg": Decimal("1.50"), "5kg+": Decimal("6")}


# --8<-- [start:async]
async def fetch_quotes(
    keys: set[tuple[str, str]], collected: dict, context: Any
) -> dict:
    """One remote call for every (country, carrier) pair in the batch."""
    slow = any(carrier == "SLOWPOST" for _country, carrier in keys)
    await asyncio.sleep(LATENCY * (10 if slow else 1))  # the HTTP call
    return {pair: QUOTES[pair] for pair in keys if pair in QUOTES}


async def fetch_customs(keys: set[str], collected: dict, context: Any) -> dict:
    """Customs zone per country: needs the ORM, so it goes through run_sync."""
    regions = await run_sync(
        lambda: dict(
            Country.objects.filter(code__in=keys).values_list("code", "region__code")
        )
    )
    await asyncio.sleep(LATENCY)  # the customs API
    return {
        code: "eu" if region == "EU" else "export" for code, region in regions.items()
    }


# --8<-- [end:async]


# --8<-- [start:rates]
def fetch_surcharges(keys: set[str], collected: dict, context: Any) -> dict:
    return {band: SURCHARGES[band] for band in keys}


def fetch_rates(keys: set[tuple[str, str]], collected: dict, context: Any) -> dict:
    """Keyed by (country code, weight band); priced by the country's region,
    which only the fetched Country rows know: hence depends_on=("country",)."""
    countries = collected["country"]
    rates = {}
    for code, band in keys:
        country = countries.get(code)
        rate = RATES.get((country.region.code, band)) if country else None
        if rate is not None:
            rates[(code, band)] = rate
    return rates


# --8<-- [end:rates]
