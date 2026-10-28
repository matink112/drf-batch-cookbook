"""The execution-draft batch serializer, on drf-batch.

Replaces, in `command`:

- `BatchDraftSerializer` (the `StrategySerializerDispatcher`) and the seven
  `*StrategySerializer` classes. drf-batch validates every row with **one**
  child serializer, so the per-strategy differences become the
  `STRATEGY_RULES` table below. See README "Gaps": a polymorphic child is
  the main thing drf-batch lacks for this endpoint.
- `DraftListSerializer.to_internal_value` / `validate` and
  `CheckConflictListSerializerMixin`: the empty-list check moves to the
  view (`get_batch_rows`); duplicate `reference_id`s (in the batch, or
  against stored drafts) are the 409 conflict pass, derived from the
  model's `unique=True`.
- `LivePriceCalculatorListSerializerMixin`, which fetched quotes a second
  time after validation: the `live_price` field fetches them once, with
  every other lookup.
- Every `self.context["cache_db"][...]` read: `self.cached(name)` returns
  this row's value, whether its key was sent, derived or stored.
"""

from __future__ import annotations

import itertools
import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.utils import timezone
from drf_batch import BatchSerializer, CachedServiceField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from src.apps.core.dispatchers.toggle import toggle_service
from src.apps.core.exceptions import ServiceError
from src.apps.core.fields import BigIntegerField, ParametricIntegerField
from src.apps.core.helpers import LivePriceCalculator
from src.apps.customer.services import CustomerTypeService
from src.apps.order.consts import (
    PRICE_PARAMETER_WITH_NAV_REGEX,
    ExecutionStrategies,
    ParentOrderSides,
)
from src.apps.order.execution.consts import (
    DRAFT_EXECUTION_TIME_FUTURE_ERROR_MSG,
    DRAFT_EXECUTION_TIME_NOT_ALLOWED_FOR_CUSTOMER_ERROR_MSG,
    DRAFT_EXECUTION_TIME_PASSED_ERROR_MSG,
    PRICE_PARAMETER_VALIDATION_ERROR_MSG_FORMAT,
    REFERENCE_REGEX,
    UPDATE_OR_EDIT_DRAFT_BEFORE_THREE_MINUTES_ERROR_MSG,
    UPLOAD_FILE_OPTION_NOT_ALLOWED_ERROR_MSG,
    VOLUME_VALUE_ERROR_MSG,
)
from src.apps.order.execution.serializers.draft import BaseDraftSerializer
from src.apps.order.execution.service import DraftVolumeCalculatorService
from src.apps.order.helper import round_price_by_tick_size
from src.apps.order.models import ParentDraft
from src.apps.ticker.service import TickerTypeService

from .fields import (
    AssigneeField,
    CustomerField,
    TickerField,
    commission_key,
    fetch_assignee_candidates,
    fetch_commissions,
    fetch_live_prices,
    fetch_ticker_data,
    is_parametric,
    live_price_key,
)

if TYPE_CHECKING:
    from src.apps.ticker.models import Ticker


# --------------------------------------------------------------------------
# Per-strategy rules (condensed from the seven *StrategySerializer classes)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyRule:
    # The strategy parameters the strategy's serializer declared; the others
    # are dropped from the row, as an undeclared field was.
    fields: frozenset[str]
    required: frozenset[str] = frozenset()
    defaults: dict[str, Any] = field(default_factory=dict)
    sized_by_value: bool = True  # VolumeValueValidatorSerializerMixin
    nav_prices: bool = False  # PRICE_PARAMETER_WITH_NAV_REGEX allowed


