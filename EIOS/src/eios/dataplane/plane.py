"""Choose and build the data plane once per process: the one `ReadModels` under every route and the assistant (spec 031 FR-008, FR-009).

`EIOS_DATA_PLANE=engine` runs the detectors over the seeded world; `fixture` keeps the hand-written services for
unit tests. Unset means `engine`. Building takes a few seconds, so it happens once, at first use.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Mapping
from enum import StrEnum

from eios.cockpit.partner import PartnerWorkstationService
from eios.dataplane.aml_engine import run_aml_engine
from eios.dataplane.aml_service import EngineAMLService
from eios.foundry.scenarios.aml_config import STORY_PARTNER, AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
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


def world_config(partner: PartnerWorkstationService) -> AmlWorldConfig:
    """The world's referring partners are the partners on the radar, so a ring's partner is a partner the radar shows."""
    ids = tuple(p.partner_id for p in partner.get_churn_radar_scatter().partners)
    return AmlWorldConfig(partner_ids=(*ids, *(() if STORY_PARTNER in ids else (STORY_PARTNER,))))


def _build_engine() -> EngineAMLService:
    started = time.perf_counter()
    config = world_config(PartnerWorkstationService())
    snapshot = run_aml_engine(build_aml_world(config))
    q = snapshot.quality
    logger.info(
        "engine plane built in %.1fs: %d accounts, %d raw alerts, %d cases, top-%d precision %.2f, "
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
    return EngineAMLService(snapshot)


def read_models() -> ReadModels:
    """The process-wide read models; every route and the assistant share these objects."""
    global _models, _engine
    with _lock:
        if _models is None:
            if plane_kind() is PlaneKind.ENGINE:
                _engine = _build_engine()
                engine = _engine
                _models = ReadModels.over(
                    engine, clock=lambda: engine.as_of, aml_origin=DataOrigin.ENGINE
                )
            else:
                _models = ReadModels.default()
        return _models


def engine_service() -> EngineAMLService | None:
    """The engine-backed AML service, or None on the fixture plane."""
    read_models()
    return _engine


def aml_data_origin() -> str:
    """`engine` when the AML read model is computed from the world, `fixture` otherwise."""
    return PlaneKind.ENGINE.value if engine_service() is not None else PlaneKind.FIXTURE.value


def reset_for_testing() -> None:
    global _models, _engine
    with _lock:
        _models, _engine = None, None
