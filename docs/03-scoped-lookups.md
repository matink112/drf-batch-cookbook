# 3. Scoped lookups

In a multi-tenant SaaS, a client must not attach a project to a workspace they
do not belong to, and a workspace being archived must stop new projects.
`get_queryset()` on the field limits what a lookup may resolve to, per
request. The view's own `get_queryset()` limits which projects a batch may
touch.

| | |
|---|---|
| Domain | `saas` |
| Options | field `get_queryset()` (or `queryset=`), view `get_queryset()` |
| Run | `uv run python examples/run.py scoped-lookups` |

## Code

```python title="examples/saas/models.py"
--8<-- "examples/saas/models.py:models"
```

```python title="examples/saas/serializers.py"
--8<-- "examples/saas/serializers.py:workspace"

--8<-- "examples/saas/serializers.py:project"
```

```python title="examples/saas/views.py"
--8<-- "examples/saas/views.py:projects"
```

## Requests

### `POST`: someone else's workspace, an archived one

```python
--8<-- "examples/scenarios/s03_scoped_lookups.py:post"
```

### `PATCH`: someone else's project

```python
--8<-- "examples/scenarios/s03_scoped_lookups.py:patch"
```

## What to notice

- A workspace outside the field's queryset is an ordinary **miss** (400): the
  client cannot tell "not yours" from "does not exist".
- `self.context["request"]` is available in `get_queryset()`, as in DRF's
  `RelatedField`. For a fixed rule, pass `queryset=` instead, for example
  `BatchRelatedField(queryset=Workspace.objects.filter(archived=False))`.
- Update/delete **targets** come from the view's `get_queryset()`, so another
  tenant's project is a **404**, never validated.