_PRICED = frozenset({"price", "use_price_parameter", "volume", "value"})
S = ExecutionStrategies
STRATEGY_RULES: dict[str, StrategyRule] = {
    S.PLAIN: StrategyRule(
        _PRICED | {"wait_until_open", "volume_threshold"},
        required=frozenset({"price"}),
        defaults={"wait_until_open": False, "volume_threshold": True},
    ),
    S.PENDING: StrategyRule(
        _PRICED | {"aggressiveness", "queue_contribution"},
        required=frozenset({"price", "aggressiveness"}),
        defaults={"queue_contribution": False},
        nav_prices=True,
    ),
    S.PVOL: StrategyRule(
        _PRICED | {"target_percent", "queue_contribution"},
        required=frozenset({"price", "target_percent"}),
        defaults={"queue_contribution": False},
    ),
    S.URGENT: StrategyRule(
        _PRICED | {"queue_contribution"},
        required=frozenset({"price"}),
        defaults={"queue_contribution": False},
    ),
    S.AUTOMATIC: StrategyRule(_PRICED, defaults={"use_price_parameter": True}),
    S.VWAP: StrategyRule(
        frozenset({"volume", "queue_contribution"}),
        required=frozenset({"volume"}),
        defaults={"queue_contribution": False},
        sized_by_value=False,
    ),
    S.TWAP: StrategyRule(
        frozenset({"volume", "price"}),
        required=frozenset({"volume"}),
        sized_by_value=False,
        nav_prices=True,
    ),
}
STRATEGY_PARAMETERS = frozenset().union(
    *(rule.fields for rule in STRATEGY_RULES.values())
)


# --------------------------------------------------------------------------
# The serializer
# --------------------------------------------------------------------------


