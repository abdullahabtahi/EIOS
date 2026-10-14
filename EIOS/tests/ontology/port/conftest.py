"""Shared fixtures: the real catalogue over the same services the workstations render."""

import pytest

from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import Principal, principal_for
from eios.ontology.omcp.port.service import GovernedToolPort


@pytest.fixture
def port() -> GovernedToolPort:
    return build_port()


def who(workstation: str) -> Principal:
    return principal_for("uid-test", workstation)
