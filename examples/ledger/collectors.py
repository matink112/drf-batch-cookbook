from __future__ import annotations

from typing import Any

from drf_batch import BatchCollector

from .models import Currency
from .services import treasury_lookup


# --8<-- [start:collector]
class TreasuryCollector(BatchCollector):
    """Replaces auto collection: must return *every* map the fields use."""

    def collect(self, keys: dict[str, set[Any]], context: Any) -> dict[str, Any]:
        # keys holds every map's key set, derived and stored keys included:
        # {"currency": {"EUR", "USD"}, "rate": {("EUR", "USD")}}
        answer = treasury_lookup(keys.get("currency", set()), keys.get("rate", set()))
        currencies = Currency.objects.in_bulk(
            keys.get("currency", set()), field_name="code"
        )
        return {"currency": currencies, "rate": answer["rates"]}


# --8<-- [end:collector]
