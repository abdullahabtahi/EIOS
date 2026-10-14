"""The services the capabilities read, injected so the port and the workstation endpoints share instances.

The cockpit server builds its singletons once and passes them here, so a screen and an assistant answer are
built from the same objects (spec 023 FR-010). `default()` builds fresh ones for tests and offline runs.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from eios.cockpit.aml import AMLWorkstationService
from eios.cockpit.compliance import ComplianceExplorerService
from eios.cockpit.executive import ExecutiveCockpitService
from eios.cockpit.operations import DataPlatformOperationsService
from eios.cockpit.partner import PartnerWorkstationService
from eios.ontology.omcp.port.entities import EntityDirectory, default_directory


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ReadModels:
    aml: AMLWorkstationService
    partner: PartnerWorkstationService
    executive: ExecutiveCockpitService
    compliance: ComplianceExplorerService
    operations: DataPlatformOperationsService
    directory: EntityDirectory
    clock: Callable[[], datetime] = field(default=_utc_now)

    @classmethod
    def default(cls) -> ReadModels:
        return cls(
            aml=AMLWorkstationService(),
            partner=PartnerWorkstationService(),
            executive=ExecutiveCockpitService(),
            compliance=ComplianceExplorerService(),
            operations=DataPlatformOperationsService(),
            directory=default_directory(),
        )
