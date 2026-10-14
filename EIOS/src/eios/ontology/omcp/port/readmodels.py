"""The services the capabilities read, injected so the port and the workstation endpoints share instances.

The cockpit server builds its singletons once and passes them here, so a screen and an assistant answer are
built from the same objects (spec 023 FR-010). `default()` builds fresh ones for tests and offline runs.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from eios.cockpit.aml import AMLWorkstationService
from eios.cockpit.aml_readmodel import AmlReadModel
from eios.cockpit.compliance import ComplianceExplorerService
from eios.cockpit.executive import ExecutiveCockpitService
from eios.cockpit.operations import DataPlatformOperationsService
from eios.cockpit.partner import PartnerWorkstationService
from eios.flywheel.diagnostics import CalibrationDiagnosticsEngine
from eios.flywheel.ledger import DecisionOutcomesLedger
from eios.hardening.runbooks import RunbookVerificationEngine
from eios.observability.slo_engine import SLOMonitoringEngine
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.ontology.omcp.port.entities import EntityDirectory, build_directory
from eios.ontology.omcp.port.facts import FactResolver


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ReadModels:
    aml: AmlReadModel
    partner: PartnerWorkstationService
    executive: ExecutiveCockpitService
    compliance: ComplianceExplorerService
    operations: DataPlatformOperationsService
    directory: EntityDirectory
    slo_engine: SLOMonitoringEngine
    runbooks: RunbookVerificationEngine
    outcomes: DecisionOutcomesLedger
    calibration: CalibrationDiagnosticsEngine
    clock: Callable[[], datetime] = field(default=_utc_now)
    aml_origin: DataOrigin = DataOrigin.FIXTURE  # where the AML read model's numbers come from
    facts: FactResolver = field(default_factory=FactResolver)

    @classmethod
    def default(cls) -> ReadModels:
        """Fixture plane: fresh hand-written services, for tests and offline runs."""
        return cls.over(AMLWorkstationService())

    @classmethod
    def over(
        cls,
        aml: AmlReadModel,
        clock: Callable[[], datetime] = _utc_now,
        aml_origin: DataOrigin = DataOrigin.FIXTURE,
    ) -> ReadModels:
        """Read models over the given AML plane; everything else is built fresh."""
        partner = PartnerWorkstationService()
        return cls(
            aml=aml,
            partner=partner,
            executive=ExecutiveCockpitService(),
            compliance=ComplianceExplorerService(),
            operations=DataPlatformOperationsService(),
            directory=build_directory(aml, partner),
            slo_engine=SLOMonitoringEngine(),
            runbooks=RunbookVerificationEngine(),
            outcomes=DecisionOutcomesLedger(),
            calibration=CalibrationDiagnosticsEngine(),
            clock=clock,
            aml_origin=aml_origin,
        )
