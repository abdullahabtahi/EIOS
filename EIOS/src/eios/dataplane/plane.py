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
from enum import StrEnum

from eios.cockpit.compliance import ComplianceExplorerService
from eios.cockpit.governance_runtime import GovernanceRuntime, build_governance_runtime
from eios.cockpit.partner_readmodel import PartnerReadModel
from eios.dataplane.aml_engine import run_aml_engine
from eios.dataplane.aml_service import EngineAMLService
from eios.dataplane.partner_engine import PartnerSnapshot, run_partner_engine
from eios.dataplane.partner_service import EnginePartnerService
from eios.foundry.scenarios.aml_config import STORY_PARTNER, AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.foundry.scenarios.partner_config import PartnerWorldConfig
from eios.foundry.scenarios.partner_world import build_partner_world
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.ontology.omcp.port.readmodels import ReadModels

logger = logging.getLogger(__name__)
PLANE_ENV = "EIOS_DATA_PLANE"


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


def _build_engines() -> tuple[EngineAMLService, EnginePartnerService]:
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
    return EngineAMLService(snapshot), EnginePartnerService(partner, snapshot)


def read_models() -> ReadModels:
    """The process-wide read models; every route and the assistant share these objects."""
    global _models, _engine, _partner
    ledger = governance()
    with _lock:
        if _models is None:
            if plane_kind() is PlaneKind.ENGINE:
                _engine, _partner = _build_engines()
                engine = _engine
                _models = ReadModels.over(
                    engine,
                    clock=lambda: engine.as_of,
                    aml_origin=DataOrigin.ENGINE,
                    partner=_partner,
                    compliance=ComplianceExplorerService.over_ledger(
                        ledger.sequencer, ledger.worm, ledger.hub
                    ),
                )
            else:
                _models = ReadModels.default()
        return _models


def engine_service() -> EngineAMLService | None:
    """The engine-backed AML service, or None on the fixture plane."""
    read_models()
    return _engine


def partner_engine_service() -> EnginePartnerService | None:
    """The engine-backed partner service, or None on the fixture plane."""
    read_models()
    return _partner


def aml_data_origin() -> str:
    """`engine` when the AML read model is computed from the world, `fixture` otherwise."""
    return PlaneKind.ENGINE.value if engine_service() is not None else PlaneKind.FIXTURE.value


def reset_for_testing() -> None:
    global _models, _engine, _partner, _governance
    with _lock:
        _models, _engine, _partner, _governance = None, None, None, None
