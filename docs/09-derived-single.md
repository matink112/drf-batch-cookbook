# 9. Derived from one field

The exchange's listing service bands every ticker: band `B` is suspended, and
an unlisted ticker cannot be traded. The check must hold for **every** write:
on `POST` for the ticker sent, and on a `PATCH` that only changes the volume,
for the ticker **stored** on the order.

| | |
|---|---|
| Domain | `trading` |
| Options | `read_only=True`, `derived_from="ticker"`, `depends_on=("ticker",)`, `self.fetched()` |
| Run | `uv run python examples/run.py derived-single` |

## Code

```python title="examples/trading/services.py"
--8<-- "examples/trading/services.py:bands"
```

```python title="examples/trading/serializers.py"
--8<-- "examples/trading/serializers.py:listed"
```

## Requests

### `POST`: an unlisted and a suspended ticker

```python
--8<-- "examples/scenarios/s09_derived_single.py:post"
```

### `PATCH`: no ticker in the rows

```python
--8<-- "examples/scenarios/s09_derived_single.py:patch"
```

### `PATCH`: claiming a band does nothing

```python
--8<-- "examples/scenarios/s09_derived_single.py:body_ignored"
```

## What to notice

- `derived_from="ticker"` gives `band` the row's ticker key: the ISIN sent,
  or the stored ticker's ISIN on a `PATCH` that leaves it out. The target
  query joins the ticker for it; there are no per-row queries.
- `depends_on=("ticker",)` is there because `fetch_bands` reads the **ticker
  rows** (their names). Because `band` reads `ticker`, the ticker lookup also
  covers the stored tickers.
- `self.fetched("band")` is this row's band. `attrs["ticker"]` would be a
  `KeyError` on a `PATCH` that leaves the ticker out.
- `read_only=True`: a `band` in the row is ignored. Clients cannot vouch for
  their own band.
