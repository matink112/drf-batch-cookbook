"""One router for every example app: each ``views.ROUTES`` lists its viewsets."""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from ledger.views import ROUTES as LEDGER
from library.views import ROUTES as LIBRARY
from logistics.views import ROUTES as LOGISTICS
from saas.views import ROUTES as SAAS
from shop.views import ROUTES as SHOP
from trading.views import ROUTES as TRADING

router = DefaultRouter()
for prefix, viewset in (*LIBRARY, *TRADING, *SHOP, *LEDGER, *SAAS, *LOGISTICS):
    router.register(prefix, viewset, basename=prefix)

urlpatterns = router.urls
