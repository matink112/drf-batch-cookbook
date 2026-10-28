# Real world: `command`'s execution-draft endpoint on drf-batch

drf-batch grew out of `command` (the EMS order service). This folder is a
**port sketch** of its busiest batch endpoint, `DraftViewSet` (execution
drafts: `POST` / `PATCH` / `PUT` / `DELETE`, Excel upload, bulk re-price), to
show what the serializer and view look like on drf-batch.

- `fields.py`: the cached fields and fetches (was `get_db_filter`,
  `collect_execution_draft_cache_db`, `Batch*SerializerMixin`)
- `serializers.py`: one `BatchSerializer` (was the strategy dispatcher, seven
  strategy serializers, `DraftListSerializer` and five mixins)
- `views.py`: the viewset (was `CreateBatchMixin`, `UpdateBatchMixin`,
  `DestroyBatchMixin`, `ImportDataFromFileMixin` and their hooks)

The files import `command`'s modules (`src.apps...`) as if they lived in that
repository. They are **not run** here: they pass ruff and Python's parser,
nothing more. Treat them as a design to review, not a drop-in patch.

## What changes

| `command` today | On drf-batch |
|---|---|
| `get_db_filter`: ~120 lines building five lookup sets, with branches for JSON, Excel and PATCH (`instances[id].ticker.isin`) | Each field declares its key: sent, `derived_from`, or stored. PATCH fallbacks are automatic. |
| `collect_execution_draft_cache_db` + `asyncio.run_coroutine_threadsafe(..., thread_safe_loop)` | The fields' fetches run as one dependency graph on drf-batch's loop, with `COLLECT_TIMEOUT`. |
| `ticker_map`, `customer_map`, `assignee_map` + `validate_<field>` mixins | `TickerField`, `CustomerField`, `AssigneeField` (`CachedRelatedField` subclasses). |
| `prices_map` only for tickers with a parametric price | `live_price`: `derived_from=("ticker", "price")` + `key=live_price_key`. |
| `commission_map` only for rows sized by value (sent **or stored**) | `commission`: `derived_from=("ticker", "value")`. `value` is read from `execution_draft.value` on PATCH. |
| `get_draft_*_for_cache_db` awaiting `ticker_map_task` for ISINs | `depends_on=("ticker",)`. |
| `save_additional_customers` patching `cache_db` in `to_internal_value` | Inside `CustomerField.fetch`: once, before the rows are validated. |
| `assignee_trader_candidates_generator` in `cache_db` | `assignee_candidates`, a service field with no keys (it still runs). |
| `LivePriceCalculatorListSerializerMixin` fetching quotes **again** after validation | Gone: `self.cached("live_price")` in `validate()`. |
| `CheckConflictListSerializerMixin` (`reference_id`) | The 409 conflict pass, from the model's `unique=True`. |
| `upload` with its own pandas key extraction | File → rows → the same pipeline (`_run`). |
| `update-price/batch` building a cache from instances | Rows `{"id", "price"}` → the same pipeline. |

## Behaviour changes to decide on

- **Out-of-scope or unknown ids** are a **404** for that row (drf-batch's
  target pass), instead of a 400 `OBJECT_NOT_FOUND_OR_PERMISSION_DENIED_MSG`.
- **DELETE rules** (3-minute window, dead-end states) move into
  `check_batch_object_permissions`, so they are a **403** per row (was 400).
- **Validation order**: 400 (malformed) → 404 → 403 → 400 (rows) → 409, and
  no service is called for a request that fails 404/403.
- **Unknown fields for a strategy** are dropped, as before, but via
  `STRATEGY_RULES.fields` rather than per-strategy field declarations.
- **The PATCH response** counts what `bulk_update` reports, as before.

## Gaps in drf-batch this port exposed

In priority order: each one forced a workaround above.

1. **No polymorphic rows.** Rows choose a serializer by `strategy`. drf-batch
   validates every row with one child, so the seven strategy serializers
   collapse into `STRATEGY_RULES` + `validate()`. A
   `get_row_serializer(row)` / registry hook on `BatchSerializer` (sharing
   the collected maps) would keep per-strategy classes.
2. **No custom bulk writer.** A draft is two tables (`ParentDraft` +
   `ExecutionDraft`). drf-batch's bulk writer is flat-fields-only, and its
   per-row mode is one `create()` per row. So `perform_batch_*` write
   directly, which bypasses drf-batch's retry policy, `IntegrityError` → 409
   mapping and `select_for_update` (tenacity is kept for deadlocks). A
   pluggable `batch_writer_class` (or a public `BatchWriter` base) would fix
   it.
3. **No public `(target, validated row)` pairs.** A custom update writer
   needs them; `perform_batch_update` re-fetches the targets by the request
   ids (one extra query, no lock). Exposing the resolved targets (for example
   `serializer.targets`) would remove it.
4. **No per-target validation for DELETE.** Rules that are not permissions
   (the 3-minute window) have to be raised as 403s.

## Found while porting (in `command`)

- `PlainStrategySerializer.clean_volume_threshold` only runs for a truthy
  value, so `False` is never reset to `True` for non-market-maker customers:
  it never changes anything. `serializers.py` implements the evident intent;
  check which one is right.
- `get_db_filter` swallows every exception and returns empty lookups, so a
  malformed row can surface as "ticker not found" instead of its real error.
  drf-batch reports malformed keys as their own 400 before any fetch.
- `DraftViewSet.delete` (the `POST .../delete/` action) shadows the
  `delete` HTTP handler name. It is `delete_via_post` here.

## Next steps

- `ExecutionViewSet` (parent orders: create, credit create, update) has the
  same shape: the `ticker_map` / `customer_map` / `prices_map` /
  `stats_map` (VWAP) / credit maps become fields, and `get_lookups` goes.
- The send / auto-send / preview actions work on stored drafts by id, with
  `ObjectExtractorListSerializer`. They are not batch writes of rows; leave
  them, or model them as `PATCH` rows if they should share the pipeline.
