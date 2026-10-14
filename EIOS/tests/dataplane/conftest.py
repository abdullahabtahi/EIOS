"""The partner engine is built once per session: the world and three scoring runs take a few seconds."""

import pytest

from eios.dataplane.partner_engine import PartnerSnapshot, run_partner_engine
from eios.dataplane.partner_service import EnginePartnerService
from eios.foundry.scenarios.partner_config import PartnerWorldConfig
from eios.foundry.scenarios.partner_world import build_partner_world


@pytest.fixture(scope="session")
def partner_snapshot() -> PartnerSnapshot:
    return run_partner_engine(build_partner_world(PartnerWorldConfig()))


@pytest.fixture(scope="session")
def partner_service(partner_snapshot: PartnerSnapshot) -> EnginePartnerService:
    return EnginePartnerService(partner_snapshot)
