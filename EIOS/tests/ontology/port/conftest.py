"""Shared fixtures: the real catalogue over the same services the workstations render."""

from dataclasses import replace

import pytest

from eios.knowledge.static_index import StaticIndex
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import Principal, principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.knowledge.passages import ALL


@pytest.fixture
def port() -> GovernedToolPort:
    return build_port(replace(ReadModels.default(), knowledge=StaticIndex(ALL)))


def who(workstation: str) -> Principal:
    return principal_for("uid-test", workstation)
