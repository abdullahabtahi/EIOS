"""Tests for sealed tier CI environment protection and distribution shifts (SC-009)."""

import os
from unittest import mock

import pytest

from eios.foundry.manifest import validate_manifest_dict


def test_sealed_tier_local_blocked() -> None:
    data = {
        "manifest_id": "123e4567-e89b-12d3-a456-426614174000",
        "manifest_version": "1.0.0",
        "seed": 9001,
        "seed_tier": "sealed",
        "git_sha": "a" * 40,
        "spec_hash": "b" * 64,
        "generator_versions": {
            "gen_client": "1.0.0",
            "gen_aml": "1.0.0",
            "gen_partner": "1.0.0",
            "gen_financial": "1.0.0",
            "gen_competitive": "1.0.0",
            "gen_operational": "1.0.0",
            "gen_causal_truth": "1.0.0",
        },
        "dataset_hash": "c" * 64,
        "generated_at": "2026-10-02T12:00:00Z",
    }
    with mock.patch.dict(os.environ, {}, clear=True):
        with pytest.raises(PermissionError, match="Sealed datasets can only be generated in CI"):
            validate_manifest_dict(data)


def test_sealed_tier_ci_allowed() -> None:
    data = {
        "manifest_id": "123e4567-e89b-12d3-a456-426614174000",
        "manifest_version": "1.0.0",
        "seed": 9001,
        "seed_tier": "sealed",
        "git_sha": "a" * 40,
        "spec_hash": "b" * 64,
        "generator_versions": {
            "gen_client": "1.0.0",
            "gen_aml": "1.0.0",
            "gen_partner": "1.0.0",
            "gen_financial": "1.0.0",
            "gen_competitive": "1.0.0",
            "gen_operational": "1.0.0",
            "gen_causal_truth": "1.0.0",
        },
        "dataset_hash": "c" * 64,
        "generated_at": "2026-10-02T12:00:00Z",
    }
    with mock.patch.dict(os.environ, {"CI_RELEASE_CANDIDATE": "true"}):
        manifest = validate_manifest_dict(data)
        assert manifest.seed_tier == "sealed"
