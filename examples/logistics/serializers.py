from __future__ import annotations

from decimal import Decimal
from typing import Any

from drf_batch import BatchSerializer, CachedRelatedField, CachedServiceField
from rest_framework import serializers

from .models import Country, Shipment
from .services import fetch_customs, fetch_quotes, fetch_rates, fetch_surcharges


# --8<-- [start:shipment]
class ShipmentSerializer(BatchSerializer):
    country_code = serializers.CharField(max_length=2)
    weight_kg = serializers.DecimalField(max_digits=8, decimal_places=2)
    carrier = serializers.CharField(max_length=16, required=False)
    # country_code is a plain column, not a ForeignKey: model= names the
    # lookup model, and derived_from keys the lookup by the column's value
    # (sent, or stored on a PATCH). read_only: nothing is written from it.
    country = CachedRelatedField(
        queryset=Country.objects.select_related("region"),
        lookup="code",
        read_only=True,
        derived_from="country_code",
    )

    class Meta:
        model = Shipment
        fields = ("id", "country_code", "weight_kg", "carrier", "country")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if self.cached("country") is None:
            code = attrs.get("country_code", getattr(self.instance, "country_code", ""))
            raise serializers.ValidationError(
                {"country_code": [f"Unknown country '{code}'."]}
            )
        return attrs


# --8<-- [end:shipment]


# --8<-- [start:quoted]
class QuotedShipmentSerializer(ShipmentSerializer):
    # Two async fetches with no dependency between them: they run together.
    quote = CachedServiceField(
        fetch=fetch_quotes, read_only=True, derived_from=("country_code", "carrier")
    )
    customs = CachedServiceField(
        fetch=fetch_customs, read_only=True, derived_from="country_code"
    )

    class Meta(ShipmentSerializer.Meta):
        fields = (*ShipmentSerializer.Meta.fields, "quote", "customs")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        if self.cached("quote") is None:
            raise serializers.ValidationError(
                {"carrier": ["This carrier does not serve that country."]}
            )
        return attrs


# --8<-- [end:quoted]


# --8<-- [start:rated]
def weight_band(weight_kg: Decimal | None) -> str | None:
    if weight_kg is None:
        return None
    if weight_kg <= 1:
        return "0-1kg"
    return "1-5kg" if weight_kg <= 5 else "5kg+"


class RatedShipmentSerializer(ShipmentSerializer):
    # Key: the weight band ("1-5kg"), built from the weight (sent or stored).
    band = CachedServiceField(
        fetch=fetch_surcharges,
        read_only=True,
        derived_from="weight_kg",
        key=weight_band,
    )
    # Key: (country code, band). "band" is a cached field, so its *key* is
    # used: known before any fetch, no waiting. The fetch also reads the
    # Country rows (their region): that is a result, so depends_on.
    rate = CachedServiceField(
        fetch=fetch_rates,
        read_only=True,
        derived_from=("country_code", "band"),
        depends_on=("country",),
    )

    class Meta(ShipmentSerializer.Meta):
        fields = (*ShipmentSerializer.Meta.fields, "band", "rate")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        if self.cached("rate") is None:
            raise serializers.ValidationError(
                {"weight_kg": ["No rate for this weight to that region."]}
            )
        return attrs


# --8<-- [end:rated]
