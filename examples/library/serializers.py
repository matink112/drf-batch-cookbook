from __future__ import annotations

from drf_batch import BatchSerializer, CachedRelatedField

from .models import Book


# --8<-- [start:serializer]
class BookSerializer(BatchSerializer):
    # No options: the model comes from the Book.author ForeignKey, and rows
    # send the author's primary key (a UUID here).
    author = CachedRelatedField()

    class Meta:
        model = Book
        fields = ("id", "author", "title", "pages")


# --8<-- [end:serializer]
