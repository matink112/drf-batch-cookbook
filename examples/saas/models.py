from __future__ import annotations

from django.conf import settings
from django.db import models


# --8<-- [start:models]
class Workspace(models.Model):
    name = models.CharField(max_length=64)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="+")
    archived = models.BooleanField(default=False)


class Project(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    cost_center = models.CharField(max_length=16, default="GENERAL")
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)


# --8<-- [end:models]


# --8<-- [start:subscription]
class Subscription(models.Model):
    """Written by the billing system; the API may only change ``seats``."""

    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE)
    plan_code = models.CharField(max_length=16)
    seats = models.PositiveIntegerField()


# --8<-- [end:subscription]
