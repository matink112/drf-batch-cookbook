# 16. PUT: full replace

`PUT` validates **full** rows: required fields must be sent, unlike `PATCH`.
It is off unless `batch_actions` lists `"replace"`. Optional fields a `PUT` row
leaves out keep their stored values, and a service field among them is still
checked against the stored value.

| | |
|---|---|
| Domain | `saas` |
| Options | `batch_actions=(..., "replace", ...)`, an optional writable `CachedServiceField` |
| Run | `uv run python examples/run.py put-replace` |

## Code

```python title="examples/saas/serializers.py"
--8<-- "examples/saas/serializers.py:project"
```

```python title="examples/saas/views.py"
--8<-- "examples/saas/views.py:projects"
```

## Requests

### `PUT`: a required field missing

```python
--8<-- "examples/scenarios/s16_put_replace.py:put_required"
```

### `PUT`: an optional field left out keeps (and re-checks) its stored value

```python
--8<-- "examples/scenarios/s16_put_replace.py:put"
```

### `PUT`: a closed cost center sent

```python
--8<-- "examples/scenarios/s16_put_replace.py:put_closed"
```

## What to notice

- `PUT` maps to `batch_replace` (`self.action == "batch_replace"`), so
  permissions and throttles can treat it apart from `PATCH`.
- The stored-key rule is the same for `PUT` and `PATCH`: a writable cached
  field the row leaves out is keyed by its stored value.
- `perform_batch_replace()` defaults to `perform_batch_update()`.
