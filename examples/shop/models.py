from __future__ import annotations

from django.db import models


# --8<-- [start:models]
class Product(models.Model):
    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)


class Warehouse(models.Model):
    code = models.CharField(max_length=8, unique=True)
    city = models.CharField(max_length=64)


class Reservation(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    coupon_code = models.CharField(max_length=32, blank=True, default="")


# --8<-- [end:models]


# --8<-- [start:event]
class ReservationEvent(models.Model):
    """Written by a post_save receiver (see shop/signals.py)."""

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    kind = models.CharField(max_length=16)


# --8<-- [end:event]
