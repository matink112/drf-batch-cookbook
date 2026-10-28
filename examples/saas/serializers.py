from __future__ import annotations

from typing import Any

from drf_batch import BatchSerializer, CachedRelatedField, CachedServiceField
from rest_framework import serializers

from .models import Project, Subscription, Workspace
from .services import fetch_open_cost_centers, fetch_seat_limits


# --8<-- [start:workspace]
class MemberWorkspaceField(CachedRelatedField):
    """Only workspaces the requesting user belongs to, and not archived."""

    def get_queryset(self) -> Any:
        user = self.context["request"].user
        return Workspace.objects.filter(members=user, archived=False)


# --8<-- [end:workspace]


# --8<-- [start:project]
class ProjectSerializer(BatchSerializer):
    workspace = MemberWorkspaceField(error="Workspace {value} not found.")
    name = serializers.CharField(max_length=64)
    budget = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    # Optional and writable: the service checks a sent code, and on PATCH/PUT
    # a row that leaves it out still has its stored code checked.
    cost_center = CachedServiceField(
        fetch=fetch_open_cost_centers,
        error="Cost center '{value}' is closed.",
        required=False,
    )

    class Meta:
        model = Project
        fields = ("id", "workspace", "name", "budget", "cost_center")


# --8<-- [end:project]


# --8<-- [start:subscription]
class SubscriptionSerializer(BatchSerializer):
    seats = serializers.IntegerField(min_value=1)
    # plan_code is a column the API must not change, so it is not on the
    # serializer. derived_from may still name it: its value comes from the
    # stored row.
    seat_limit = CachedServiceField(
        fetch=fetch_seat_limits, read_only=True, derived_from="plan_code"
    )

    class Meta:
        model = Subscription
        fields = ("id", "seats", "seat_limit")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        limit = self.cached("seat_limit")
        if limit is not None and attrs.get("seats", 0) > limit:
            plan = self.instance.plan_code
            raise serializers.ValidationError(
                {"seats": [f"The {plan} plan allows {limit} seats."]}
            )
        return attrs


# --8<-- [end:subscription]
