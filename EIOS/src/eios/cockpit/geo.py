"""Geospatial reference endpoint: real public layers (boundaries, FATF lists, offshore-structure counts, indicators).

Served from the warm tier's `warm_reference` dataset. When the warehouse is not configured the answer is a plain 503
`reference_unavailable`: a map with no data says so, it never invents any (docs/geospatial-milestones.md M1).
"""

from __future__ import annotations

import functools
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from eios.cockpit.auth import current_operator
from eios.cockpit.geo_account import account_payload
from eios.cockpit.geo_address import address_payload
from eios.cockpit.geo_view import flows_payload
from eios.dataplane.geo_plane import geo_snapshot, graph_store
from eios.netintel.store import NetUnavailable, SnapshotReader
from eios.netintel.store import reader_from_env as net_reader_from_env
from eios.reference.reader import ReferenceReader, ReferenceUnavailable, reader_from_env

_LOG = logging.getLogger("eios.cockpit.geo")
GEO_REFERENCE_PATH = "/api/cockpit/geo/reference"
GEO_FLOWS_PATH = "/api/cockpit/geo/flows"
GEO_ACCOUNT_PATH = "/api/cockpit/geo/accounts/{account_id}"
GEO_ADDRESS_PATH = "/api/cockpit/geo/address"
_ACCOUNT_ID = re.compile(r"^[A-Z]{2}[0-9]{3,8}$")

router = APIRouter(tags=["Cockpit Geo"], dependencies=[Depends(current_operator)])


@functools.cache
def get_reader() -> ReferenceReader | None:
    return reader_from_env()


@router.get(GEO_REFERENCE_PATH)
def geo_reference(reader: ReferenceReader | None = Depends(get_reader)) -> dict[str, Any]:
    if reader is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="reference_unavailable")
    try:
        return reader.world()
    except ReferenceUnavailable as exc:
        _LOG.warning("reference layer unavailable: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="reference_unavailable"
        ) from exc
    except Exception as exc:  # the warehouse failed: say offline, never a partial map
        _LOG.exception("reference layer read failed")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="reference_unavailable"
        ) from exc


@router.get(GEO_FLOWS_PATH)
def geo_flows() -> dict[str, Any]:
    """Customer flows from the geo engine. No engine plane (fixture mode) or a failed build is a plain 503."""
    try:
        snapshot = geo_snapshot()
    except Exception as exc:  # never serve a partial or guessed picture
        _LOG.exception("geo engine build failed")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="geo_unavailable") from exc
    if snapshot is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="geo_unavailable")
    return flows_payload(snapshot)


@router.get(GEO_ACCOUNT_PATH)
def geo_account(account_id: str) -> dict[str, Any]:
    """One account's geography as case evidence. Unknown account is 404; no engine plane is a plain 503."""
    if not _ACCOUNT_ID.match(account_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="unknown_account")
    try:
        snapshot = geo_snapshot()
    except Exception as exc:
        _LOG.exception("geo engine build failed")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="geo_unavailable") from exc
    if snapshot is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="geo_unavailable")
    payload = account_payload(snapshot, account_id, graph_store())
    if payload is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="unknown_account")
    return payload


class AddressQuery(BaseModel):
    address: str = Field(max_length=64)


@functools.cache
def get_net_reader() -> SnapshotReader | None:
    return net_reader_from_env()


@router.post(GEO_ADDRESS_PATH)
def geo_address(
    query: AddressQuery, reader: SnapshotReader | None = Depends(get_net_reader)
) -> dict[str, Any]:
    """What the network reference says about one address. It is a POST so the address stays out of URLs and access
    logs, and nothing on this path logs it: an investigator may be typing a suspect's address."""
    if reader is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="address_check_unavailable")
    try:
        snapshot = reader.snapshot()
    except NetUnavailable as exc:
        _LOG.warning("address-check snapshot unavailable: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="address_check_unavailable"
        ) from exc
    except Exception as exc:
        _LOG.exception("address-check snapshot could not be read")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="address_check_unavailable"
        ) from exc
    try:
        return address_payload(snapshot.lookup(query.address))
    except (
        ValueError
    ):  # not an IP address; the message would repeat the input, so it is not passed on
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_an_ip_address"
        ) from None