class ExecutionDraftBatchSerializer(BatchSerializer):
    # -- related lookups (one query each per batch) -------------------------
    ticker = TickerField()
    customer = CustomerField()
    assignee = AssigneeField(required=False)

    # -- ParentDraft columns -------------------------------------------------
    reference_id = serializers.CharField(
        max_length=40, default=lambda: str(uuid.uuid4())
    )
    strategy = serializers.ChoiceField(choices=ExecutionStrategies.choices)
    volume = BigIntegerField(min_value=1, required=False)
    price = ParametricIntegerField(
        min_value=1, parameter_regex=PRICE_PARAMETER_WITH_NAV_REGEX, required=False
    )
    reporter = serializers.EmailField(max_length=100, required=False)
    expire_at = serializers.DateField(default=None)
    comment = serializers.CharField(max_length=500, default=None)
    execution_time = serializers.DateTimeField(required=False)
    uses_credit = serializers.BooleanField(default=False)

    # -- ExecutionDraft columns (the one-to-one child row) ------------------
    # `source="execution_draft.<name>"` lets drf-batch read the *stored*
    # value on a PATCH (value -> commission). validate() flattens them back.
    side = serializers.ChoiceField(
        choices=ParentOrderSides.choices, source="execution_draft.side"
    )
    value = BigIntegerField(min_value=1, required=False, source="execution_draft.value")
    target_percent = serializers.FloatField(
        min_value=0.01,
        max_value=50,
        required=False,
        source="execution_draft.target_percent",
    )
    aggressiveness = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=False,
        source="execution_draft.aggressiveness",
    )
    queue_contribution = serializers.BooleanField(
        required=False, source="execution_draft.queue_contribution"
    )
    wait_until_open = serializers.BooleanField(
        required=False, source="execution_draft.wait_until_open"
    )
    volume_threshold = serializers.BooleanField(
        required=False, source="execution_draft.volume_threshold"
    )
    use_price_parameter = serializers.BooleanField(
        required=False, allow_null=True, source="execution_draft.use_price_parameter"
    )

    # -- services: read-only, keyed by the row's ticker (sent or stored) ----
    ticker_data = CachedServiceField(
        fetch=fetch_ticker_data,
        read_only=True,
        derived_from="ticker",
        depends_on=("ticker",),  # needs the Ticker rows for their ISINs
    )
    live_price = CachedServiceField(
        fetch=fetch_live_prices,
        read_only=True,
        derived_from=("ticker", "price"),
        key=live_price_key,  # only rows with a parametric price
        depends_on=("ticker",),
    )
    commission = CachedServiceField(
        fetch=fetch_commissions,
        read_only=True,
        derived_from=("ticker", "value"),  # value: sent, or the stored one
        key=commission_key,  # only rows sized by value
        depends_on=("ticker",),
    )
    assignee_candidates = CachedServiceField(
        fetch=fetch_assignee_candidates, read_only=True
    )

    class Meta:
        model = ParentDraft
        fields = (
            "id",
            "reference_id",
            "ticker",
            "customer",
            "assignee",
            "strategy",
            "volume",
            "price",
            "reporter",
            "expire_at",
            "comment",
            "execution_time",
            "uses_credit",
            "side",
            "value",
            "target_percent",
            "aggressiveness",
            "queue_contribution",
            "wait_until_open",
            "volume_threshold",
            "use_price_parameter",
            "ticker_data",
            "live_price",
            "commission",
            "assignee_candidates",
        )

    # -- field rules (unchanged) --------------------------------------------

    def validate_reference_id(self, value: str) -> str:
        if re.match(REFERENCE_REGEX, value):
            return value
        try:
            uuid.UUID(value)
        except ValueError:
            raise ValidationError("use a valid reference key") from None
        return value

    def validate_ticker(self, ticker: Ticker) -> Ticker:
        # The field already resolved the instance: only business rules here.
        if not toggle_service.ticker_type_id_is_allowed(ticker.type_id):
            raise ValidationError(
                "Order placement for this market is suspended until further notice."
            )
        if self.context["view"].action == "upload" and TickerTypeService.is_option(
            ticker
        ):
            raise ValidationError(UPLOAD_FILE_OPTION_NOT_ALLOWED_ERROR_MSG)
        return ticker

    def validate_execution_time(self, execution_time: Any) -> Any:
        now = timezone.now()
        if execution_time <= now + timedelta(minutes=2):
            raise ValidationError(DRAFT_EXECUTION_TIME_PASSED_ERROR_MSG)
        if execution_time > now + timedelta(days=30):
            raise ValidationError(DRAFT_EXECUTION_TIME_FUTURE_ERROR_MSG)
        return execution_time

    # -- row rules ------------------------------------------------------------

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # One flat dict, as the business helpers expect.
        attrs.update(attrs.pop("execution_draft", {}))
        draft: ParentDraft | None = self.instance  # the update target, or None

        self._check_not_too_close_to_execution_time(draft)
        strategy = attrs.get("strategy") or draft.strategy
        rule = STRATEGY_RULES[strategy]
        self._apply_strategy(attrs, draft, strategy, rule)

        attrs["side"] = attrs.get("side") or draft.execution_draft.side
        ticker = attrs.get("ticker") or draft.ticker
        self._resolve_price(attrs, ticker, rule, draft)
        self._calculate_volume(attrs, ticker, draft)

        customer = attrs.get("customer") or draft.customer
        self._check_execution_time_for_customer(attrs, customer)
        self._clean_volume_threshold(attrs, customer)
        self._default_assignee(attrs)
        attrs["user"] = self.context["request"].user
        return attrs

    def _apply_strategy(
        self,
        attrs: dict[str, Any],
        draft: ParentDraft | None,
        strategy: str,
        rule: StrategyRule,
    ) -> None:
        if draft is None:  # create: the strategy's own fields
            missing = [name for name in rule.required if attrs.get(name) is None]
            if missing:
                raise ValidationError(
                    {name: ["This field is required."] for name in missing}
                )
            if rule.sized_by_value and not (("value" in attrs) ^ ("volume" in attrs)):
                raise ValidationError({"detail": VOLUME_VALUE_ERROR_MSG})
            for name, default in rule.defaults.items():
                attrs.setdefault(name, default)
        elif "strategy" in attrs:  # update to another strategy: unchanged helper
            BaseDraftSerializer.fill_strategy_null_value_with_defaults(
                attrs, draft, strategy
            )
        for name in STRATEGY_PARAMETERS - rule.fields:
            attrs.pop(name, None)
        if "target_percent" in attrs:  # PVOL sends percent, stores a fraction
            attrs["target_percent"] /= 100

    def _resolve_price(
        self,
        attrs: dict[str, Any],
        ticker: Ticker,
        rule: StrategyRule,
        draft: ParentDraft | None,
    ) -> None:
        price = attrs.get("price")
        if price is None:
            return
        parameter = price if is_parametric(price) else None
        use_parameter = attrs.get("use_price_parameter")
        if use_parameter is None and draft is not None:
            use_parameter = draft.execution_draft.use_price_parameter
        nav = parameter is not None and parameter.lower().startswith("nav")
        if nav and not (rule.nav_prices and use_parameter):
            message = PRICE_PARAMETER_VALIDATION_ERROR_MSG_FORMAT.format(parameter)
            raise ValidationError({"use_price_parameter": message})
        attrs["price_parameter"] = parameter

        if parameter:
            # Was a second quote fetch after validation; now this row's quote.
            quote = self.cached("live_price")
            item = {"price": price, "ticker": ticker, "side": attrs["side"]}
            try:
                LivePriceCalculator(
                    item, {ticker.isin: quote} if quote else {}
                ).set_price()
            except ServiceError as exc:
                raise ValidationError(exc.data) from exc
            price = item["price"]

        tick = (self.cached("ticker_data") or {}).get("minimum_dealable_price", 1)
        attrs["price"] = round_price_by_tick_size(price, attrs["side"], tick)

    def _calculate_volume(
        self, attrs: dict[str, Any], ticker: Ticker, draft: ParentDraft | None
    ) -> None:
        value = attrs.get("value")
        if value is None and draft is not None:
            value = draft.execution_draft.value
        if value is None or not ({"value", "price"} & attrs.keys()):
            return
        if draft is None and "price" not in attrs:
            return  # sized by value, priced later (AUTOMATIC)
        price = attrs.get("price") or draft.execution_draft.price
        # The service reads commissions from a cache_db-shaped context: give
        # it this row's commission (fetched only for rows sized by value).
        context = {
            "cache_db": {"commission_map": {ticker.isin: self.cached("commission")}}
        }
        attrs["volume"] = DraftVolumeCalculatorService(context).calculate(
            value, attrs["side"], price, ticker.isin
        )

    def _check_not_too_close_to_execution_time(self, draft: ParentDraft | None) -> None:
        if draft is None or draft.execution_time is None:
            return
        now = timezone.now()
        if now < draft.execution_time < now + timedelta(minutes=3):
            raise ValidationError(UPDATE_OR_EDIT_DRAFT_BEFORE_THREE_MINUTES_ERROR_MSG)

    def _check_execution_time_for_customer(
        self, attrs: dict[str, Any], customer: Any
    ) -> None:
        if (
            attrs.get("execution_time") is None
            or self.context["request"].user.is_superuser
        ):
            return
        if not CustomerTypeService.can_set_execution_time(customer):
            message = DRAFT_EXECUTION_TIME_NOT_ALLOWED_FOR_CUSTOMER_ERROR_MSG
            raise ValidationError({"execution_time": message})

    def _clean_volume_threshold(self, attrs: dict[str, Any], customer: Any) -> None:
        # Only market-maker customers may switch the threshold off. (The
        # original only ran for a truthy value, so it never changed anything:
        # see README "Found while porting".)
        if attrs.get(
            "volume_threshold"
        ) is False and not CustomerTypeService.is_mofid_mm_found(customer):
            attrs["volume_threshold"] = True

    def _default_assignee(self, attrs: dict[str, Any]) -> None:
        traders = self.collected.get("assignee_candidates", {}).get("traders")
        if attrs.get("assignee") or not traders:
            return
        # One shuffled round-robin per request, shared by every row.
        context = self.context
        if "_assignee_cycle" not in context:
            context["_assignee_cycle"] = itertools.cycle(
                random.sample(traders, len(traders))
            )
        attrs["assignee"] = next(context["_assignee_cycle"])
