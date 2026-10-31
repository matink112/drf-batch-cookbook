# 12. Hidden model columns

Subscriptions are created by billing; clients may only change `seats`, up to
their plan's limit. `plan_code` must not be on the serializer (clients cannot
change it), yet the limit depends on it. `derived_from` may name a **model
column that is not on the serializer**: its value comes from the stored row.

| | |
|---|---|
| Domain | `saas` |
| Options | `derived_from="plan_code"` (not a serializer field), `batch_actions=("update",)` |
| Run | `uv run python examples/run.py hidden-columns` |

## Code

```python title="examples/saas/models.py"
--8<-- "examples/saas/models.py:subscription"
```

```python title="examples/saas/serializers.py"
--8<-- "examples/saas/serializers.py:subscription"
```

```python title="examples/saas/views.py"
--8<-- "examples/saas/views.py:subscriptions"
```

## Requests

### `PATCH`: over and within the limit

```python
--8<-- "examples/scenarios/s12_hidden_columns.py:patch"
```

### `PATCH`: a `plan_code` in the row

```python
--8<-- "examples/scenarios/s12_hidden_columns.py:plan_ignored"
```

### `POST`: not enabled

```python
--8<-- "examples/scenarios/s12_hidden_columns.py:post"
```

## What to notice

- A model field that is not on the serializer is read **only** from the stored
  row (`None` on create), so the client cannot influence it.
- Any ForeignKey or OneToOneField column works the same way (its value is the
  related pk).
- A shortcut: a read-only batch field **named after the column** (for
  example `plan_code = BatchServiceField(..., read_only=True)`) gets the
  stored key without `derived_from`, but it also renders the column in
  responses.
