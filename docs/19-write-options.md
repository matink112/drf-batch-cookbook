# 19. Write options

By default a batch is written with `bulk_create` / `bulk_update`: fast, but
model signals and `save()` overrides do not run. When an audit trail lives in
a `post_save` receiver, `batch_use_bulk = False` writes row by row. A retry
policy re-runs the whole write after a transient database error, and
`batch_response = "data"` returns the rows instead of a count.

| | |
|---|---|
| Domain | `shop` |
| Options | `batch_use_bulk`, `batch_retry_policy`, `batch_response`, `non_atomic_requests` |
| Run | `uv run python examples/run.py write-options` |

## Code

```python title="examples/shop/models.py"
--8<-- "examples/shop/models.py:event"
```

```python title="examples/shop/signals.py"
--8<-- "examples/shop/signals.py:audit"
```

```python title="examples/shop/views.py"
--8<-- "examples/shop/views.py:writes"
```

## Requests

### Bulk (the default)

```python
--8<-- "examples/scenarios/s19_write_options.py:bulk"
```

### Per row, after one transient failure

```python
--8<-- "examples/scenarios/s19_write_options.py:per_row"
```

## What to notice

- Each retry attempt is its own transaction, so a failed attempt leaves
  nothing behind (one audit event per row, not two).
- Inside `ATOMIC_REQUESTS` a retry cannot recover: the policy runs the write
  once and warns. Decorate the view with `transaction.non_atomic_requests`
  to retry.
- `IntegrityError` is never retried: it is deterministic, and becomes a 409.
