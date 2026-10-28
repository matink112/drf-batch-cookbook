# 18. Cross-row conflicts

Two rows of one batch may collide with each other, or with stored rows, on a
unique rule. The conflict pass reports both as **409**, index-aligned, before
anything is written. The rules come from the model (`unique`,
`UniqueConstraint`) and from `Meta.batch_unique_together`.

| | |
|---|---|
| Domain | `trading` |
| Options | `Meta.batch_unique_together`, model constraints, `batch_conflict_status` |
| Run | `uv run python examples/run.py conflicts` |

## Code

```python title="examples/trading/serializers.py"
--8<-- "examples/trading/serializers.py:unique"
```

```python title="examples/trading/views.py"
--8<-- "examples/trading/views.py:unique"
```

## Requests

### `POST`: two rows share a reference

```python
--8<-- "examples/scenarios/s18_conflicts.py:in_batch"
```

### `POST`: clashes with stored rows

```python
--8<-- "examples/scenarios/s18_conflicts.py:existing"
```

### `PATCH`: a row never conflicts with itself

```python
--8<-- "examples/scenarios/s18_conflicts.py:update"
```

## What to notice

- The model's `UniqueConstraint(ticker, customer)` is enforced without
  declaring anything; `batch_unique_together` adds rules the database does
  not have.
- One query per rule checks the whole batch against stored rows.
- Set `batch_conflict_status = 422` on the view if your API reports
  conflicts as validation errors. See [Cross-row conflicts](https://matink112.github.io/drf-batch/guide/conflicts/).
