"""Map commands: the map moves only to an object a tool of the same turn returned, like a figure."""

from __future__ import annotations

from eios.assistant.map_commands import MAX_MAP_COMMANDS, extract, target_key, targets_of

TARGETS = {
    target_key("gateway", "GW-NG-X00"),
    target_key("account", "CR11568"),
    target_key("corridor", "ID>MM"),
    target_key("country", "NG"),
}


def test_a_returned_target_becomes_a_command_and_leaves_the_text() -> None:
    out = extract(
        "The exit in Nigeria {{map:gateway:GW-NG-X00}} is shared by many accounts.", TARGETS
    )
    assert out.problems == ()
    assert out.commands == ({"kind": "gateway", "id": "GW-NG-X00"},)
    assert out.text == "The exit in Nigeria is shared by many accounts."


def test_an_id_is_matched_whatever_its_case_and_repeats_count_once() -> None:
    out = extract(
        "See {{map:account:cr11568}} and again {{map:account:CR11568}}. Then {{map:corridor:ID>MM}}.",
        TARGETS,
    )
    assert out.problems == ()
    assert out.commands == (
        {"kind": "account", "id": "CR11568"},
        {"kind": "corridor", "id": "ID>MM"},
    )


def test_an_object_no_tool_returned_sends_the_draft_back() -> None:
    out = extract("Look at {{map:gateway:GW-IQ-X02}}.", TARGETS)
    assert out.commands == ()
    assert out.problems and "not returned by a tool in this turn" in out.problems[0]


def test_an_unknown_kind_is_refused_and_named() -> None:
    out = extract("Zoom {{map:coordinates:3.1,101.7}}.", TARGETS)
    assert out.commands == () and "coordinates" in out.problems[0]


def test_too_many_moves_are_refused() -> None:
    many = " ".join(f"{{{{map:{t}}}}}" for t in sorted(TARGETS))
    assert len(TARGETS) > MAX_MAP_COMMANDS
    assert any("at most" in p for p in extract(many, TARGETS).problems)


def test_no_targets_means_no_command_is_ever_accepted() -> None:
    out = extract("{{map:country:NG}}", set())
    assert out.commands == () and out.problems


def test_targets_come_only_from_a_trusted_result() -> None:
    payload = {
        "map_targets": [
            {"kind": "gateway", "target_id": "GW-NG-X00"},
            {"kind": "planet", "target_id": "X"},
        ]
    }
    assert targets_of(payload) == {"gateway:GW-NG-X00"}
    assert targets_of({**payload, "untrusted": True}) == set()
    assert targets_of({"capability": "aml.dossier"}) == set()
