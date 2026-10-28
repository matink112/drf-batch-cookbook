"""Mocked external systems for the SaaS examples."""

from __future__ import annotations

from typing import Any

# The billing system: plan -> seat limit.
PLAN_LIMITS = {"starter": 5, "team": 50}

# The finance system: cost center -> status.
COST_CENTERS = {"GENERAL": "open", "RND": "open", "LEGACY": "closed"}
COST_CENTER_CALLS: list[set[str]] = []


# --8<-- [start:limits]
def fetch_seat_limits(keys: set[str], collected: dict, context: Any) -> dict:
    return {plan: PLAN_LIMITS[plan] for plan in keys if plan in PLAN_LIMITS}


# --8<-- [end:limits]


# --8<-- [start:cost_centers]
def fetch_open_cost_centers(keys: set[str], collected: dict, context: Any) -> dict:
    COST_CENTER_CALLS.append(set(keys))
    return {code: code for code in keys if COST_CENTERS.get(code) == "open"}


# --8<-- [end:cost_centers]
