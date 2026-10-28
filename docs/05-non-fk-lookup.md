# 5. A lookup for a plain column

Shipments store a two-letter `country_code` in a plain `CharField`, not a
ForeignKey, yet every code must exist in the `Country` table, both when a
shipment is created and whenever it changes. A **read-only** related field
keyed by that column (`derived_from`) checks it.

| | |
|---|---|
| Domain | `logistics` |
| Options | `queryset=` (or `model=`), `lookup=`, `read_only=True`, `derived_from=` |
| Run | `uv run python examples/run.py non-fk-lookup` |

## Code

```python title="examples/logistics/models.py"
--8<-- "examples/logistics/models.py:models"
```

```python title="examples/logistics/serializers.py"
--8<-- "examples/logistics/serializers.py:shipment"
```

## Requests

### `POST`: a known and an unknown country

```python
--8<-- "examples/scenarios/s05_non_fk_lookup.py:post"
```

### `POST`: the read-only field in the row

```python
--8<-- "examples/scenarios/s05_non_fk_lookup.py:read_only"
```

### `PATCH`: a stale stored code

```python
--8<-- "examples/scenarios/s05_non_fk_lookup.py:patch"
```

## What to notice

- No ForeignKey named `country` exists, so the field names its model through
  `queryset=` (or `model=`). The `select_related("region")` is reused by
  [chains](13-chains.md).
- `read_only=True`: nothing is written from it, and **the row's value is
  ignored**, so `"country": "nonsense"` changes nothing.
- `derived_from="country_code"` keys the lookup by the column: the sent value
  or, on a `PATCH` that leaves it out, the stored one.
- A derived key that misses is **not** an automatic error (the client did not
  send it). `validate()` checks `self.cached("country")` and words the error
  for the column the client knows.
