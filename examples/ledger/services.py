"""Mocked external systems for the ledger examples."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

# The accounting system: fiscal period -> status.
PERIODS = {"2026-09": "closed", "2026-10": "open"}

# The treasury system: (from, to) -> rate.
RATES = {("EUR", "USD"): Decimal("1.08"), ("USD", "EUR"): Decimal("0.93")}

# Every call the treasury system received (the collector example reads it).
TREASURY_CALLS: list[dict[str, Any]] = []


# --8<-- [start:periods]
def fetch_period_status(keys: set[str], collected: dict, context: Any) -> dict:
    """``{"2026-09": "closed", ...}`` for the periods the rows touch."""
    return {period: PERIODS.get(period, "open") for period in keys}


# --8<-- [end:periods]


# --8<-- [start:rates]
def fetch_rates(keys: set[tuple[str, str]], collected: dict, context: Any) -> dict:
    """``{(from, to): rate}``; a pair the treasury does not quote is missing."""
    return {pair: RATES[pair] for pair in keys if pair in RATES}


def treasury_lookup(currencies: set[str], pairs: set[tuple[str, str]]) -> dict:
    """One RPC that answers currencies *and* rates."""
    TREASURY_CALLS.append({"currencies": currencies, "pairs": pairs})
    return {"rates": {pair: RATES[pair] for pair in pairs if pair in RATES}}


# --8<-- [end:rates]
