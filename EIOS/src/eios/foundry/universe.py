"""Global Entity Universe managing underlying physical reality and entity pools (FR-011 to FR-015)."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import faker

from eios.foundry.rng import RNGManager


@dataclass(frozen=True)
class PhysicalPerson:
    person_id: str
    first_name: str
    last_name: str
    email_base: str
    country: str
    tax_id: str
    birth_date: str


@dataclass(frozen=True)
class ClientAccount:
    client_id: str
    account_id: str
    person_id: str
    mt5_login_id: int
    dp2p_nickname: str
    country: str
    kyc_tier: str
    kyc_approved_at: str | None
    created_at: str
    status: str
    email: str
    has_identity_duplicate_noise: bool = False


@dataclass(frozen=True)
class Partner:
    partner_id: str
    person_id: str
    tier: int
    parent_partner_id: str | None
    country: str
    status: str = "ACTIVE"


@dataclass(frozen=True)
class Device:
    device_hash: str
    device_type: str


@dataclass(frozen=True)
class IPAddress:
    ip_address: str
    is_hub: bool = False
    hub_type: str | None = None


@dataclass(frozen=True)
class PaymentMethod:
    payment_method_id: str
    method_type: str
    account_hash: str


SAFE_DOMAINS = ["example.com", "testmail.org", "synthetic-mail.net", "foundry.local"]
COUNTRIES = ["SG", "MY", "NG", "ID", "BR", "ZA", "GB", "AE", "TH", "VN", "KE", "GH", "CO", "MX"]
KYC_TIERS = ["TIER_0_UNVERIFIED", "TIER_1_IDENTITY", "TIER_2_ADDRESS", "TIER_3_ENHANCED"]
ACCOUNT_STATUSES = ["ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "SUSPENDED", "CLOSED"]


class GlobalEntityUniverse:
    """Deterministic universe maintaining underlying physical entities and system links."""

    def __init__(
        self,
        rng: RNGManager,
        client_count: int = 1000,
        partner_count: int = 100,
    ) -> None:
        self.rng = rng
        self.client_count = client_count
        self.partner_count = partner_count

        self._gen = rng.get_generator("universe")
        self._faker = faker.Faker()
        self._faker.seed_instance(rng.derive_faker_seed("universe"))

        self.persons: list[PhysicalPerson] = []
        self.accounts: list[ClientAccount] = []
        self.partners: list[Partner] = []
        self.devices: list[Device] = []
        self.ips: list[IPAddress] = []
        self.payment_methods: list[PaymentMethod] = []

        self._client_to_devices: dict[str, list[Device]] = {}
        self._client_to_ips: dict[str, list[IPAddress]] = {}

        self._generate_universe()

    def _generate_universe(self) -> None:  # noqa: PLR0915
        """Deterministically generates entity pools and establishes referential mappings."""
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        namespace = uuid.uuid5(uuid.NAMESPACE_DNS, f"foundry.universe.{self.rng.master_seed}")

        # 1. Generate Devices
        num_devices = int(self.client_count * 1.5)
        device_types = ["MOBILE_IOS", "MOBILE_ANDROID", "DESKTOP_MAC", "DESKTOP_WIN"]
        for d_idx in range(num_devices):
            raw_hash = hashlib.sha256(f"device_{self.rng.master_seed}_{d_idx}".encode()).hexdigest()
            d_type = device_types[d_idx % len(device_types)]
            self.devices.append(Device(device_hash=raw_hash, device_type=d_type))

        # 2. Generate IPs (including 1 carrier-NAT hub IP)
        num_ips = int(self.client_count * 1.2)
        # Dedicated Carrier-NAT hub IP
        cgnat_hub = IPAddress(ip_address="100.64.0.1", is_hub=True, hub_type="CGNAT")
        self.ips.append(cgnat_hub)

        for ip_idx in range(1, num_ips):
            # Synthetic IPv4 in private or documentation space
            octet2 = (ip_idx // 254) % 250 + 1
            octet3 = (ip_idx % 254) + 1
            ip_str = f"198.51.{octet2}.{octet3}"
            self.ips.append(IPAddress(ip_address=ip_str, is_hub=False))

        # 3. Generate Physical Persons & Accounts
        for c_idx in range(self.client_count):
            person_uuid = str(uuid.uuid5(namespace, f"person_{c_idx}"))
            first_name = self._faker.first_name()
            last_name = self._faker.last_name()
            country = COUNTRIES[c_idx % len(COUNTRIES)]
            tax_id = f"TAX-{country}-{100000 + c_idx}"
            birth_date = f"{1970 + (c_idx % 35):04d}-{(c_idx % 12) + 1:02d}-{(c_idx % 28) + 1:02d}"

            person = PhysicalPerson(
                person_id=person_uuid,
                first_name=first_name,
                last_name=last_name,
                email_base=f"{first_name.lower()}.{last_name.lower()}",
                country=country,
                tax_id=tax_id,
                birth_date=birth_date,
            )
            self.persons.append(person)

            # Account attributes
            client_id = f"CR{1000000 + c_idx}"
            mt5_login_id = 10000000 + c_idx
            dp2p_nickname = f"Trader_{c_idx:05d}"
            kyc_tier = KYC_TIERS[c_idx % len(KYC_TIERS)]

            created_offset_days = int(self._gen.integers(0, 365))
            created_dt = base_time + timedelta(
                days=created_offset_days, seconds=int(self._gen.integers(0, 86400))
            )
            created_at = created_dt.isoformat()

            if kyc_tier != "TIER_0_UNVERIFIED":
                kyc_dt = created_dt + timedelta(
                    days=int(self._gen.integers(1, 10)), hours=int(self._gen.integers(1, 24))
                )
                kyc_approved_at: str | None = kyc_dt.isoformat()
            else:
                kyc_approved_at = None

            status = ACCOUNT_STATUSES[c_idx % len(ACCOUNT_STATUSES)]

            # 5% domain variations / duplicate identity noise
            has_identity_duplicate_noise = c_idx % 20 == 0
            if has_identity_duplicate_noise:
                domain = SAFE_DOMAINS[(c_idx + 1) % len(SAFE_DOMAINS)]
                email = f"{person.email_base}.alt{c_idx}@{domain}"
            else:
                domain = SAFE_DOMAINS[c_idx % len(SAFE_DOMAINS)]
                email = f"{person.email_base}{c_idx}@{domain}"

            account = ClientAccount(
                client_id=client_id,
                account_id=client_id,
                person_id=person_uuid,
                mt5_login_id=mt5_login_id,
                dp2p_nickname=dp2p_nickname,
                country=country,
                kyc_tier=kyc_tier,
                kyc_approved_at=kyc_approved_at,
                created_at=created_at,
                status=status,
                email=email,
                has_identity_duplicate_noise=has_identity_duplicate_noise,
            )
            self.accounts.append(account)

            # Assign device & IP
            # Family / shared device hard negatives: ~3% share device with previous client
            if c_idx > 0 and c_idx % 30 == 0:
                assigned_device = self.devices[c_idx - 1]
            else:
                assigned_device = self.devices[c_idx]

            assigned_ip = self.ips[c_idx % len(self.ips)]
            self._client_to_devices[client_id] = [assigned_device]
            self._client_to_ips[client_id] = [assigned_ip]

        # 4. Generate Partners
        for p_idx in range(self.partner_count):
            p_uuid = str(uuid.uuid5(namespace, f"partner_{p_idx}"))
            partner_id = f"PT{100000 + p_idx}"
            tier = 1 if p_idx < 10 else (2 if p_idx < 40 else 3)
            parent_id = f"PT{100000 + (p_idx % 10)}" if tier > 1 else None

            self.partners.append(
                Partner(
                    partner_id=partner_id,
                    person_id=p_uuid,
                    tier=tier,
                    parent_partner_id=parent_id,
                    country=COUNTRIES[p_idx % len(COUNTRIES)],
                )
            )

    def get_devices_for_client(self, client_id: str) -> list[Device]:
        return self._client_to_devices.get(client_id, [self.devices[0]])

    def get_ips_for_client(self, client_id: str) -> list[IPAddress]:
        return self._client_to_ips.get(client_id, [self.ips[0]])
