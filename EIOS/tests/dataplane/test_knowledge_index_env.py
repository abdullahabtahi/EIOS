"""Which project the regulation index is read from: its own when named, else the service's project."""

import pytest

from eios.dataplane.plane import PlaneConfigError, knowledge_index


def _project(index) -> str:
    return index._project


def test_the_index_is_read_from_the_services_project_by_default() -> None:
    env = {"EIOS_KNOWLEDGE_DATA_STORE": "regs", "GOOGLE_CLOUD_PROJECT": "svc-project"}
    assert _project(knowledge_index(env)) == "svc-project"


def test_a_named_knowledge_project_wins_over_the_services_project() -> None:
    env = {
        "EIOS_KNOWLEDGE_DATA_STORE": "regs",
        "GOOGLE_CLOUD_PROJECT": "svc-project",
        "EIOS_KNOWLEDGE_PROJECT": "docs-project",
    }
    assert _project(knowledge_index(env)) == "docs-project"


def test_no_data_store_means_no_index() -> None:
    assert knowledge_index({"GOOGLE_CLOUD_PROJECT": "svc-project"}) is None


def test_a_data_store_without_any_project_is_a_configuration_error() -> None:
    with pytest.raises(PlaneConfigError):
        knowledge_index({"EIOS_KNOWLEDGE_DATA_STORE": "regs"})
