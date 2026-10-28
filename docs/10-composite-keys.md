# 10. Composite keys

Stock lives per warehouse **and** product. A reservation may not exceed what
the warehouse system reports for that pair, and a `PATCH` that only raises the
quantity must still be checked against the stored pair. A tuple of names in
`derived_from` makes a composite key, each half sent or stored.

| | |
|---|---|
| Domain | `shop` |
| Options | `derived_from=("warehouse", "product")`, a `CachedServiceField` subclass with `fetch()` |
| Run | `uv run python examples/run.py composite-keys` |

## Code

```python title="examples/shop/serializers.py"
--8<-- "examples/shop/serializers.py:stock"
```

## Requests

### `POST`: one pair in stock, one sold out

```python
--8<-- "examples/scenarios/s10_composite_keys.py:post"
```

### `PATCH`: quantity only, the pair is stored

```python
--8<-- "examples/scenarios/s10_composite_keys.py:patch"
```

### `PATCH`: half sent, half stored

```python
--8<-- "examples/scenarios/s10_composite_keys.py:patch_half"
```

## What to notice

- Each half is the **cached key** of a related field (`"AMS"`, `"AB-1"`), not
  a model instance: keys are known before any fetch, so `available` does not
  wait for the warehouse or product queries.
- Because `available` reads `warehouse` and `product`, an update fetches their
  stored keys. Both use non-pk lookups (`code`, `sku`), so the **target query
  joins them** once; a pk lookup would read the FK column with no join.
- With a single name, `derived_from` passes the value through; with several,
  the key is the tuple. Any `None` half means no key, unless you pass `key=`
  ([next page](11-key-callable.md)).
