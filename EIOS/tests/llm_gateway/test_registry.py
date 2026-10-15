import pytest

from eios.llm_gateway.providers.registry import UnknownModelError, load_registry


def test_the_default_is_the_fastest_entry_and_the_browser_never_sees_an_id() -> None:
    registry = load_registry({})
    assert registry.resolve(None).key == registry.choices[0].key == "fast"
    shown = registry.public()
    assert [m["default"] for m in shown] == [True] + [False] * (len(shown) - 1)
    assert all(set(m) == {"key", "label", "note", "default"} for m in shown)


def test_a_turn_can_pick_another_model_by_key() -> None:
    registry = load_registry({})
    assert registry.resolve("deep").id != registry.resolve("fast").id


def test_an_unknown_key_is_refused() -> None:
    with pytest.raises(UnknownModelError):
        load_registry({}).resolve("nope")


def test_the_default_can_be_moved_by_environment_but_not_to_nothing() -> None:
    assert load_registry({"EIOS_ASSISTANT_DEFAULT_MODEL": "deep"}).default_key == "deep"
    with pytest.raises(UnknownModelError):
        load_registry({"EIOS_ASSISTANT_DEFAULT_MODEL": "nope"})
