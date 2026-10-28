# drf-batch cookbook

Runnable scenarios for [drf-batch](https://github.com/matink112/drf-batch):
19 scenarios across six small domains, each focused on one or two
cached-field options, with a docs page per scenario.

```bash
uv sync
uv run python examples/run.py                    # every scenario
uv run python examples/run.py composite-keys 14  # by slug or number
uv run --group docs mkdocs serve                 # the pages
```

## How it works

`examples/` is a Django project. Each scenario in `examples/scenarios/` starts
from an empty database: `seed()` creates its rows, then `walk()` sends real
`POST` / `PATCH` / `PUT` / `DELETE` batches through DRF's `APIClient` and
asserts every response. The pages in `docs/` embed those exact blocks (the
`# --8<-- [start:name]` markers), so a page cannot show a response the code
does not produce. `mkdocs build --strict` fails on a missing block.

| App | Domain | Scenarios |
|---|---|---|
| `library` | books and authors (UUID pks) | 1 |
| `trading` | orders, tickers, customers | 2, 9, 14, 17, 18 |
| `shop` | stock reservations, coupons | 6, 7, 10, 19 |
| `ledger` | currency transfers, expenses | 4, 11, 15 |
| `saas` | workspaces, projects, subscriptions | 3, 12, 16 |
| `logistics` | shipments, countries, carriers | 5, 8, 13 |

External systems (listing, KYC, coupons, stock, treasury, carriers, ...) are
faked in each app's `services.py` with plain dicts, so everything runs
offline. Requests run in a transaction (`ATOMIC_REQUESTS = True`), except the
retry example, which opts out.

## Real world

[`real-world/command/`](real-world/command/) ports the execution-draft batch
endpoint of `command` (the EMS order service drf-batch grew out of) to
drf-batch: the serializer and view, plus a review of what changes and which
drf-batch gaps it exposed. It is a design sketch, not run here.

## drf-batch version

The scenarios use features that are not released yet (`derived_from`, `key=`,
`BatchSerializer.cached`), so `pyproject.toml` installs drf-batch from the
sibling checkout `../drf-batch`. Point `[tool.uv.sources]` at a release (or a
git URL) once they are published.

## Checks

```bash
uv run ruff check && uv run ruff format --check
uv run python examples/run.py
uv run --group docs mkdocs build --strict
```
