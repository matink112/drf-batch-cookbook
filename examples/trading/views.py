from __future__ import annotations

from typing import Any

from drf_batch import BatchListSerializer, BatchMixin
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from .models import Order
from .serializers import (
    ExchangeOrderSerializer,
    ListedOrderSerializer,
    OrderSerializer,
    UniqueReferenceOrderSerializer,
)


# --8<-- [start:order]
class OrderViewSet(BatchMixin, GenericViewSet):
    queryset = Order.objects.all()
    batch_serializer_class = OrderSerializer


# --8<-- [end:order]


# --8<-- [start:listed]
class ListedOrderViewSet(BatchMixin, GenericViewSet):
    queryset = Order.objects.all()
    batch_serializer_class = ListedOrderSerializer


# --8<-- [end:listed]


# --8<-- [start:exchange]
class ExchangeOrderViewSet(BatchMixin, GenericViewSet):
    queryset = Order.objects.all()
    batch_serializer_class = ExchangeOrderSerializer


class SequentialExchangeOrderViewSet(ExchangeOrderViewSet):
    # One fetch at a time, in plan order, sync fetches inline.
    batch_concurrent_collection = False


# --8<-- [end:exchange]


# --8<-- [start:mine]
class SmallOrdersOnly(BasePermission):
    message = "Orders of 1000 or more need a manager."

    def has_object_permission(self, request: Any, view: Any, obj: Order) -> bool:
        return obj.volume < 1000


class MyOrderViewSet(BatchMixin, GenericViewSet):
    batch_serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, SmallOrdersOnly]

    def get_queryset(self) -> Any:
        # Update/delete targets come from here: someone else's order is a 404.
        return Order.objects.filter(owner=self.request.user)

    def perform_batch_create(self, serializer: BatchListSerializer) -> None:
        serializer.save(owner=self.request.user)  # merged into every row


# --8<-- [end:mine]


# --8<-- [start:unique]
class UniqueReferenceOrderViewSet(BatchMixin, GenericViewSet):
    queryset = Order.objects.all()
    batch_serializer_class = UniqueReferenceOrderSerializer


# --8<-- [end:unique]


ROUTES = [
    ("orders", OrderViewSet),
    ("listed-orders", ListedOrderViewSet),
    ("exchange-orders", ExchangeOrderViewSet),
    ("exchange-orders-sequential", SequentialExchangeOrderViewSet),
    ("my-orders", MyOrderViewSet),
    ("unique-orders", UniqueReferenceOrderViewSet),
]
