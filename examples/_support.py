"""Helpers shared by the scenario walkthroughs."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient


def user(username: str = "alice") -> User:
    return User.objects.get_or_create(username=username)[0]


def client(username: str = "alice") -> APIClient:
    """An API client authenticated as ``username``."""
    api = APIClient()
    api.force_authenticate(user=user(username))
    return api


@contextmanager
def queries() -> Iterator[CaptureQueriesContext]:
    """Capture the queries of the request thread."""
    with CaptureQueriesContext(connection) as captured:
        yield captured


def reads(captured: CaptureQueriesContext, table: str) -> int:
    """How many SELECTs read ``table`` directly (``FROM``, not a ``JOIN``)."""
    return sum(
        1
        for query in captured
        if query["sql"].startswith("SELECT") and f'FROM "{table}"' in query["sql"]
    )


def joins(captured: CaptureQueriesContext, table: str) -> int:
    """How many queries join ``table``."""
    return sum(1 for query in captured if f'JOIN "{table}"' in query["sql"])
