from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from drf_batch import BatchRelatedField, BatchSerializer, BatchServiceField
from rest_framework import serializers

from .models import Expense, Transfer
from .services import fetch_period_status, fetch_rates


# --8<-- [start:transfer]
class TransferSerializer(BatchSerializer):
    # Two ForeignKeys to Currency, one "currency" map: every code in the
    # batch (from or to) is resolved by a single query.
    from_currency = BatchRelatedField(
        lookup="code", map="currency", error="Unknown currency '{value}'."
    )
    to_currency = BatchRelatedField(
        lookup="code", map="currency", error="Unknown currency '{value}'."
    )
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )

    class Meta:
        model = Transfer
        fields = ("id", "from_currency", "to_currency", "amount")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        def currency_id(name: str) -> Any:  # sent, else stored (no query)
            if name in attrs:
                return attrs[name].pk
            return getattr(self.instance, f"{name}_id", None)

        if currency_id("from_currency") == currency_id("to_currency"):
            raise serializers.ValidationError("A transfer needs two currencies.")
        return attrs


# --8<-- [end:transfer]


# --8<-- [start:rated]
class RatedTransferSerializer(TransferSerializer):
    # Keyed by the (from, to) codes: sent, or stored on a PATCH.
    rate = BatchServiceField(
        fetch=fetch_rates,
        read_only=True,
        derived_from=("from_currency", "to_currency"),
    )

    class Meta(TransferSerializer.Meta):
        fields = (*TransferSerializer.Meta.fields, "rate")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        if self.fetched("rate") is None:
            raise serializers.ValidationError("The treasury does not quote this pair.")
        return attrs


# --8<-- [end:rated]


# --8<-- [start:expense]
def fiscal_period(booked_on: date | None) -> str | None:
    """The key builder: a date -> its "YYYY-MM" period (None: no key)."""
    return None if booked_on is None else f"{booked_on:%Y-%m}"


class ExpenseSerializer(BatchSerializer):
    booked_on = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = serializers.CharField(max_length=32)
    # derived_from hands the field's *value* (a date, sent or stored) to key=.
    period = BatchServiceField(
        fetch=fetch_period_status,
        read_only=True,
        derived_from="booked_on",
        key=fiscal_period,
    )

    class Meta:
        model = Expense
        fields = ("id", "booked_on", "amount", "category", "period")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if self.fetched("period") == "closed":
            raise serializers.ValidationError(
                {"booked_on": ["The books for this month are closed."]}
            )
        return attrs


# --8<-- [end:expense]
