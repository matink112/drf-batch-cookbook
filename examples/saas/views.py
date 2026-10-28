from __future__ import annotations

from typing import Any

from drf_batch import BatchMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from .models import Project, Subscription
from .serializers import ProjectSerializer, SubscriptionSerializer


# --8<-- [start:projects]
class ProjectViewSet(BatchMixin, GenericViewSet):
    batch_serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    # PUT (batch_replace) is opt-in.
    batch_actions = ("create", "update", "replace", "destroy")

    def get_queryset(self) -> Any:
        # PATCH/PUT/DELETE targets: projects in the user's workspaces only.
        return Project.objects.filter(workspace__members=self.request.user)


# --8<-- [end:projects]


# --8<-- [start:subscriptions]
class SubscriptionViewSet(BatchMixin, GenericViewSet):
    queryset = Subscription.objects.all()
    batch_serializer_class = SubscriptionSerializer
    batch_actions = ("update",)  # billing creates and deletes them


# --8<-- [end:subscriptions]


ROUTES = [("projects", ProjectViewSet), ("subscriptions", SubscriptionViewSet)]
