"""The backend is chosen by environment; a deployed service that asks for the warehouse and lacks a project refuses."""

import pytest

from eios.foundry.scenarios.aml_world import AmlWorld
from eios.warm.config import LazyLocalWarmStore, WarmConfigError, build_warm_store
from eios.warm.store import BigQueryWarmStore


def test_the_default_is_the_local_double_filled_on_first_use(small_world: AmlWorld) -> None:
    store = build_warm_store(small_world, {})
    assert (
        isinstance(store, LazyLocalWarmStore) and store._inner is None
    )  # nothing loaded at start-up
    assert (
        store.run(
            "account_daily_activity",
            {
                "client_id": "NOPE",
                "start": "2026-09-01T00:00:00+00:00",
                "end": "2026-10-01T00:00:00+00:00",
            },
        ).rows
        == []
    )
    assert store._inner is not None  # loaded by the first query


def test_off_means_no_warm_tier(small_world: AmlWorld) -> None:
    assert build_warm_store(small_world, {"EIOS_WARM_BACKEND": "off"}) is None


def test_bigquery_needs_a_project(small_world: AmlWorld) -> None:
    with pytest.raises(WarmConfigError):
        build_warm_store(small_world, {"EIOS_WARM_BACKEND": "bigquery"})


def test_bigquery_reads_its_cap_and_project(
    small_world: AmlWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "eios.warm.store.BigQueryWarmStore.__init__",
        lambda self, project, **kw: self.__dict__.update(project=project, **kw),
    )
    store = build_warm_store(
        small_world,
        {"EIOS_WARM_BACKEND": "bigquery", "EIOS_WARM_PROJECT": "p", "EIOS_WARM_MAX_BYTES": "5000"},
    )
    assert isinstance(store, BigQueryWarmStore) and store.__dict__["max_bytes"] == 5000


def test_bigquery_jobs_are_labelled_with_the_environment(
    small_world: AmlWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "eios.warm.store.BigQueryWarmStore.__init__",
        lambda self, project, **kw: self.__dict__.update(project=project, **kw),
    )
    store = build_warm_store(
        small_world,
        {
            "EIOS_WARM_BACKEND": "bigquery",
            "EIOS_WARM_PROJECT": "p",
            "EIOS_ENVIRONMENT": "Prod-Like",
        },
    )
    assert store.__dict__["labels"] == {"environment": "prod-like"}


def test_an_unknown_backend_is_a_start_up_error(small_world: AmlWorld) -> None:
    with pytest.raises(WarmConfigError):
        build_warm_store(small_world, {"EIOS_WARM_BACKEND": "postgres"})
