# 17. DELETE

`DELETE` rows are bare primary keys. Targets come from the view's
`get_queryset()` (someone else's order is a **404**), every target passes the
object permissions (**403**), a pk listed twice is a **409**, and a database
refusal such as `PROTECT` rolls the whole batch back (**409**). Nothing is
collected: there is no row payload.

| | |
|---|---|
| Domain | `trading` |
| Options | view `get_queryset()`, object permissions, `perform_batch_create` |
| Run | `uv run python examples/run.py delete` |

## Code

```python title="examples/trading/models.py"
--8<-- "examples/trading/models.py:note"
```

```python title="examples/trading/views.py"
--8<-- "examples/trading/views.py:mine"
```

## Requests

### Someone else's order, a missing one

```python
--8<-- "examples/scenarios/s17_delete.py:not_found"
```

### An order the permission refuses

```python
--8<-- "examples/scenarios/s17_delete.py:forbidden"
```

### A pk listed twice

```python
--8<-- "examples/scenarios/s17_delete.py:duplicate"
```

### A protected order

```python
--8<-- "examples/scenarios/s17_delete.py:protected"
```

### Success

```python
--8<-- "examples/scenarios/s17_delete.py:ok"
```

## What to notice

- The checks run in order (404, then 403, then 409), and the first failing
  one answers for the whole batch, index-aligned.
- `perform_batch_create()` passes `owner=` to `save()`, which merges it into
  every created row: the same hook works for update and delete.
- `ProtectedError` is an `IntegrityError`: the write is rolled back and the
  answer is a 409 with a `detail` (error code `batch_integrity_conflict`),
  not a per-row list: the database does not say which row failed.
