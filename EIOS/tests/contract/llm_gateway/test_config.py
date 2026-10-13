"""T107: configuration is validated against the schema, tagged, and has no default model."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from eios.common.errors import ConfigError
from eios.llm_gateway.config import GatewayConfig, config_identity, load_config, parse_config
from tests.support.llm_gateway import config_dict, make_config, make_kit
from tests.support.llm_gateway import echo_request as _echo

REPO = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO / "config"
TAGS = ("[BRIEF]", "[ASSUMPTION]", "[ILLUSTRATIVE]", "[TARGET]", "[SPIKE]")


def _without(key: str, *, tag_of: str | None = None) -> dict[str, object]:
    data = copy.deepcopy(config_dict())
    if tag_of is None:
        data.pop(key)
    else:
        verification = data["verification"]
        assert isinstance(verification, dict)
        verification.pop(tag_of)
    return data


def test_valid_config_parses_into_a_frozen_model() -> None:
    config = parse_config(config_dict(), source="test")
    assert isinstance(config, GatewayConfig)
    assert config.daily_token_cap == 1000
    with pytest.raises(ValueError):
        config.daily_token_cap = 5


@pytest.mark.parametrize(
    "key", ["model_id", "prices", "rate_limits", "cap_warning_thresholds_percent"]
)
def test_a_value_without_a_verification_tag_is_rejected_at_load(key: str) -> None:
    with pytest.raises(ConfigError) as caught:
        parse_config(_without(key, tag_of=key), source="x.yaml")
    assert f"verification.{key}" in str(caught.value)
    assert "x.yaml" in str(caught.value)


@pytest.mark.parametrize("bad_tag", ["[VERIFIED]", "SPIKE", "", "[spike]", 5, None])
def test_tags_outside_the_vocabulary_are_rejected(bad_tag: object) -> None:
    data = copy.deepcopy(config_dict())
    data["verification"]["daily_token_cap"] = bad_tag  # type: ignore[index]
    with pytest.raises(ConfigError):
        parse_config(data, source="test")


@pytest.mark.parametrize("tag", TAGS)
def test_every_vocabulary_tag_is_accepted(tag: str) -> None:
    data = copy.deepcopy(config_dict())
    data["verification"]["daily_token_cap"] = tag  # type: ignore[index]
    assert parse_config(data, source="test").verification.daily_token_cap.value == tag


def test_daily_token_cap_and_its_tag_are_required() -> None:
    with pytest.raises(ConfigError):
        parse_config(_without("daily_token_cap"), source="test")
    with pytest.raises(ConfigError):
        parse_config(_without("daily_token_cap", tag_of="daily_token_cap"), source="test")


@pytest.mark.parametrize("cap", [0, -5, 1.5, "100", True])
def test_daily_token_cap_must_be_a_positive_integer(cap: object) -> None:
    with pytest.raises(ConfigError):
        parse_config(config_dict(daily_token_cap=cap), source="test")


@pytest.mark.parametrize("thresholds", [[0], [100], [50, 50], ["a"], [50.5]])
def test_warning_thresholds_must_be_unique_percentages_below_100(thresholds: list[object]) -> None:
    with pytest.raises(ConfigError):
        parse_config(config_dict(cap_warning_thresholds_percent=thresholds), source="test")


def _dev_without_model() -> dict[str, object]:
    data = copy.deepcopy(config_dict())
    data.pop("model_id")
    data["verification"].pop("model_id")  # type: ignore[attr-defined]
    return data


def test_dev_may_omit_model_id_and_there_is_no_default() -> None:
    assert parse_config(_dev_without_model(), source="test").model_id is None


@pytest.mark.parametrize("environment", ["stage", "prod-like"])
def test_deployed_environment_without_model_id_fails_startup(environment: str) -> None:
    data = _dev_without_model()
    data["environment"] = environment
    with pytest.raises(ConfigError) as caught:
        parse_config(data, source="deployed.yaml")
    message = str(caught.value)
    assert "model_id" in message
    assert "deployed.yaml" in message


@pytest.mark.parametrize("environment", ["stage", "prod-like"])
def test_deployed_environment_with_model_id_starts(environment: str) -> None:
    assert parse_config(config_dict(environment=environment), source="t").environment == environment


def test_unknown_environment_unknown_field_and_unsupported_provider_are_rejected() -> None:
    for bad in (
        config_dict(environment="production"),
        config_dict(default_model="x"),
        config_dict(provider="not-a-registered-provider"),
        config_dict(provider=""),
    ):
        with pytest.raises(ConfigError):
            parse_config(bad, source="test")


@pytest.mark.parametrize(
    "prices",
    [
        {"input_per_unit": -1, "output_per_unit": 1, "currency": "USD", "unit": "1000 tokens"},
        {"input_per_unit": 1, "output_per_unit": 1, "currency": "US", "unit": "1000 tokens"},
        {"input_per_unit": 1, "output_per_unit": 1, "currency": "USD", "unit": "per thing"},
        {"input_per_unit": 1, "output_per_unit": 1, "currency": "USD", "unit": "0 tokens"},
        {"input_per_unit": 1, "output_per_unit": 1, "currency": "USD"},
        {
            "input_per_unit": float("inf"),
            "output_per_unit": 1,
            "currency": "USD",
            "unit": "1 tokens",
        },
    ],
)
def test_invalid_prices_are_rejected(prices: dict[str, object]) -> None:
    with pytest.raises(ConfigError):
        parse_config(config_dict(prices=prices), source="test")


def test_errors_never_echo_configured_values() -> None:
    marker = "value-that-must-not-be-echoed"
    with pytest.raises(ConfigError) as caught:
        parse_config(config_dict(environment=marker), source="test")
    assert marker not in str(caught.value)


def test_price_derivation_uses_the_configured_unit() -> None:
    prices = make_config().prices
    assert prices is not None
    assert prices.cost(tokens_in=1000, tokens_out=500) == pytest.approx(
        prices.input_per_unit + prices.output_per_unit / 2
    )
    assert prices.cost(tokens_in=0, tokens_out=0) == 0.0


def test_load_config_reads_a_yaml_file(tmp_path: Path) -> None:
    path = tmp_path / "gw.yaml"
    path.write_text(yaml.safe_dump(config_dict()), encoding="utf-8")
    assert load_config(path).provider == "stub"


@pytest.mark.parametrize("text", ["", "- a\n- b\n", "key: [unclosed", "just a string"])
def test_load_config_rejects_non_mapping_or_unparsable_files(tmp_path: Path, text: str) -> None:
    path = tmp_path / "gw.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        load_config(path)
    assert str(path) in str(caught.value)


def test_load_config_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "absent.yaml")


def test_identity_is_a_stable_hash_that_changes_with_any_value() -> None:
    assert config_identity(make_config()) == config_identity(make_config())
    assert len(config_identity(make_config())) == 64
    assert config_identity(make_config(daily_token_cap=999)) != config_identity(make_config())
    assert config_identity(make_config(model_id="other-stub")) != config_identity(make_config())


def test_changing_model_in_config_changes_what_the_provider_receives(tmp_path: Path) -> None:
    first = make_kit(tmp_path / "a", config=make_config(model_id="stub-model-a"))
    second = make_kit(tmp_path / "b", config=make_config(model_id="stub-model-b"))
    first.gateway.complete(_echo())
    second.gateway.complete(_echo())
    assert first.provider.calls[0][1] == "stub-model-a"
    assert second.provider.calls[0][1] == "stub-model-b"


def test_changing_prices_in_config_changes_trace_cost_without_code_change(tmp_path: Path) -> None:
    cheap = {"input_per_unit": 1.0, "output_per_unit": 1.0, "currency": "USD", "unit": "1 tokens"}
    dear = {**cheap, "input_per_unit": 10.0, "output_per_unit": 10.0}
    a = make_kit(tmp_path / "a", config=make_config(prices=cheap))
    b = make_kit(tmp_path / "b", config=make_config(prices=dear))
    a.gateway.complete(_echo())
    b.gateway.complete(_echo())
    cost_a, cost_b = a.traces.records[0]["cost"], b.traces.records[0]["cost"]
    assert isinstance(cost_a, float) and isinstance(cost_b, float)
    assert cost_b == pytest.approx(cost_a * 10)


@pytest.mark.parametrize("environment", ["stage", "prod-like"])
def test_committed_deployed_configs_fail_startup_while_adr_002_is_open(environment: str) -> None:
    path = CONFIG_DIR / f"llm_gateway.{environment}.yaml"
    with pytest.raises(ConfigError) as caught:
        load_config(path)
    assert "model_id" in str(caught.value)


@pytest.mark.parametrize("environment", ["stage", "prod-like"])
def test_committed_deployed_configs_state_the_omission_is_intentional(environment: str) -> None:
    text = (CONFIG_DIR / f"llm_gateway.{environment}.yaml").read_text(encoding="utf-8")
    assert "intentional" in text.lower()
    assert "ADR-002" in text
    data = yaml.safe_load(text)
    assert "model_id" not in data
    assert data["environment"] == environment


def test_committed_dev_config_loads_with_a_stub_provider_and_every_value_tagged() -> None:
    config = load_config(CONFIG_DIR / "llm_gateway.dev.yaml")
    assert config.environment == "dev"
    assert config.provider == "stub"
    assert config.model_id
    raw = yaml.safe_load((CONFIG_DIR / "llm_gateway.dev.yaml").read_text(encoding="utf-8"))
    assert set(raw["verification"].values()) <= set(TAGS)
    assert config.cap_warning_thresholds_percent == (50, 80)
