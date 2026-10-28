from __future__ import annotations

from django.db import models


# --8<-- [start:models]
class Region(models.Model):
    code = models.CharField(max_length=8, unique=True)


class Country(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=64)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)


class Shipment(models.Model):
    # A plain column holding a country code: no ForeignKey.
    country_code = models.CharField(max_length=2)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    carrier = models.CharField(max_length=16, default="POSTNL")


# --8<-- [end:models]
