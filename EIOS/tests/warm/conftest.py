import pytest

from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import AmlWorld, build_aml_world


@pytest.fixture(scope="session")
def small_world() -> AmlWorld:
    """A real AML world, small enough to build in a fraction of a second: 30 days of history."""
    return build_aml_world(
        AmlWorldConfig(
            n_clients=300,
            n_wash=2,
            n_structuring=2,
            ring_sizes=(5, 4),
            n_cgnat_hubs=1,
            cgnat_degree=(110, 120),
            n_hub_agent_clients=0,
            n_households=2,
            n_family_triplets=1,
            n_scalpers=2,
            n_wealthy=2,
        )
    )
