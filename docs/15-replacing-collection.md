# 15. Replacing collection

The treasury system answers currencies **and** exchange rates in one RPC, and
one call per batch beats one per field. `batch_collector_class` replaces auto
collection: the collector receives every map's key set (derived and stored
keys included) and returns every map.

| | |
|---|---|
| Domain | `ledger` |
| Options | `batch_collector_class`, `derived_from=("from_currency", "to_currency")` |
| Run | `uv run python examples/run.py replacing-collection` |

## Code

```python title="examples/ledger/services.py"
--8<-- "examples/ledger/services.py:rates"
```

```python title="examples/ledger/serializers.py"
--8<-- "examples/ledger/serializers.py:rated"
```

```python title="examples/ledger/collectors.py"
--8<-- "examples/ledger/collectors.py:collector"
```

```python title="examples/ledger/views.py"
--8<-- "examples/ledger/views.py:view"
```

## Requests

### `POST`: one call answers everything

```python
--8<-- "examples/scenarios/s15_replacing_collection.py:post"
```

### `PATCH`: the stored pair reaches the collector

```python
--8<-- "examples/scenarios/s15_replacing_collection.py:patch"
```

## What to notice

- The collector must return **every** map the fields read (`currency`,
  `rate`). A missing map means every row misses.
- Keys arrive coerced and complete: row keys, derived keys and stored keys,
  so the collector never parses rows.
- The fields' own `fetch=` callables are not called while a collector is set.
- `collect` may be `async def`; use `self.run_sync(...)` for the ORM there.
