# 2. FK by natural key

Order rows reference tickers and customers by their ISIN, the identifier
clients actually know, not by database ids. `lookup=` picks the column to
match, and `error=` words the miss.

| | |
|---|---|
| Domain | `trading` |
| Options | `lookup="isin"`, `error=` |
| Run | `uv run python examples/run.py fk-by-natural-key` |

## Code

```python title="examples/trading/models.py"
--8<-- "examples/trading/models.py:models"
```

```python title="examples/trading/serializers.py"
--8<-- "examples/trading/serializers.py:order"
```

```python title="examples/trading/views.py"
--8<-- "examples/trading/views.py:order"
```

## Requests

### `POST`: ISINs, one of them a number

```python
--8<-- "examples/scenarios/s02_fk_by_natural_key.py:post"
```

### `POST`: misses, with the custom messages

```python
--8<-- "examples/scenarios/s02_fk_by_natural_key.py:miss"
```

### `POST`: a malformed key

```python
--8<-- "examples/scenarios/s02_fk_by_natural_key.py:malformed"
```

## What to notice

- The model is still derived from the ForeignKey; `lookup="isin"` only
  changes the column. `validated_data["ticker"]` is the `Ticker` instance, so
  `create()` and the bulk insert work unchanged.
- `1102` (a number) becomes `"1102"` because `isin` is a `CharField`. A list
  is rejected: `expected a string, got list`.
- `{value}` in `error=` is the **coerced** key.
- The read path renders the ISIN back (`"ticker": "1101"`), so the same
  serializer works for `list` and `retrieve`.
