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
from eios.cockpit.executive_readmodel import ExecutiveReadModel
from eios.cockpit.operations import DataPlatformOperationsService
from eios.cockpit.operations_readmodel import OperationsReadModel
from eios.cockpit.partner import PartnerWorkstationService
from eios.cockpit.partner_readmodel import PartnerReadModel
from eios.dataplane.ops_calibration import CalibrationSample
from eios.flywheel.diagnostics import CalibrationDiagnosticsEngine
from eios.flywheel.ledger import DecisionOutcomesLedger
from eios.hardening.runbooks import RunbookVerificationEngine
from eios.knowledge.passage import RegulationIndex
from eios.observability.slo_engine import SLOMonitoringEngine
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.ontology.omcp.port.entities import EntityDirectory, build_directory
from eios.ontology.omcp.port.facts import FactResolver


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ReadModels:
    aml: AmlReadModel
    partner: PartnerReadModel
    executive: ExecutiveReadModel
    compliance: ComplianceExplorerService
    operations: OperationsReadModel
    directory: EntityDirectory
    slo_engine: SLOMonitoringEngine
    runbooks: RunbookVerificationEngine
    outcomes: DecisionOutcomesLedger
    calibration: CalibrationDiagnosticsEngine
    clock: Callable[[], datetime] = field(default=_utc_now)
    aml_origin: DataOrigin = DataOrigin.FIXTURE  # where the AML read model's numbers come from
    partner_origin: DataOrigin = (
        DataOrigin.FIXTURE
    )  # where the partner read model's numbers come from
    operations_origin: DataOrigin = (
        DataOrigin.FIXTURE
    )  # where the operations read model's numbers come from
    calibration_sample: CalibrationSample | None = (
        None  # predictions with observed outcomes, when a plane has them
    )
    executive_origin: DataOrigin = (
        DataOrigin.FIXTURE
    )  # where the executive read model's numbers come from
    facts: FactResolver = field(default_factory=FactResolver)
    knowledge: RegulationIndex | None = (
        None  # the regulatory corpus; None until an index is configured
    )

    @classmethod
    def default(cls) -> ReadModels:
        """Fixture plane: fresh hand-written services, for tests and offline runs."""
        return cls.over(AMLWorkstationService())

    @classmethod
    def over(  # noqa: PLR0913
        cls,
        aml: AmlReadModel,
        clock: Callable[[], datetime] = _utc_now,
        aml_origin: DataOrigin = DataOrigin.FIXTURE,
        compliance: ComplianceExplorerService | None = None,
        partner: PartnerReadModel | None = None,
        knowledge: RegulationIndex | None = None,
        executive: ExecutiveReadModel | None = None,
        operations: OperationsReadModel | None = None,
        calibration_sample: CalibrationSample | None = None,
    ) -> ReadModels:
        """Read models over the given AML plane (and partner plane and ledger, when given); the rest is built fresh."""
        partners: PartnerReadModel = partner or PartnerWorkstationService()
        return cls(
            aml=aml,
            partner=partners,
            executive=executive or ExecutiveCockpitService(),
            compliance=compliance or ComplianceExplorerService(),
            operations=operations or DataPlatformOperationsService(),
            directory=build_directory(aml, partners),
            slo_engine=SLOMonitoringEngine(),
            runbooks=RunbookVerificationEngine(),
            outcomes=DecisionOutcomesLedger(),
            calibration=CalibrationDiagnosticsEngine(),
            clock=clock,
            aml_origin=aml_origin,
            partner_origin=DataOrigin.ENGINE if partner is not None else DataOrigin.FIXTURE,
            executive_origin=DataOrigin.ENGINE if executive is not None else DataOrigin.FIXTURE,
            operations_origin=DataOrigin.ENGINE if operations is not None else DataOrigin.FIXTURE,
            calibration_sample=calibration_sample,
            knowledge=knowledge,
        )
