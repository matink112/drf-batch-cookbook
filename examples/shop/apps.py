from __future__ import annotations

from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = "shop"

    def ready(self) -> None:
        from . import signals  # noqa: F401  (connects the receivers)
