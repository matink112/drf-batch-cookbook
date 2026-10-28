from __future__ import annotations

from drf_batch import BatchMixin
from rest_framework.viewsets import GenericViewSet

from .collectors import TreasuryCollector
from .models import Expense, Transfer
from .serializers import ExpenseSerializer, RatedTransferSerializer, TransferSerializer


class TransferViewSet(BatchMixin, GenericViewSet):
    queryset = Transfer.objects.all()
    batch_serializer_class = TransferSerializer


class ExpenseViewSet(BatchMixin, GenericViewSet):
    queryset = Expense.objects.all()
    batch_serializer_class = ExpenseSerializer


# --8<-- [start:view]
class TreasuryTransferViewSet(BatchMixin, GenericViewSet):
    queryset = Transfer.objects.all()
    batch_serializer_class = RatedTransferSerializer
    batch_collector_class = TreasuryCollector


# --8<-- [end:view]


ROUTES = [
    ("transfers", TransferViewSet),
    ("expenses", ExpenseViewSet),
    ("treasury-transfers", TreasuryTransferViewSet),
]
