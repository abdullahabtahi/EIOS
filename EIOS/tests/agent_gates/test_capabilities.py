"""Capability map tests (T009): cases name capabilities, never tools; no role can approve or execute."""

from eios.agent_gates.capabilities import FORBIDDEN_AGENT_TOOLS, Availability, default_map


def test_copilot_tools_resolve_to_capabilities() -> None:
    cmap = default_map()
    assert cmap.capability_for_tool("copilot", "inspect_aml_entity") == "aml.dossier"
    assert cmap.capability_for_tool("copilot", "get_governed_metric") == "metric.get"
    assert cmap.capability_for_tool("copilot", "no_such_tool") is None


def test_a_capability_the_runtime_lacks_is_reported_missing_not_passed() -> None:
    cmap = default_map()
    assert cmap.availability("copilot", "aml.timeline") is Availability.CAPABILITY_MISSING
    assert cmap.availability("copilot", "aml.dossier") is Availability.AVAILABLE
    assert cmap.availability("target", "aml.timeline") is Availability.AVAILABLE


def test_the_copilots_retrieval_tools_are_marked_fixture_only() -> None:
    cmap = default_map()
    assert cmap.availability("copilot", "knowledge.regulation") is Availability.FIXTURE_ONLY


def test_no_capability_or_role_toolset_can_approve_or_execute() -> None:
    cmap = default_map()
    for cap in cmap.capabilities.values():
        for tool in (cap.copilot, cap.target):
            assert tool not in FORBIDDEN_AGENT_TOOLS
        assert not cap.id.startswith(("action.approve", "action.execute"))
    for role, caps in cmap.roles.items():
        assert not [c for c in caps if c.startswith(("action.approve", "action.execute"))], role


def test_every_role_capability_exists_and_toolsets_stay_small() -> None:
    cmap = default_map()
    for role, caps in cmap.roles.items():
        assert set(caps) <= set(cmap.capabilities), role
        assert len(caps) <= 13, f"{role} has {len(caps)} capabilities"
