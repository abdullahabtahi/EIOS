"""Tests for Institutional Light-Mode Design Token Registry (Palantir x QBDS)."""

import pytest
from eios.cockpit.tokens import (
    INSTITUTIONAL_LIGHT_TOKENS,
    calculate_contrast_ratio,
    generate_css_custom_properties,
    validate_institutional_palette,
)


def test_institutional_palette_tokens():
    """Verify exact color codes and sharp 0px radius."""
    assert INSTITUTIONAL_LIGHT_TOKENS["surface_ground"] == "#f4f6f8"
    assert INSTITUTIONAL_LIGHT_TOKENS["surface_card"] == "#ffffff"
    assert INSTITUTIONAL_LIGHT_TOKENS["surface_rail"] == "#1c2530"
    assert INSTITUTIONAL_LIGHT_TOKENS["radius_base"] == "0px"
    assert INSTITUTIONAL_LIGHT_TOKENS["text_primary"] == "#0f172a"
    assert INSTITUTIONAL_LIGHT_TOKENS["border_divider"] == "#e2e8f0"


def test_dark_mode_exclusion():
    """Verify that dark mode is strictly prohibited and marked as unsupported."""
    res = validate_institutional_palette()
    assert res["is_pure_light_mode"] is True
    assert res["dark_mode_supported"] is False
    assert res["radius_base"] == "0px"


def test_wcag_aa_contrast_ratios():
    """Verify high-contrast legibility exceeds WCAG 2.2 AA (4.5:1)."""
    text_ratio = calculate_contrast_ratio(
        INSTITUTIONAL_LIGHT_TOKENS["text_primary"],
        INSTITUTIONAL_LIGHT_TOKENS["surface_card"],
    )
    # Slate-900 on pure white is ~15:1
    assert text_ratio >= 12.0
    assert text_ratio >= 4.5

    muted_ratio = calculate_contrast_ratio(
        INSTITUTIONAL_LIGHT_TOKENS["text_muted"],
        INSTITUTIONAL_LIGHT_TOKENS["surface_card"],
    )
    assert muted_ratio >= 4.5

    rail_ratio = calculate_contrast_ratio(
        INSTITUTIONAL_LIGHT_TOKENS["text_on_rail"],
        INSTITUTIONAL_LIGHT_TOKENS["surface_rail"],
    )
    assert rail_ratio >= 4.5


def test_generate_css_custom_properties():
    """Verify CSS variable export contains required token names."""
    css = generate_css_custom_properties()
    assert ":root {" in css
    assert "--surface-ground: #f4f6f8;" in css
    assert "--surface-card: #ffffff;" in css
    assert "--surface-rail: #1c2530;" in css
    assert "--radius-base: 0px;" in css
    assert "--accent-verified: #047857;" in css
    assert "--accent-replay: #b45309;" in css
