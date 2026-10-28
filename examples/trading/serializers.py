from __future__ import annotations

from typing import Any

from drf_batch import BatchSerializer, CachedRelatedField, CachedServiceField
from rest_framework import serializers

from .models import Order, Ticker
from .services import CALLS, fetch_bands, fetch_kyc


# --8<-- [start:order]
class OrderSerializer(BatchSerializer):
    # Rows send the ISIN, not the pk; a miss uses the error template.
    ticker = CachedRelatedField(lookup="isin", error="Ticker '{value}' not found.")
    customer = CachedRelatedField(lookup="isin", error="Customer '{value}' not found.")
    volume = serializers.IntegerField(min_value=1)
    reference_id = serializers.CharField(max_length=64)

    class Meta:
        model = Order
        fields = ("id", "ticker", "customer", "volume", "reference_id")


# --8<-- [end:order]


# --8<-- [start:listed]
class ListedOrderSerializer(OrderSerializer):
    # Never read from the row. The key is the row's ticker: the one it
    # sends, or the stored one on a PATCH that leaves it out.
    band = CachedServiceField(
        fetch=fetch_bands,
        read_only=True,
        derived_from="ticker",
        depends_on=("ticker",),  # fetch_bands reads collected["ticker"]
    )

    class Meta(OrderSerializer.Meta):
        fields = (*OrderSerializer.Meta.fields, "band")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        band = self.cached("band")  # this row's value, None on a miss
        if band is None:
            raise serializers.ValidationError({"ticker": ["Ticker is not listed."]})
        if band == "B":
            raise serializers.ValidationError({"ticker": ["Ticker is suspended."]})
        return attrs


# --8<-- [end:listed]


# --8<-- [start:exchange]
class PrimaryListingField(CachedRelatedField):
    """DB-after-service: only tickers the listing service put in band A."""

    def fetch(self, keys: set[Any], collected: dict[str, Any], context: Any) -> Any:
        CALLS.append("primary_listing")
        band_a = {isin for isin, band in collected["band"].items() if band == "A"}
        return (
            self.get_queryset()
            .filter(isin__in=keys & band_a)
            .in_bulk(field_name="isin")
        )


class ExchangeOrderSerializer(ListedOrderSerializer):
    kyc = CachedServiceField(fetch=fetch_kyc, read_only=True, derived_from="customer")
    primary_listing = PrimaryListingField(
        model=Ticker,
        lookup="isin",
        read_only=True,
        derived_from="ticker",
        depends_on=("band",),
    )

    class Meta(ListedOrderSerializer.Meta):
        fields = (*ListedOrderSerializer.Meta.fields, "kyc", "primary_listing")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        if self.cached("kyc") != "verified":
            raise serializers.ValidationError(
                {"customer": ["Customer is not KYC-verified."]}
            )
        if self.cached("primary_listing") is None:
            raise serializers.ValidationError(
                {"ticker": ["Ticker has no primary listing."]}
            )
        return attrs


# --8<-- [end:exchange]


# --8<-- [start:unique]
class UniqueReferenceOrderSerializer(OrderSerializer):
    class Meta(OrderSerializer.Meta):
        # Unique within the batch and against stored rows -> 409.
        batch_unique_together = ("reference_id",)


# --8<-- [end:unique]
