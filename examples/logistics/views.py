from __future__ import annotations

from drf_batch import BatchMixin
from rest_framework.viewsets import GenericViewSet

from .models import Shipment
from .serializers import (
    QuotedShipmentSerializer,
    RatedShipmentSerializer,
    ShipmentSerializer,
)


class ShipmentViewSet(BatchMixin, GenericViewSet):
    queryset = Shipment.objects.all()
    batch_serializer_class = ShipmentSerializer


class QuotedShipmentViewSet(BatchMixin, GenericViewSet):
    queryset = Shipment.objects.all()
    batch_serializer_class = QuotedShipmentSerializer


class RatedShipmentViewSet(BatchMixin, GenericViewSet):
    queryset = Shipment.objects.all()
    batch_serializer_class = RatedShipmentSerializer


ROUTES = [
    ("shipments", ShipmentViewSet),
    ("quoted-shipments", QuotedShipmentViewSet),
    ("rated-shipments", RatedShipmentViewSet),
]
