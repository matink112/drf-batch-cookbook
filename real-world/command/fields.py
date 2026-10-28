"""Cached fields for the execution-draft batch endpoint.

These replace, in `command`:

- `BatchTickerSerializerMixin`, `BatchCustomerSerializerMixin`,
  `BatchAssigneeSerializerMixin` (field + `validate_<field>` against
  `context["cache_db"]`),
- `DraftViewSet.get_db_filter` (hand-built lookup sets, including the PATCH
  fallbacks `instances[id].ticker.isin`),
- `collect_execution_draft_cache_db` and its `get_draft_*_for_cache_db`
  helpers (one TaskGroup per request, maps in a dict).

Each map is now one field; drf-batch extracts the keys (sent, derived or
stored), runs the fetches as one dependency graph, and validates every row
against the results.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from django.db.models import Q
from drf_batch import CachedRelatedField
from src.apps.authentication.models import User
from src.apps.order.consts import PRICE_PARAMETER_WITH_NAV_REGEX
from src.apps.order.execution.helpers import (
    aget_price_map,
    resolve_execution_draft_assignee_trader_candidates,
    save_additional_customers,
)
from src.apps.ticker.service import TickerService

if TYPE_CHECKING:
    from drf_batch import BatchContext


# --------------------------------------------------------------------------
# Related lookups
# --------------------------------------------------------------------------


class TickerField(CachedRelatedField):
    """A ticker by ISIN **or** symbol (`ticker_filter_by_symbol_isin_in_bulk`).

    The map is keyed by both spellings, so a row sending `"FOOLAD"` and one
    sending its ISIN resolve the same instance from one query. On a PATCH that
    leaves `ticker` out, the stored ticker's ISIN is the key (read across the
    FK; drf-batch joins `ticker` into the target query for it).
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(lookup="isin", **kwargs)

    def prepare_key(self, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
        return super().prepare_key(value)

    def fetch(self, keys: set[str], collected: dict, context: BatchContext) -> dict:
        tickers = self.get_queryset().filter(Q(symbol__in=keys) | Q(isin__in=keys))
        by_key: dict[str, Any] = {}
        for ticker in tickers:
            by_key[ticker.isin] = ticker
            by_key[ticker.symbol] = ticker
        return by_key


class CustomerField(CachedRelatedField):
    """A customer by ISIN; unknown ISINs may be created on the fly.

    `save_additional_customers` used to run in `DraftListSerializer.
    to_internal_value`, patching `cache_db["customer_map"]` before the rows
    were validated. Here it runs inside the fetch, which is exactly "before
    the rows are validated, once per batch".
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            lookup="isin",
            error="Customer '{value}' not found.",
            **kwargs,
        )

    def fetch(self, keys: set[str], collected: dict, context: BatchContext) -> dict:
        found = (
            self.get_queryset()
            .only("isin", "name", "can_submit_inline_order")
            .in_bulk(keys, field_name="isin")
        )
        # Dynamic customer creation (toggled per user group): unchanged helper.
        created = save_additional_customers(
            {"customer_map": found, "customers_isins": keys},
            context["request"].user.id,
        )
        return found | created


class AssigneeField(CachedRelatedField):
    """A user by e-mail, case-insensitive (`user_filter_by_email_in_bulk`)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            queryset=User.objects.only("email"),
            lookup="email",
            error="User '{value}' not found.",
            **kwargs,
        )

    def prepare_key(self, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip().lower()
        return super().prepare_key(value)

    def fetch(self, keys: set[str], collected: dict, context: BatchContext) -> dict:
        users = self.get_queryset().filter(email__in=keys)
        return {user.email.lower(): user for user in users}


# --------------------------------------------------------------------------
# Service fetches (async: they run on the event loop, concurrently)
# --------------------------------------------------------------------------
#
# Keys are what the row (or the stored draft) says about the ticker: an ISIN
# or a symbol. The market services want ISINs, which only the fetched Ticker
# rows know, hence `depends_on=("ticker",)` on these fields. That is the old
# `asyncio.wait_for(ticker_map_task)` inside `get_draft_*_for_cache_db`.


def _isins(keys: set[str], collected: dict) -> dict[str, str]:
    """``{row key: isin}`` for the keys whose ticker exists."""
    tickers = collected.get("ticker", {})
    return {key: tickers[key].isin for key in keys if key in tickers}


async def fetch_ticker_data(keys: set[str], collected: dict, context: Any) -> dict:
    """Market data (tick size, market hours, state) per ticker key."""
    isins = _isins(keys, collected)
    data = await TickerService.aget_ticker_data(set(isins.values()))
    return {key: data[isin] for key, isin in isins.items() if isin in data}


async def fetch_live_prices(keys: set[str], collected: dict, context: Any) -> dict:
    """Last quotes, only for the tickers whose rows need one (see `key=`)."""
    isins = _isins(keys, collected)
    quotes = await aget_price_map(set(isins.values()))
    return {key: quotes[isin] for key, isin in isins.items() if isin in quotes}


async def fetch_commissions(keys: set[str], collected: dict, context: Any) -> dict:
    """Commission rates, only for rows sized by value (see `key=`)."""
    isins = _isins(keys, collected)
    commissions = await TickerService.aget_ticker_commission(set(isins.values()))
    return {
        key: commissions[isin] for key, isin in isins.items() if isin in commissions
    }


async def fetch_assignee_candidates(keys: set, collected: dict, context: Any) -> dict:
    """Round-robin traders for application (Keycloak) requests without an assignee.

    Request-level, not per row: the field has no keys, and a service fetch
    still runs with an empty key set. The map has a single entry.
    """
    request = context["request"]
    if not hasattr(request, "application") or getattr(request, "is_internal", False):
        return {}
    traders = await resolve_execution_draft_assignee_trader_candidates(
        application_user_id=request.application.id
    )
    return {"traders": list(traders.values())}


# --------------------------------------------------------------------------
# Key builders (`key=`): which rows need a quote / a commission
# --------------------------------------------------------------------------


def is_parametric(price: Any) -> bool:
    return isinstance(price, str) and bool(
        re.match(PRICE_PARAMETER_WITH_NAV_REGEX, price, re.IGNORECASE)
    )


def live_price_key(ticker: str | None, price: Any) -> str | None:
    """A quote is needed for a parametric price ("best_bid+2"), sent in the row.

    A stored price is always an integer, so a PATCH that leaves `price` out
    needs no quote.
    """
    return ticker if is_parametric(price) else None


def commission_key(ticker: str | None, value: int | None) -> str | None:
    """A commission is needed when the draft is sized by value (sent or stored)."""
    return ticker if value is not None else None
