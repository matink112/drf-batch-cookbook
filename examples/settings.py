"""Settings for the Cookbook examples project (see examples/README.md)."""

from __future__ import annotations

import os

SECRET_KEY = "examples-only-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "urls"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_batch",
    "library",
    "trading",
    "shop",
    "ledger",
    "saas",
    "logistics",
]

# A file database (run.py points it at a temporary file): the async example
# reads it from a worker thread, which a private in-memory SQLite database
# would not allow.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DRF_BATCH_EXAMPLES_DB", "examples.sqlite3"),
        # Every request in one transaction, as many projects run: the sync
        # fetches then run on the request thread and see its writes.
        "ATOMIC_REQUESTS": True,
    }
}

REST_FRAMEWORK = {"TEST_REQUEST_DEFAULT_FORMAT": "json"}

DRF_BATCH = {"BATCH_MAX_SIZE": 500}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The walkthroughs send rejected batches (and a 504) on purpose: keep the
# request log quiet.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {"django.request": {"level": "CRITICAL"}},
}
