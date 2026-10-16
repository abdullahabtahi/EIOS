"""Which warm backend a process uses, from the environment (docs/warm-tier.md).

`EIOS_WARM_BACKEND`: `bigquery` (needs `EIOS_WARM_PROJECT`; the history was loaded beforehand with `python -m eios.warm
load`), `local` (a DuckDB double, loaded from the AML world on first use) or `off`. The default is `local`. A deployed
service that wants the warehouse says so explicitly; a missing project is a start-up error, never a silent fall-back.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Mapping
from typing import Any

from eios.foundry.scenarios.aml_world import AmlWorld
from eios.warm.loader import load_transactions_history
from eios.warm.sink import LocalWarmSink
from eios.warm.store import (
    DEFAULT_MAX_BYTES,
    BigQueryWarmStore,
    LocalWarmStore,
    WarmResult,
    WarmStore,
)

_LOG = logging.getLogger("eios.warm.config")
BACKEND_ENV = "EIOS_WARM_BACKEND"
PROJECT_ENV = "EIOS_WARM_PROJECT"
MAX_BYTES_ENV = "EIOS_WARM_MAX_BYTES"
LOCATION_ENV = "EIOS_WARM_LOCATION"
ENVIRONMENT_ENV = "EIOS_ENVIRONMENT"


class WarmConfigError(ValueError):
    """The warm tier is configured in a way that cannot work; the service refuses to start."""


class LazyLocalWarmStore:
    """The local double, filled from the world the first time a warm query arrives, so start-up does not pay for it."""

    backend = "local"

    def __init__(self, world: AmlWorld) -> None:
        self._world = world
        self._inner: LocalWarmStore | None = None
        self._lock = threading.Lock()

    def _ready(self) -> LocalWarmStore:
        with self._lock:
            if self._inner is None:
                started = time.perf_counter()
                sink = LocalWarmSink()
                summary = load_transactions_history(self._world, None, sink)
                _LOG.info(
                    "local warm tier loaded in %.1fs: %d events accepted, %d quarantined [MEASURED]",
                    time.perf_counter() - started,
                    summary.loaded,
                    summary.quarantined,
                )
                self._inner = LocalWarmStore(sink.connection)
            return self._inner

    def run(self, query: str, params: Mapping[str, Any]) -> WarmResult:
        return self._ready().run(query, params)


def build_warm_store(world: AmlWorld, env: Mapping[str, str] | None = None) -> WarmStore | None:
    source = os.environ if env is None else env
    backend = source.get(BACKEND_ENV, "local").strip().lower()
    if backend == "off":
        return None
    if backend == "local":
        return LazyLocalWarmStore(world)
    if backend == "bigquery":
        project = source.get(PROJECT_ENV, "").strip()
        if not project:
            raise WarmConfigError(f"{BACKEND_ENV}=bigquery needs {PROJECT_ENV}")
        return BigQueryWarmStore(
            project,
            max_bytes=int(source.get(MAX_BYTES_ENV, DEFAULT_MAX_BYTES)),
            location=source.get(LOCATION_ENV, "us-central1"),
            labels={"environment": source.get(ENVIRONMENT_ENV, "").strip().lower()},
        )
    raise WarmConfigError(f"{BACKEND_ENV} must be bigquery, local or off, not {backend!r}")
