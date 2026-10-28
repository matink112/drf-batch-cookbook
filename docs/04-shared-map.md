# 4. Two fields, one map

A transfer has two ForeignKeys to `Currency`. Declared separately they would
run two queries for overlapping codes. `map="currency"` puts both fields on
one map: every code in the batch, from either field, is fetched once.

| | |
|---|---|
| Domain | `ledger` |
| Options | `map=`, `lookup="code"`, `error=` |
| Run | `uv run python examples/run.py shared-map` |

## Code

```python title="examples/ledger/models.py"
--8<-- "examples/ledger/models.py:models"
```

```python title="examples/ledger/serializers.py"
--8<-- "examples/ledger/serializers.py:transfer"
```

## Requests

### `POST`: three currencies, one query

```python
--8<-- "examples/scenarios/s04_shared_map.py:post"
```

### `POST`: same currency twice, an unknown one

```python
--8<-- "examples/scenarios/s04_shared_map.py:invalid"
```

### `PATCH`: one side sent, the other stored

```python
--8<-- "examples/scenarios/s04_shared_map.py:patch"
```

## What to notice

- Fields that share a map must agree on what the keys mean (here both are
  currency codes on the same model).
- `validate()` compares the sent side with the **stored** side through the FK
  column (`from_currency_id`): no query per row.
- A non-field error lands under `non_field_errors`, still index-aligned.
