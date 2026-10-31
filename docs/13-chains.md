# 13. Chains

A shipment's rate depends on its destination's **region** and its **weight
band**. The band is computed from the weight; the region is only known from
the `Country` row. That gives two kinds of dependency: a **key** built from
another field's key (`derived_from`, no waiting) and a fetch that reads
another fetch's **results** (`depends_on`).

| | |
|---|---|
| Domain | `logistics` |
| Options | `derived_from` naming a batch field, `key=`, `depends_on=` |
| Run | `uv run python examples/run.py chains` |

## Code

```python title="examples/logistics/services.py"
--8<-- "examples/logistics/services.py:rates"
```

```python title="examples/logistics/serializers.py"
--8<-- "examples/logistics/serializers.py:shipment"

--8<-- "examples/logistics/serializers.py:rated"
```

## Requests

### `POST`: three destinations and weights

```python
--8<-- "examples/scenarios/s13_chains.py:post"
```

### `PATCH`: the weight sent, the country stored

```python
--8<-- "examples/scenarios/s13_chains.py:patch"
```

## What to notice

The keys are resolved first, in dependency order, before anything is fetched:

```
country_code ──► country  (key "US")
weight_kg ─────► band     (key "1-5kg", via key=weight_band)
country_code, band ──► rate (key ("US", "1-5kg"))
```

Then the fetches run as a graph:

```
country (DB) ──┐
band (service) │   band and country start together
               └──► rate (service, depends_on country: needs .region)
```

- `derived_from=("country_code", "band")` uses `band`'s **key**, so `rate`
  never waits for the surcharge service.
- `depends_on=("country",)` is needed only because `fetch_rates` reads the
  `Country` rows. The `select_related("region")` on that field's queryset
  keeps it to one query.
- A cycle in either `derived_from` or `depends_on` is an
  `ImproperlyConfigured` when the serializer is built.
