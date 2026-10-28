from __future__ import annotations

from typing import Any

from drf_batch import BatchSerializer, CachedRelatedField, CachedServiceField
from rest_framework import serializers

from .models import Reservation
from .services import STOCK, fetch_active_coupons


# --8<-- [start:coupon]
class CouponReservationSerializer(BatchSerializer):
    warehouse = CachedRelatedField(lookup="code")
    product = CachedRelatedField(lookup="sku")
    quantity = serializers.IntegerField(min_value=1)
    # Writable: a code the row sends must be active ("not active" otherwise).
    # A PATCH that leaves it out still sends the stored code to the service.
    coupon_code = CachedServiceField(
        fetch=fetch_active_coupons,
        error="Coupon '{value}' is not active.",
        required=False,
    )

    class Meta:
        model = Reservation
        fields = ("id", "warehouse", "product", "quantity", "coupon_code")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # A stored code the service no longer lists is not an automatic
        # error (the client did not send it): the serializer decides.
        stored = self.instance.coupon_code if self.instance is not None else ""
        if "coupon_code" not in attrs and stored and self.cached("coupon_code") is None:
            raise serializers.ValidationError(
                {"coupon_code": [f"Coupon '{stored}' has ended; send a new one."]}
            )
        return attrs


# --8<-- [end:coupon]


# --8<-- [start:sku]
class SkuField(CachedRelatedField):
    """Accepts ``" ab_1 "`` for ``"AB-1"``: shop staff type SKUs by hand."""

    def prepare_key(self, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip().upper().replace("_", "-")
        # The base class coerces to the sku column's type and rejects
        # lists, dicts and booleans with a 400 before anything is fetched.
        return super().prepare_key(value)


class SkuReservationSerializer(BatchSerializer):
    warehouse = CachedRelatedField(lookup="code")
    product = SkuField(lookup="sku", error="Unknown SKU '{value}'.")
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Reservation
        fields = ("id", "warehouse", "product", "quantity")


# --8<-- [end:sku]


# --8<-- [start:stock]
class StockLevelField(CachedServiceField):
    """A service field as a subclass: override ``fetch`` instead of ``fetch=``."""

    def fetch(self, keys: set[Any], collected: dict[str, Any], context: Any) -> Any:
        # keys are (warehouse code, sku) pairs, one per row.
        return {key: STOCK.get(key, 0) for key in keys}


class StockedReservationSerializer(BatchSerializer):
    warehouse = CachedRelatedField(lookup="code")
    product = CachedRelatedField(lookup="sku")
    quantity = serializers.IntegerField(min_value=1)
    # Keyed by the pair: each half is the row's value or, on a PATCH that
    # leaves it out, the stored one.
    available = StockLevelField(read_only=True, derived_from=("warehouse", "product"))

    class Meta:
        model = Reservation
        fields = ("id", "warehouse", "product", "quantity", "available")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 0))
        available = self.cached("available") or 0
        if quantity > available:
            raise serializers.ValidationError(
                {"quantity": [f"Only {available} in stock."]}
            )
        return attrs


# --8<-- [end:stock]


# --8<-- [start:plain]
class ReservationSerializer(BatchSerializer):
    warehouse = CachedRelatedField(lookup="code")
    product = CachedRelatedField(lookup="sku")
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Reservation
        fields = ("id", "warehouse", "product", "quantity")


# --8<-- [end:plain]
