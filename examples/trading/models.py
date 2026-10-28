from __future__ import annotations

from django.conf import settings
from django.db import models


# --8<-- [start:models]
class Ticker(models.Model):
    isin = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=128)


class Customer(models.Model):
    isin = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=128)


class Order(models.Model):
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    volume = models.PositiveIntegerField()
    reference_id = models.CharField(max_length=64)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ticker", "customer"], name="one_order_per_ticker_customer"
            )
        ]


# --8<-- [end:models]


# --8<-- [start:note]
class OrderNote(models.Model):
    """A note blocks deleting its order (PROTECT)."""

    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    text = models.CharField(max_length=256)


# --8<-- [end:note]
