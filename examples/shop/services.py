"""Mocked external systems for the shop examples."""

from __future__ import annotations

from typing import Any

# The marketing system: coupon code -> status.
COUPONS = {"WELCOME10": "active", "SPRING": "active", "WINTER": "ended"}

# The warehouse system: (warehouse code, sku) -> units available.
STOCK = {("AMS", "AB-1"): 5, ("AMS", "CD-2"): 0, ("BER", "AB-1"): 20}


# --8<-- [start:coupons]
def fetch_active_coupons(keys: set[str], collected: dict, context: Any) -> dict:
    """``{code: code}`` for the active coupons among ``keys``."""
    return {code: code for code in keys if COUPONS.get(code) == "active"}


# --8<-- [end:coupons]
