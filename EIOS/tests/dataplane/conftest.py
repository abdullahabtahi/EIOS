"""The partner engine is built once per session: the world and three scoring runs take a few seconds."""

import pytest

from eios.dataplane.aml_engine import AmlSnapshot, run_aml_engine
from eios.dataplane.executive_engine import run_executive_engine
from eios.dataplane.executive_service import EngineExecutiveService
from eios.dataplane.partner_engine import PartnerSnapshot, run_partner_engine
from eios.dataplane.partner_service import EnginePartnerService
from eios.dataplane.plane import _aml_config
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.foundry.scenarios.executive_world import ExecutiveWorldConfig, build_executive_world
from eios.foundry.scenarios.partner_config import PartnerWorldConfig
from eios.foundry.scenarios.partner_world import build_partner_world


@pytest.fixture(scope="session")
def partner_snapshot() -> PartnerSnapshot:
    return run_partner_engine(build_partner_world(PartnerWorldConfig()))


@pytest.fixture(scope="session")
def partner_service(partner_snapshot: PartnerSnapshot) -> EnginePartnerService:
    return EnginePartnerService(partner_snapshot)


@pytest.fixture(scope="session")
def aml_snapshot(partner_snapshot: PartnerSnapshot) -> AmlSnapshot:
    config = _aml_config(partner_snapshot.scored.index.astype(str))
    return run_aml_engine(build_aml_world(config))


@pytest.fixture(scope="session")
def executive_service(
    partner_snapshot: PartnerSnapshot, aml_snapshot: AmlSnapshot
) -> EngineExecutiveService:
    world = build_executive_world(
        ExecutiveWorldConfig(as_of=partner_snapshot.world.config.as_of.date())
    )
    partners = EnginePartnerService(partner_snapshot, aml_snapshot)
    return EngineExecutiveService(run_executive_engine(world), partners, aml_snapshot)


@pytest.fixture(scope="session")
def ops_models(
    partner_snapshot: PartnerSnapshot,
    aml_snapshot: AmlSnapshot,
    executive_service: EngineExecutiveService,
):
    """Read models over every engine, with the operations service built, probed and measured."""
    from eios.dataplane.aml_service import EngineAMLService
    from eios.dataplane.ops_calibration import calibration_sample
    from eios.dataplane.ops_service import EngineOperationsService
    from eios.ontology.omcp.port.readmodels import ReadModels

    partners = EnginePartnerService(partner_snapshot, aml_snapshot)
    as_of = partner_snapshot.world.config.as_of
    ops = EngineOperationsService.build(
        aml_snapshot, partners, executive_service.snapshot.world, as_of
    )
    engine = EngineAMLService(aml_snapshot)
    models = ReadModels.over(
        engine,
        clock=lambda: engine.as_of,
        partner=partners,
        executive=executive_service,
        operations=ops,
        calibration_sample=calibration_sample(partner_snapshot),
    )
    ops.measure(models, aml_snapshot)
    return models, ops
