"""Run the Cookbook scenarios.

    python examples/run.py                      # every scenario
    python examples/run.py composite-keys ...   # some, by slug (or number)

Each scenario starts from an empty database: ``seed()`` creates its rows,
then ``walk()`` sends real batch requests and asserts every response.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import time
from pathlib import Path

SCENARIOS = [
    "s01_fk_by_pk",
    "s02_fk_by_natural_key",
    "s03_scoped_lookups",
    "s04_shared_map",
    "s05_non_fk_lookup",
    "s06_writable_service",
    "s07_custom_keys",
    "s08_async_services",
    "s09_derived_single",
    "s10_composite_keys",
    "s11_key_callable",
    "s12_hidden_columns",
    "s13_chains",
    "s14_fetch_order",
    "s15_replacing_collection",
    "s16_put_replace",
    "s17_delete",
    "s18_conflicts",
    "s19_write_options",
]


def slug(module: str) -> str:
    """``s10_composite_keys`` -> ``composite-keys``."""
    return module.split("_", 1)[1].replace("_", "-")


def select(args: list[str]) -> list[str]:
    if not args:
        return SCENARIOS
    chosen = []
    for arg in args:
        matches = [
            m for m in SCENARIOS if arg in (slug(m), m, m[1:3], m[1:3].lstrip("0"))
        ]
        if not matches:
            known = ", ".join(slug(m) for m in SCENARIOS)
            raise SystemExit(f"unknown scenario {arg!r}; known: {known}")
        chosen.extend(matches)
    return chosen


def main(args: list[str]) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    workdir = tempfile.mkdtemp(prefix="drf-batch-examples-")
    os.environ["DRF_BATCH_EXAMPLES_DB"] = str(Path(workdir) / "examples.sqlite3")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    import django

    django.setup()

    from django.core.management import call_command

    call_command("migrate", run_syncdb=True, verbosity=0)
    for module_name in select(args):
        call_command("flush", interactive=False, verbosity=0)
        module = importlib.import_module(f"scenarios.{module_name}")
        started = time.perf_counter()
        seed = getattr(module, "seed", None)
        if seed is not None:
            seed()
        module.walk()
        elapsed = time.perf_counter() - started
        print(f"ok  {module_name[1:3]} {slug(module_name):<22} {elapsed:6.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
