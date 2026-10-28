# 7. Custom keys

Shop staff type SKUs by hand: `" ab_1 "`, `"Ab-1"`. Normalising them in
`validate_product()` is too late, because the lookup has already missed. A
field subclass overriding `prepare_key()` normalises the key **before**
collection, so every spelling resolves the same product with one query.

| | |
|---|---|
| Domain | `shop` |
| Options | a `CachedRelatedField` subclass with `prepare_key()`; `error=` |
| Run | `uv run python examples/run.py custom-keys` |

## Code

```python title="examples/shop/serializers.py"
--8<-- "examples/shop/serializers.py:sku"
```

## Requests

### `POST`: two spellings of one SKU

```python
--8<-- "examples/scenarios/s07_custom_keys.py:post"
```

### `POST`: a miss reports the normalised key

```python
--8<-- "examples/scenarios/s07_custom_keys.py:miss"
```

### `POST`: a malformed key never reaches the database

```python
--8<-- "examples/scenarios/s07_custom_keys.py:malformed"
```

## What to notice

- `prepare_key()` must be **idempotent**: it can run on a value it already
  normalised (stored keys go through it too).
- Calling `super().prepare_key()` keeps the built-in coercion and its 400 for
  lists, dicts and booleans, raised before any fetch.
- The same hook exists on `CachedServiceField`, whose default
  `prepare_key()` is the identity.
