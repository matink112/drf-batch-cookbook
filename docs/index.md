# drf-batch cookbook

Nineteen scenarios for [drf-batch](https://matink112.github.io/drf-batch/) across six small domains. Each one shows a cached-field
option (or two) doing a real job, with the code and the `POST` / `PATCH` /
`PUT` / `DELETE` batches it handles. Everything on these pages is embedded
from the runnable `examples/` project in this repository, whose walkthroughs
assert every response shown here:

```bash
uv run python examples/run.py                  # all scenarios
uv run python examples/run.py composite-keys   # one, by slug or number
```

## Where a key comes from

Every row gets a key for every cached field before anything is fetched:

| Field | Row sends it | Row omits it, `POST` | Row omits it, `PATCH` / `PUT` |
|---|---|---|---|
| writable | the row's value ([2](02-fk-by-natural-key.md), [6](06-writable-service.md)) | `derived_from`, else no key | `derived_from`, else the stored value ([6](06-writable-service.md), [16](16-put-replace.md)) |
| `read_only` | **ignored** ([9](09-derived-single.md)) | `derived_from`, else no key | `derived_from`, else the stored value |

Only a value the row **sent** can be a "not found" error. A derived or stored
key the fetch does not return is for `validate()` to judge, through
`self.cached(name)`.

## Which page shows what

**Field options**

| Option | What it does | Pages |
|---|---|---|
| *(none)* | FK by primary key; model from the ForeignKey | [1](01-fk-by-pk.md) |
| `lookup=` | match another column (`isin`, `sku`, `code`) | [2](02-fk-by-natural-key.md), [4](04-shared-map.md), [7](07-custom-keys.md), [10](10-composite-keys.md) |
| `error=` | the miss message | [2](02-fk-by-natural-key.md), [4](04-shared-map.md), [6](06-writable-service.md), [7](07-custom-keys.md) |
| `queryset=` / `get_queryset()` | the rows a lookup may resolve to | [3](03-scoped-lookups.md), [5](05-non-fk-lookup.md) |
| `model=` / `queryset=` without a ForeignKey | a lookup for a plain column | [5](05-non-fk-lookup.md), [14](14-fetch-order.md) |
| `map=` | two fields share one fetch | [4](04-shared-map.md) |
| `fetch=` (sync) | a service field | [6](06-writable-service.md), [9](09-derived-single.md), [11](11-key-callable.md) |
| `async def` fetch | concurrent remote calls | [8](08-async-services.md) |
| `fetch()` override | a field class with its own fetch | [10](10-composite-keys.md), [14](14-fetch-order.md) |
| `prepare_key()` override | normalise or reject row values | [7](07-custom-keys.md) |
| `read_only=True` | never read the row | [5](05-non-fk-lookup.md), [9](09-derived-single.md), [12](12-hidden-columns.md) |
| `derived_from="name"` | key from another field, sent or stored | [5](05-non-fk-lookup.md), [9](09-derived-single.md), [12](12-hidden-columns.md) |
| `derived_from=("a", "b")` | a composite key | [10](10-composite-keys.md), [8](08-async-services.md), [15](15-replacing-collection.md) |
| `key=` | build the key with a function | [11](11-key-callable.md), [13](13-chains.md) |
| derived from a derived field | chains | [13](13-chains.md) |
| `depends_on=` | wait for another fetch's results | [9](09-derived-single.md), [13](13-chains.md), [14](14-fetch-order.md) |
| stored keys (automatic) | `PATCH`/`PUT` rows that omit a field | [6](06-writable-service.md), [9](09-derived-single.md), [10](10-composite-keys.md), [16](16-put-replace.md) |
| `self.cached(name)` | read a field's result in `validate()` | [5](05-non-fk-lookup.md), [6](06-writable-service.md), [9](09-derived-single.md)–[13](13-chains.md) |

**View options**

| Option | Pages |
|---|---|
| `get_queryset()` (target scoping) | [3](03-scoped-lookups.md), [17](17-delete.md) |
| object permissions | [17](17-delete.md) |
| `batch_actions` (`"replace"` for `PUT`, or fewer actions) | [12](12-hidden-columns.md), [16](16-put-replace.md) |
| `batch_collector_class` | [15](15-replacing-collection.md) |
| `batch_concurrent_collection` | [14](14-fetch-order.md) |
| `COLLECT_TIMEOUT` | [8](08-async-services.md) |
| `batch_unique_together` | [18](18-conflicts.md) |
| `batch_use_bulk`, `batch_retry_policy`, `batch_response` | [19](19-write-options.md) |
| `perform_batch_create` (`save()` kwargs) | [17](17-delete.md) |
