"""Model signals: they only fire for per-row writes (batch_use_bulk = False)."""

from __future__ import annotations

from typing import Any

from django.db import OperationalError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Reservation, ReservationEvent

# The retry example sets this to make the next N row writes fail as if the
# database were briefly unavailable.
TRANSIENT_FAILURES = {"remaining": 0}


# --8<-- [start:audit]
@receiver(post_save, sender=Reservation)
def audit(sender: Any, instance: Reservation, created: bool, **kwargs: Any) -> None:
    kind = "created" if created else "updated"
    ReservationEvent.objects.create(reservation=instance, kind=kind)


# --8<-- [end:audit]


@receiver(pre_save, sender=Reservation)
def flaky_database(sender: Any, instance: Reservation, **kwargs: Any) -> None:
    if TRANSIENT_FAILURES["remaining"] > 0:
        TRANSIENT_FAILURES["remaining"] -= 1
        raise OperationalError("database is locked")
