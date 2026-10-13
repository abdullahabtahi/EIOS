"""Tests for isolated ground truth store access and IAM role simulation (SC-004)."""

from pathlib import Path

import pytest

from eios.foundry.storage.eval_truth_store import AccessDeniedError, EvalTruthStore


def test_eval_truth_store_iam_access_control(tmp_path: Path) -> None:
    store = EvalTruthStore(base_dir=tmp_path / "eval_truth")

    # Store some ground truth
    store.write_truth("test_manifest", {"key": "secret_label"})

    # Eval harness identity can read
    data = store.read_truth("test_manifest", role="eval-harness")
    assert data["key"] == "secret_label"

    # Reasoning mesh identity MUST be denied
    with pytest.raises(AccessDeniedError, match="Access to eval-truth denied"):
        store.read_truth("test_manifest", role="reasoning-mesh")

    # Cockpit API identity MUST be denied
    with pytest.raises(AccessDeniedError, match="Access to eval-truth denied"):
        store.read_truth("test_manifest", role="cockpit-api")
