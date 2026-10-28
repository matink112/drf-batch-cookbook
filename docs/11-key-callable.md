# 11. Keys built by a callable

Accounting closes the books month by month. An expense in a closed month may
not be created or changed, including a `PATCH` that only fixes the amount. The
accounting system answers per **period** (`"2026-09"`), not per date: `key=`
turns the date into the period.

| | |
|---|---|
| Domain | `ledger` |
| Options | `derived_from="booked_on"` (a plain field), `key=` |
| Run | `uv run python examples/run.py key-callable` |

## Code

```python title="examples/ledger/models.py"
--8<-- "examples/ledger/models.py:expense"
```

```python title="examples/ledger/services.py"
--8<-- "examples/ledger/services.py:periods"
```

```python title="examples/ledger/serializers.py"
--8<-- "examples/ledger/serializers.py:expense"
```

## Requests

### `POST`: an open and a closed month

```python
--8<-- "examples/scenarios/s11_key_callable.py:post"
```

### `PATCH`: the stored date decides, unless a new one is sent

```python
--8<-- "examples/scenarios/s11_key_callable.py:patch"
```

### `POST`: an invalid date

```python
--8<-- "examples/scenarios/s11_key_callable.py:invalid"
```

## What to notice

- For a plain serializer field, the value handed to `key=` is the field's
  `to_internal_value()` (a `date`, not the string), or the stored value on an
  update. The types match either way.
- An invalid value reaches `key=` as `None` (so no key), and the field
  reports its own error during validation.
- `key=` receives `None` values too: return `None` for "no key".
- Two expenses in one month share one key: the service is asked once per
  period, not per row.
