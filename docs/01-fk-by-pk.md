# 1. FK by primary key

A library imports books in bulk. Each row names its author by primary key, a
UUID here. A `CachedRelatedField` with **no options** resolves every author in
the batch with one query.

| | |
|---|---|
| Domain | `library` |
| Options | none (the defaults) |
| Run | `uv run python examples/run.py fk-by-pk` |

## Code

```python title="examples/library/models.py"
--8<-- "examples/library/models.py:models"
```

```python title="examples/library/serializers.py"
--8<-- "examples/library/serializers.py:serializer"
```

```python title="examples/library/views.py"
--8<-- "examples/library/views.py:view"
```

## Requests

### `POST`: two authors, one query

```python
--8<-- "examples/scenarios/s01_fk_by_pk.py:post"
```

### `POST`: an unknown author

```python
--8<-- "examples/scenarios/s01_fk_by_pk.py:miss"
```

### `POST`: not a UUID at all

```python
--8<-- "examples/scenarios/s01_fk_by_pk.py:malformed"
```

### `PATCH`: the author is left out

```python
--8<-- "examples/scenarios/s01_fk_by_pk.py:patch"
```

### `DELETE`

```python
--8<-- "examples/scenarios/s01_fk_by_pk.py:delete"
```

## What to notice

- The model comes from the `Book.author` ForeignKey, and the lookup defaults to
  its primary key.
- Row values are **coerced** to the pk's type: an upper-case UUID string
  resolves the same author. A value that cannot be coerced is a 400 before
  anything is fetched.
- Errors are **index-aligned**: one entry per row, `{}` for rows without
  errors. Any error writes nothing.
- A `PATCH` that leaves `author` out never looks it up. Nothing else reads it
  (compare [composite keys](10-composite-keys.md), where another field does).
