# 6. A writable service field

Reservations may carry a coupon code, validated by the marketing system. A sent
code must be active. Coupons also **end**, and a reservation whose stored
coupon has ended must not be changed until the client sends a new one, even by
a `PATCH` that only touches the quantity.

| | |
|---|---|
| Domain | `shop` |
| Options | `CachedServiceField(fetch=, error=)`, writable; stored keys (automatic) |
| Run | `uv run python examples/run.py writable-service` |

## Code

```python title="examples/shop/models.py"
--8<-- "examples/shop/models.py:models"
```

```python title="examples/shop/services.py"
--8<-- "examples/shop/services.py:coupons"
```

```python title="examples/shop/serializers.py"
--8<-- "examples/shop/serializers.py:coupon"
```

## Requests

### `POST`: an active and an ended coupon

```python
--8<-- "examples/scenarios/s06_writable_service.py:post"
```

### `PATCH`: the coupon ends after the reservation was made

```python
--8<-- "examples/scenarios/s06_writable_service.py:patch"
```

## What to notice

- A writable service field writes the **map value** (`{code: code}` here) to
  `validated_data`, like a related field writes the instance.
- A **sent** code that misses gets the field's `error=` (a 400 on that row).
- A `PATCH` that leaves `coupon_code` out still sends the stored code to the
  service: there is no opt-in for that. The service is asked about every row.
- A **stored** code that misses is not an automatic error, so `validate()`
  decides, and can say *which* coupon ended.
