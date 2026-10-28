# 14. Fetch order

Before an order is accepted, five lookups run: two database queries (tickers,
customers), the listing service (needs the ticker rows), the KYC service
(needs only the customer keys), and a second database query restricted to
tickers the listing service put in band A. `depends_on` turns them into a
graph: service-after-DB and DB-after-service in one serializer.

| | |
|---|---|
| Domain | `trading` |
| Options | `depends_on=` both ways, a `fetch()` override on a related field, `batch_concurrent_collection` |
| Run | `uv run python examples/run.py fetch-order` |

## Code

```python title="examples/trading/services.py"
--8<-- "examples/trading/services.py:kyc"
```

```python title="examples/trading/serializers.py"
--8<-- "examples/trading/serializers.py:exchange"
```

```python title="examples/trading/views.py"
--8<-- "examples/trading/views.py:exchange"
```

## The graph

```
ticker (DB) ───► band (service) ───► primary_listing (DB, band "A" only)
customer (DB)
kyc (service, keys only: starts at once)
```

`ticker`, `customer` and `kyc` start together; `band` starts when `ticker` is
done; `primary_listing` when `band` is done. ([Concurrency and
`depends_on`](https://matink112.github.io/drf-batch/guide/collection/#concurrency-and-depends_on) has the
details.)

## Requests

### `POST`: one customer is not verified

```python
--8<-- "examples/scenarios/s14_fetch_order.py:post"
```

### `POST`: the same graph, one fetch at a time

```python
--8<-- "examples/scenarios/s14_fetch_order.py:sequential"
```

## What to notice

- `kyc` and `primary_listing` both key off other fields (`derived_from`),
  but only `primary_listing` reads another **result**, so only it has
  `depends_on`.
- A related field can override `fetch()`; keep `self.get_queryset()` in it so
  scoping still applies.
- `batch_concurrent_collection = False` runs the plan in order on the request
  thread: dependencies first, then declaration order. The result is the same.
