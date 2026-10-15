"""What the tool port and the workstation routes need from an operations read model (spec 035).

Two planes satisfy it: `DataPlatformOperationsService` (hand-written fixtures) and the engine-backed service over the
real ingestion pipeline, the profiled data products, the probes and the restore drill.
"""

from datetime import datetime
from typing import Any, Protocol

from eios.cockpit.operations import DataProductSLAStatus


class OperationsReadModel(Protocol):
    def get_data_products(self, as_of: datetime | None = None) -> list[DataProductSLAStatus]: ...

    def get_contract_breach_alerts(self, as_of: datetime | None = None) -> list[dict[str, Any]]: ...

    def get_identity_cluster_conflicts(self) -> list[dict[str, Any]]: ...

    def get_board_summary(self, as_of: datetime | None = None) -> dict[str, Any]: ...
