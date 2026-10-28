"""The execution-draft viewset, on drf-batch.

Replaces, in `command`'s `DraftViewSet`:

- `CreateBatchMixin` / `UpdateBatchMixin` / `DestroyBatchMixin` /
  `ImportDataFromFileMixin` and their `get_cache_db` / `get_batch_objects`
  hooks: `BatchMixin` resolves targets from `get_queryset()` (404 outside
  it) and runs collection itself.
- `get_db_filter` (about 120 lines building five lookup sets, with separate
  branches for JSON rows, Excel uploads and PATCH fallbacks to the stored
  draft): gone. The fields declare where their keys come from.
- `asyncio.run_coroutine_threadsafe(collect_execution_draft_cache_db(...),
  loop=thread_safe_loop)`: drf-batch runs the fetch graph on its own loop
  (or the ASGI server's), with `COLLECT_TIMEOUT`.

Kept as is: the send / auto-send / preview / recalculate actions (they work
on stored drafts, not on rows; see README "Next steps").
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pandas as pd
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from drf_batch import BatchListSerializer, BatchMixin, BatchOperation
from ems.protobuf import enums_pb2
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from src.apps.core.helpers import InternalUserService
from src.apps.core.permissions import HasVerifiedTrader, IsAuthenticatedExceptOption
from src.apps.emitter.kafka.entity import CdcExecutionDraftEventHeaders
from src.apps.emitter.kafka.events import send_execution_draft_events
from src.apps.order.consts import DraftState, ErrorMessages, ExecutionStrategies
from src.apps.order.execution.consts import (
    DRAFT_UPDATABLE_FIELDS,
    EXECUTION_DRAFT_UPDATABLE_FIELDS,
    UPDATE_OR_EDIT_DRAFT_BEFORE_THREE_MINUTES_ERROR_MSG,
)
from src.apps.order.execution.helpers import remove_related_strategy_attr
from src.apps.order.execution.mixins import SendDraftWithCreditViewMixin
from src.apps.order.execution.models import ExecutionDraft
from src.apps.order.execution.serializers.draft import (
    BatchDraftSerializer,
    DraftListSerializer,
    ExcelSerializer,
    SendDraftListSerializer,
    SendDraftWithCreditListSerializer,
)
from src.apps.order.filters import BaseDraftFilter
from src.apps.order.mixins import AutoSendDraftViewMixin, SendDraftViewMixin
from src.apps.order.models import ParentDraft
from tenacity import retry, stop_after_attempt, wait_fixed

from .serializers import ExecutionDraftBatchSerializer

if TYPE_CHECKING:
    from rest_framework.request import Request

DESTROY_ACTIONS = frozenset({"batch_destroy", "delete_via_post"})
DEAD_END_STATES = frozenset(
    {DraftState.EXPIRED, DraftState.DELETE_BY_USER, DraftState.DELETE_BY_TRADER}
)


class DraftViewSet(
    SendDraftWithCreditViewMixin,
    SendDraftViewMixin,
    AutoSendDraftViewMixin,
    ListModelMixin,
    BatchMixin,
    GenericViewSet,
):
    """``/drafts/batch/``: POST create, PATCH/PUT update, DELETE soft-delete."""

    queryset = ParentDraft.objects.filter(
        strategy__in=ExecutionStrategies
    ).select_related("execution_draft", "customer", "ticker")
    serializer_class = BatchDraftSerializer  # the read path (list) is unchanged
    batch_serializer_class = ExecutionDraftBatchSerializer
    # Drafts are two tables (ParentDraft + ExecutionDraft): the perform_*
    # hooks below write them in bulk. use_bulk=False only switches off
    # drf-batch's flat-fields check, since its writer is not used.
    batch_use_bulk = False
    filterset_class = BaseDraftFilter
    permission_classes = (IsAuthenticatedExceptOption,)
    send_draft_serializer_class = SendDraftListSerializer
    send_draft_with_credit_serializer_class = SendDraftWithCreditListSerializer
    send_permission_classes = (IsAuthenticated, HasVerifiedTrader)
    send_with_credit_permission_classes = send_permission_classes

    # -- scoping: unchanged. A draft outside it is now a 404 for that row. --

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        if self.action == "edit_delete_by_customer_isin":
            return queryset.filter(customer__isin=self.kwargs["customer_isin"])
        if InternalUserService.is_internal_user(self.request.user):
            return queryset
        user_id = self.request.user.id
        return queryset.filter(Q(user_id=user_id) | Q(assignee_id=user_id))

    def get_batch_rows(self, request: Request) -> list[Any]:
        rows = super().get_batch_rows(request)
        if not rows:
            raise ValidationError("The list cannot be empty.")
        return rows

    def get_batch_partial(self) -> bool:
        # PUT was a partial update too in `command`: with this, PUT runs as
        # PATCH (no "replace" in batch_actions needed).
        return True

    # -- DELETE rules: the old DestroyBatchSerializer.validate_with_instance --

    def check_batch_object_permissions(self, obj: ParentDraft) -> None:
        super().check_batch_object_permissions(obj)
        if self.action not in DESTROY_ACTIONS and self.request.method != "DELETE":
            return
        now = timezone.now()
        if obj.execution_time and now <= obj.execution_time <= now + timedelta(
            minutes=3
        ):
            raise PermissionDenied(UPDATE_OR_EDIT_DRAFT_BEFORE_THREE_MINUTES_ERROR_MSG)
        if obj.state in DEAD_END_STATES:
            raise PermissionDenied(
                ErrorMessages.STATE_IS_NOT_ELIGIBLE_FOR_DELETE.format(
                    DraftState(obj.state).label
                )
            )

    # -- writes: two tables, in bulk ------------------------------------------

    def perform_batch_create(self, serializer: BatchListSerializer) -> None:
        rows = serializer.validated_data
        drafts, items = _create_drafts(rows)
        self._send_events(
            drafts, items, enums_pb2.AuditActionEnum.AUDIT_ACTION_ENUM_CREATE
        )
        serializer.instance = [
            {"id": d.id, "reference_id": d.reference_id} for d in drafts
        ]

    def perform_batch_update(self, serializer: BatchListSerializer) -> None:
        # Every row validated (or the request would be a 4xx), so the
        # validated rows line up with the request rows and their ids.
        ids = [int(row["id"]) for row in serializer.initial_data]
        targets = self.get_queryset().in_bulk(ids)
        drafts, items = [], []
        for pk, row in zip(ids, serializer.validated_data, strict=True):
            draft = targets[pk]
            if "strategy" in row:
                remove_related_strategy_attr(draft)
            for name, value in row.items():
                setattr(draft, name, value)
                setattr(draft.execution_draft, name, value)
            drafts.append(draft)
            items.append(draft.execution_draft)
        with transaction.atomic():
            ExecutionDraft.objects.bulk_update(
                items, fields=EXECUTION_DRAFT_UPDATABLE_FIELDS
            )
            count = ParentDraft.objects.bulk_update(
                drafts, fields=DRAFT_UPDATABLE_FIELDS
            )
        self._send_events(
            drafts, items, enums_pb2.AuditActionEnum.AUDIT_ACTION_ENUM_MODIFY
        )
        serializer.instance = drafts[:count]

    def perform_batch_destroy(self, serializer: BatchListSerializer) -> None:
        # Soft delete: the state changes, the rows stay.
        drafts = list(self.get_queryset().in_bulk(serializer.validated_data).values())
        user_id = self.request.user.id
        namak = bool(self.request.query_params.get("namak"))
        for draft in drafts:
            draft.state = (
                DraftState.DELETE_BY_USER
                if draft.user_id == user_id
                else DraftState.DELETE_BY_TRADER
            )
            if namak:
                draft.comment = "Nx01: Sent to Namak"
        ParentDraft.objects.bulk_update(drafts, ["state", "comment"])
        self._send_events(
            drafts,
            [draft.execution_draft for draft in drafts],
            enums_pb2.AuditActionEnum.AUDIT_ACTION_ENUM_DELETE,
        )
        serializer.instance = drafts

    def get_batch_response(self, serializer: BatchListSerializer) -> Any:
        # The response shapes `command` clients already parse.
        count = len(serializer.instance or [])
        if serializer.operation == BatchOperation.CREATE:
            return serializer.instance
        if serializer.operation == BatchOperation.UPDATE:
            return {"msg": f"updated {count} item/s", "count": count}
        return {"message": f"{count} item/s effected"}

    def _send_events(self, drafts: list, items: list, action_id: int) -> None:
        headers = CdcExecutionDraftEventHeaders.safe_load_from_request(
            self.request, action_id=action_id
        )
        send_execution_draft_events(drafts, items, headers)

    # -- the other entry points: rows from elsewhere, same batch pipeline ----

    @action(detail=False, methods=["post"])
    def upload(self, request: Request) -> Response:
        """Excel upload: the file's rows go through the same pipeline as JSON."""
        file = ExcelSerializer(data=request.data)
        file.is_valid(raise_exception=True)
        rows = [
            {k: v for k, v in row.items() if v != "" and pd.notnull(v)}
            for row in file.validated_data["file"].to_dict("records")
        ]
        return self._run(rows, BatchOperation.CREATE, status=201)

    @action(detail=False, methods=["post"], url_path="delete")
    def delete_via_post(self, request: Request) -> Response:
        """``POST /drafts/delete/``: ids, for clients that cannot send DELETE bodies."""
        return self.run_batch(BatchOperation.DESTROY)

    @action(
        detail=False,
        methods=["DELETE", "PATCH"],
        url_path=r"batch/(?P<customer_isin>[^/.]+)",
    )
    def edit_delete_by_customer_isin(
        self, request: Request, customer_isin: str
    ) -> Response:
        """Orbis offline: the batch, scoped to one customer's drafts."""
        operation = (
            BatchOperation.UPDATE
            if request.method == "PATCH"
            else BatchOperation.DESTROY
        )
        return self.run_batch(operation)

    @action(detail=False, methods=["POST"], url_path=r"update-price/batch")
    def update_drafts_with_new_price(self, request: Request) -> Response:
        """Re-price every on-board draft: one PATCH row per draft."""
        drafts = self.filter_queryset(
            self.get_queryset().filter(state=DraftState.ON_BOARD)
        )
        rows = [
            {"id": pk, "price": request.data["price"]}
            for pk in drafts.values_list("pk", flat=True)
        ]
        return self._run(rows, BatchOperation.UPDATE, status=200)

    def _run(
        self, rows: list[dict], operation: BatchOperation, *, status: int
    ) -> Response:
        self.enforce_batch_size(rows)
        serializer = self.get_batch_serializer(data=rows, operation=operation)
        serializer.is_valid(raise_exception=True)
        perform = {
            BatchOperation.CREATE: self.perform_batch_create,
            BatchOperation.UPDATE: self.perform_batch_update,
        }[operation]
        perform(serializer)
        return Response(self.get_batch_response(serializer), status=status)


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_fixed(0.1))  # deadlocks
def _create_drafts(rows: list[dict]) -> tuple[list, list]:
    """ParentDraft + ExecutionDraft rows in two bulk inserts (unchanged helpers)."""
    with transaction.atomic():
        drafts = DraftListSerializer.create_drafts(rows)
        items = DraftListSerializer.create_execution_draft(
            drafts, {str(row["reference_id"]): row for row in rows}
        )
    return drafts, items
