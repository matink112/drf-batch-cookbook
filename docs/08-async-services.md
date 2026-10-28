# 8. Async services and timeouts

Each shipment needs a carrier quote and a customs zone, from two remote APIs
that each take about 300 ms. As `async def` fetches without a dependency
between them, they run **at the same time**, once per batch rather than once
per row. A fetch that needs the ORM goes through `run_sync`, and a carrier that
hangs is cut off by `COLLECT_TIMEOUT`.

| | |
|---|---|
| Domain | `logistics` |
| Options | `async def` fetch, `derived_from=` (a pair), `drf_batch.loop.run_sync`, `COLLECT_TIMEOUT` |
| Run | `uv run python examples/run.py async-services` |

## Code

```python title="examples/logistics/services.py"
--8<-- "examples/logistics/services.py:async"
```

```python title="examples/logistics/serializers.py"
--8<-- "examples/logistics/serializers.py:quoted"
```

## Requests

### `POST`: three rows, two remote calls, in parallel

```python
--8<-- "examples/scenarios/s08_async_services.py:post"
```

### `POST`: no quote for that pair

```python
--8<-- "examples/scenarios/s08_async_services.py:miss"
```

### `POST`: a carrier that hangs

```python
--8<-- "examples/scenarios/s08_async_services.py:timeout"
```

## What to notice

- An `async def` fetch is detected automatically and runs on the event loop.
  A sync fetch would run on a worker thread (or, inside a transaction as here,
  on the request thread).
- Do not call the ORM directly inside an `async def` fetch. `run_sync(...)`
  runs it where it sees the request's transaction (see
  [Async collection](https://matink112.github.io/drf-batch/guide/async/)).
- `COLLECT_TIMEOUT` (seconds, default 10) bounds the whole collection. On
  expiry the batch is a **504** and nothing is written.
