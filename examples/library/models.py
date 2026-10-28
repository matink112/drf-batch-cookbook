from __future__ import annotations

import uuid

from django.db import models


# --8<-- [start:models]
class Author(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)


class Book(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    pages = models.PositiveIntegerField()


# --8<-- [end:models]
