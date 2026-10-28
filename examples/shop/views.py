from __future__ import annotations

from django.db import OperationalError, transaction
from django.utils.decorators import method_decorator
from drf_batch import BatchMixin, FixedRetryPolicy
from rest_framework.viewsets import GenericViewSet

from .models import Reservation
from .serializers import (
    CouponReservationSerializer,
    ReservationSerializer,
    SkuReservationSerializer,
    StockedReservationSerializer,
)


class CouponReservationViewSet(BatchMixin, GenericViewSet):
    queryset = Reservation.objects.all()
    batch_serializer_class = CouponReservationSerializer


class SkuReservationViewSet(BatchMixin, GenericViewSet):
    queryset = Reservation.objects.all()
    batch_serializer_class = SkuReservationSerializer


class StockedReservationViewSet(BatchMixin, GenericViewSet):
    queryset = Reservation.objects.all()
    batch_serializer_class = StockedReservationSerializer


# --8<-- [start:writes]
class ReservationViewSet(BatchMixin, GenericViewSet):
    """Defaults: bulk_create / bulk_update, no model signals, {"count": N}."""

    queryset = Reservation.objects.all()
    batch_serializer_class = ReservationSerializer


# A retry cannot recover inside the request's transaction (ATOMIC_REQUESTS),
# so this view runs outside it: each attempt is its own transaction.
@method_decorator(transaction.non_atomic_requests, name="dispatch")
class AuditedReservationViewSet(ReservationViewSet):
    batch_use_bulk = False  # per-row save(): signals and save() overrides run
    batch_retry_policy = FixedRetryPolicy(
        attempts=3, delay=0.05, retry_on=(OperationalError,)
    )
    batch_response = "data"  # the serialized rows instead of {"count": N}


# --8<-- [end:writes]


ROUTES = [
    ("coupon-reservations", CouponReservationViewSet),
    ("sku-reservations", SkuReservationViewSet),
    ("stocked-reservations", StockedReservationViewSet),
    ("reservations", ReservationViewSet),
    ("audited-reservations", AuditedReservationViewSet),
]
