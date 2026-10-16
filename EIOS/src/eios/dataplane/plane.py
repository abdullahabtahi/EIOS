"""Choose and build the data plane once per process: the one `ReadModels` under every route and the assistant (spec 031 FR-008, FR-009; spec 032).

`EIOS_DATA_PLANE=engine` runs the AML and partner engines over their seeded worlds; `fixture` keeps the hand-written
services for unit tests. Unset means `engine`. Building takes a few seconds, so it happens once, at first use. The
partner world is built first: its roster is the AML world's list of referring partners, so a ring's partner is a
partner on the radar, and the partner service reads the AML cases among each partner's referrals.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Iterable, Mapping
from dataclasses import replace
from enum import StrEnum
from typing import NamedTuple

from eios.cockpit.compliance import ComplianceExplorerService
from eios.cockpit.governance_runtime import GovernanceRuntime, build_governance_runtime
from eios.cockpit.partner_readmodel import PartnerReadModel
from eios.dataplane.aml_engine import AmlSnapshot, run_aml_engine
from eios.dataplane.aml_service import EngineAMLService
from eios.dataplane.executive_engine import run_executive_engine
from eios.dataplane.executive_service import EngineExecutiveService
from eios.dataplane.geo_readmodel import PlaneGeo
from eios.dataplane.ops_calibration import calibration_sample
from eios.dataplane.ops_service import EngineOperationsService
from eios.dataplane.partner_engine import PartnerSnapshot, run_partner_engine
from eios.dataplane.partner_service import EnginePartnerService
from eios.foundry.scenarios.aml_config import STORY_PARTNER, AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.foundry.scenarios.executive_world import ExecutiveWorldConfig, build_executive_world
from eios.foundry.scenarios.partner_config import PartnerWorldConfig
from eios.foundry.scenarios.partner_world import build_partner_world
from eios.knowledge.agent_search import AgentSearchIndex
from eios.knowledge.passage import RegulationIndex
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.warm.config import build_warm_store

logger = logging.getLogger(__name__)
PLANE_ENV = "EIOS_DATA_PLANE"
KNOWLEDGE_STORE_ENV = "EIOS_KNOWLEDGE_DATA_STORE"
KNOWLEDGE_PROJECT_ENV = "GOOGLE_CLOUD_PROJECT"
KNOWLEDGE_OWN_PROJECT_ENV = (
    "EIOS_KNOWLEDGE_PROJECT"  # optional: the project that holds the data store
)


class PlaneKind(StrEnum):
    ENGINE = "engine"
    FIXTURE = "fixture"


class PlaneConfigError(ValueError):
    """`EIOS_DATA_PLANE` names a plane that does not exist."""


def plane_kind(env: Mapping[str, str] | None = None) -> PlaneKind:
    source = os.environ if env is None else env
    raw = source.get(PLANE_ENV, PlaneKind.ENGINE.value).strip().lower()
    try:
        return PlaneKind(raw)
    except ValueError:
        raise PlaneConfigError(f"{PLANE_ENV} must be 'engine' or 'fixture', not '{raw}'") from None


_lock = threading.Lock()
_models: ReadModels | None = None
_engine: EngineAMLService | None = None
_partner: EnginePartnerService | None = None
_executive: EngineExecutiveService | None = None
_operations: EngineOperationsService | None = None
_governance: GovernanceRuntime | None = None


def governance() -> GovernanceRuntime:
    """The process-wide governed-action stack: the shelf writes to it and the compliance views read it."""
    global _governance
    with _lock:
        if _governance is None:
            _governance = build_governance_runtime()
        return _governance


def _aml_config(ids: Iterable[str]) -> AmlWorldConfig:
    found = tuple(ids)
    return AmlWorldConfig(
        partner_ids=(*found, *(() if STORY_PARTNER in found else (STORY_PARTNER,)))
    )


def world_config(partner: PartnerReadModel) -> AmlWorldConfig:
    """The world's referring partners are the partners on the radar, so a ring's partner is a partner the radar shows."""
    return _aml_config(p.partner_id for p in partner.get_churn_radar_scatter().partners)


def _build_partner() -> PartnerSnapshot:
    started = time.perf_counter()
    snap = run_partner_engine(build_partner_world(PartnerWorldConfig()))
    q = snap.quality
    logger.info(
        "partner engine built in %.1fs: %d partners, hazard AUC %.3f, precision at %d %.2f, "
        "holiday false alarms %d of %d, cohort found %s, pairs %d of %d (%d false) [MEASURED]",
        time.perf_counter() - started,
        q.partners,
        q.hazard_auc,
        q.planted_churners,
        q.precision_at_k,
        q.seasonal_false_alarms,
        q.seasonal_partners,
        q.cohort_found,
        q.pairs_found,
        q.pairs_planted,
        q.false_pairs,
    )
    return snap


def _build_executive(
    partner: EnginePartnerService, snapshot: AmlSnapshot
) -> EngineExecutiveService:
    started = time.perf_counter()
    exec_world = build_executive_world(
        ExecutiveWorldConfig(as_of=partner.snapshot.world.config.as_of.date())
    )
    service = EngineExecutiveService(run_executive_engine(exec_world), partner, snapshot)
    q = service.snapshot.quality
    logger.info(
        "executive engine built in %.1fs: %d days, causal chain %d of %d edges passed, max coefficient error %.3f, "
        "control rejected %s, forecast skill vs persistence %.2f, interval coverage %.2f over %d origins [MEASURED]",
        time.perf_counter() - started,
        q.history_days,
        q.chain_edges_passed,
        q.chain_edges,
        q.max_coefficient_error,
        q.control_rejected,
        q.forecast_mase,
        q.forecast_coverage,
        q.backtest_origins,
    )
    return service


class _Engines(NamedTuple):
    aml: EngineAMLService
    partner: EnginePartnerService
    executive: EngineExecutiveService
    operations: EngineOperationsService
    aml_snapshot: AmlSnapshot


def _build_operations(
    snapshot: AmlSnapshot, partner: EnginePartnerService, executive: EngineExecutiveService
) -> EngineOperationsService:
    started = time.perf_counter()
    service = EngineOperationsService.build(
        snapshot, partner, executive.snapshot.world, partner.as_of
    )
    r, d = service.replay, service.drill
    logger.info(
        "operations engine built in %.1fs: %d events replayed through the ingestion pipeline, %d of %d planted "
        "breaches quarantined, %d healthy events refused, restore drill %d of %d rows verified %s [MEASURED]",
        time.perf_counter() - started,
        r.offered,
        r.caught,
        r.planted,
        r.false_rejects,
        d.rows_restored,
        d.rows_exported,
        d.verified,
    )
    return service


def _build_engines() -> _Engines:
    partner = _build_partner()
    started = time.perf_counter()
    snapshot = run_aml_engine(build_aml_world(_aml_config(partner.scored.index.astype(str))))
    q = snapshot.quality
    logger.info(
        "AML engine built in %.1fs: %d accounts, %d raw alerts, %d cases, top-%d precision %.2f, "
        "planted recall %.2f, ring recovery %.2f [MEASURED]",
        time.perf_counter() - started,
        len(snapshot.facts),
        q.raw_alerts,
        q.cases,
        q.top_k,
        q.precision_at_k,
        q.recall_at_k,
        q.ring_recovery,
    )
    partner_service = EnginePartnerService(partner, snapshot)
    executive = _build_executive(partner_service, snapshot)
    return _Engines(
        EngineAMLService(snapshot),
        partner_service,
        executive,
        _build_operations(snapshot, partner_service, executive),
        snapshot,
    )


def knowledge_index(env: Mapping[str, str] | None = None) -> RegulationIndex | None:
    """The regulatory index named by `EIOS_KNOWLEDGE_DATA_STORE`, or None when none is configured (the tool then says so)."""
    source = os.environ if env is None else env
    store = source.get(KNOWLEDGE_STORE_ENV, "").strip()
    # The data store may live in another project than the service (the regulation corpus is built once, in dev).
    project = (
        source.get(KNOWLEDGE_OWN_PROJECT_ENV, "").strip()
        or source.get(KNOWLEDGE_PROJECT_ENV, "").strip()
    )
    if not store:
        return None
    if not project:
        raise PlaneConfigError(f"{KNOWLEDGE_STORE_ENV} needs {KNOWLEDGE_PROJECT_ENV}")
    return AgentSearchIndex(project, store)


def read_models() -> ReadModels:
    """The process-wide read models; every route and the assistant share these objects."""
    global _models, _engine, _partner, _executive, _operations
    ledger = governance()
    with _lock:
        if _models is None:
            if plane_kind() is PlaneKind.ENGINE:
                built = _build_engines()
                _engine, _partner, _executive, _operations = (
                    built.aml,
                    built.partner,
                    built.executive,
                    built.operations,
                )
                engine = _engine
                _models = ReadModels.over(
                    engine,
                    clock=lambda: engine.as_of,
                    aml_origin=DataOrigin.ENGINE,
                    partner=_partner,
                    executive=_executive,
                    operations=_operations,
                    calibration_sample=calibration_sample(built.partner.snapshot),
                    compliance=ComplianceExplorerService.over_ledger(
                        ledger.sequencer, ledger.worm, ledger.hub
                    ),
                    knowledge=knowledge_index(),
                    warm=build_warm_store(built.aml_snapshot.world),
                    geo=PlaneGeo(),  # built on first use: its tiers come from the warehouse
                )
                _operations.measure(_models, built.aml_snapshot)
            else:
                _models = replace(ReadModels.default(), knowledge=knowledge_index())
        return _models


def engine_service() -> EngineAMLService | None:
    """The engine-backed AML service, or None on the fixture plane."""
    read_models()
    return _engine


def partner_engine_service() -> EnginePartnerService | None:
    """The engine-backed partner service, or None on the fixture plane."""
    read_models()
    return _partner


def executive_engine_service() -> EngineExecutiveService | None:
    """The engine-backed executive service, or None on the fixture plane."""
    read_models()
    return _executive


def operations_engine_service() -> EngineOperationsService | None:
    """The engine-backed operations service, or None on the fixture plane."""
    read_models()
    return _operations


def aml_data_origin() -> str:
    """`engine` when the AML read model is computed from the world, `fixture` otherwise."""
    return PlaneKind.ENGINE.value if engine_service() is not None else PlaneKind.FIXTURE.value


def reset_for_testing() -> None:
    global _models, _engine, _partner, _executive, _operations, _governance
    with _lock:
        _models, _engine, _partner, _executive, _operations, _governance = (
            None,
            None,
            None,
            None,
            None,
            None,
        )
