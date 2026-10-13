"""Client data generator producing client_360, client_funnel, and device_network feeds (FR-011 to FR-016)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

from eios.foundry.contracts import (
    Client360Record,
    ContractValidator,
    DeviceNetworkEdge,
    FunnelEventRecord,
)
from eios.foundry.rng import RNGManager
from eios.foundry.storage.parquet_writer import DeterministicParquetWriter
from eios.foundry.universe import GlobalEntityUniverse


class ClientDataGenerator:
    """Generates siloed client projections, customer 360, funnel, and device network products."""

    def __init__(self, universe: GlobalEntityUniverse, rng: RNGManager) -> None:
        self.universe = universe
        self.rng = rng
        self._gen = rng.get_generator("gen_client")
        self._validator_360 = ContractValidator(Client360Record)
        self._validator_funnel = ContractValidator(FunnelEventRecord)
        self._validator_device = ContractValidator(DeviceNetworkEdge)

    def generate_silo_projections(self) -> list[dict[str, Any]]:
        """Returns fragmented multi-silo identity representations for entity resolution benchmarking."""
        projections: list[dict[str, Any]] = []
        for account in self.universe.accounts:
            projections.append(
                {
                    "person_id": account.person_id,
                    "deriv_trader_cr_id": account.account_id,
                    "mt5_login_id": account.mt5_login_id,
                    "dp2p_nickname": account.dp2p_nickname,
                    "email": account.email,
                    "country": account.country,
                }
            )
        return projections

    def generate_client_360(self) -> list[dict[str, Any]]:
        """Emits validated client_360 records."""
        records: list[dict[str, Any]] = []
        for account in self.universe.accounts:
            record = {
                "client_id": account.client_id,
                "person_id": account.person_id,
                "country": account.country,
                "kyc_tier": account.kyc_tier,
                "kyc_approved_at": account.kyc_approved_at,
                "created_at": account.created_at,
                "status": account.status,
                "mt5_login_id": account.mt5_login_id,
                "account_id": account.account_id,
                "email": account.email,
                "has_identity_duplicate_noise": account.has_identity_duplicate_noise,
            }
            records.append(record)

        # Batch validation gate against Layer 1 schema
        self._validator_360.validate_batch(records)
        return records

    def generate_client_funnel(self) -> list[dict[str, Any]]:
        """Emits validated client_funnel progression event records."""
        events: list[dict[str, Any]] = []
        event_counter = 0

        for account in self.universe.accounts:
            base_dt = datetime.fromisoformat(account.created_at)
            # Visit happens minutes or hours before signup
            visit_dt = base_dt - timedelta(minutes=int(self._gen.integers(5, 120)))

            event_counter += 1
            events.append(
                {
                    "event_id": f"FNL-{event_counter:08d}",
                    "client_id": account.client_id,
                    "step": "VISIT",
                    "timestamp": visit_dt.isoformat(),
                }
            )

            event_counter += 1
            events.append(
                {
                    "event_id": f"FNL-{event_counter:08d}",
                    "client_id": account.client_id,
                    "step": "SIGNUP",
                    "timestamp": account.created_at,
                }
            )

            if account.kyc_tier != "TIER_0_UNVERIFIED":
                kyc_submit_dt = base_dt + timedelta(hours=int(self._gen.integers(1, 24)))
                event_counter += 1
                events.append(
                    {
                        "event_id": f"FNL-{event_counter:08d}",
                        "client_id": account.client_id,
                        "step": "KYC_SUBMIT",
                        "timestamp": kyc_submit_dt.isoformat(),
                    }
                )

                # 80% of verified clients proceed to FIRST_DEPOSIT
                if self._gen.uniform(0, 1) < 0.8:
                    deposit_dt = kyc_submit_dt + timedelta(hours=int(self._gen.integers(2, 48)))
                    event_counter += 1
                    events.append(
                        {
                            "event_id": f"FNL-{event_counter:08d}",
                            "client_id": account.client_id,
                            "step": "FIRST_DEPOSIT",
                            "timestamp": deposit_dt.isoformat(),
                        }
                    )

        # Batch validation gate
        self._validator_funnel.validate_batch(events)
        return events

    def generate_device_network(self) -> list[dict[str, Any]]:
        """Emits validated device_network_graph edge records."""
        edges: list[dict[str, Any]] = []
        edge_counter = 0

        for account in self.universe.accounts:
            devices = self.universe.get_devices_for_client(account.client_id)
            ips = self.universe.get_ips_for_client(account.client_id)

            for dev in devices:
                for ip in ips:
                    edge_counter += 1
                    edges.append(
                        {
                            "edge_id": f"DNE-{edge_counter:08d}",
                            "client_id": account.client_id,
                            "device_hash": dev.device_hash,
                            "ip_address": ip.ip_address,
                            "is_hub": ip.is_hub,
                            "timestamp": account.created_at,
                        }
                    )

        # Batch validation gate
        self._validator_device.validate_batch(edges)
        return edges

    def write_to_storage(self, output_dir: Path) -> dict[str, Path]:
        """Writes client_360, client_funnel, and device_network Parquet files deterministically."""
        writer = DeterministicParquetWriter()
        c360_dir = output_dir / "client_360"
        funnel_dir = output_dir / "client_funnel"
        device_dir = output_dir / "device_network"

        c360_df = pl.DataFrame(self.generate_client_360())
        funnel_df = pl.DataFrame(self.generate_client_funnel())
        device_df = pl.DataFrame(self.generate_device_network())

        # Sort columns deterministically and write
        p_c360 = writer.write_partition(
            c360_df, c360_dir / "client_360.parquet", sort_columns=["client_id"]
        )
        p_funnel = writer.write_partition(
            funnel_df, funnel_dir / "client_funnel.parquet", sort_columns=["event_id"]
        )
        p_device = writer.write_partition(
            device_df, device_dir / "device_network.parquet", sort_columns=["edge_id"]
        )

        return {
            "client_360": p_c360,
            "client_funnel": p_funnel,
            "device_network": p_device,
        }
