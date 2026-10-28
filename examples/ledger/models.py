from __future__ import annotations

from django.db import models


# --8<-- [start:models]
class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=64)


class Transfer(models.Model):
    from_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="+"
    )
    to_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="+"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)


# --8<-- [end:models]


# --8<-- [start:expense]
class Expense(models.Model):
    booked_on = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=32)


# --8<-- [end:expense]
