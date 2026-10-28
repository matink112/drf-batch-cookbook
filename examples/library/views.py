from __future__ import annotations

from drf_batch import BatchMixin
from rest_framework.viewsets import GenericViewSet

from .models import Book
from .serializers import BookSerializer


# --8<-- [start:view]
class BookViewSet(BatchMixin, GenericViewSet):
    queryset = Book.objects.all()
    batch_serializer_class = BookSerializer


# --8<-- [end:view]


ROUTES = [("books", BookViewSet)]
