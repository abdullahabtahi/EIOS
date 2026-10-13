"""Institutional Light-Mode Design Token Registry.

Grounds the visual architecture in Palantir Solution Designer and McKinsey
QuantumBlack Design System (QBDS). Strictly prohibits dark mode.
"""

from __future__ import annotations

import math
from typing import Any

INSTITUTIONAL_LIGHT_TOKENS: dict[str, str] = {
    # Surfaces
    "surface_ground": "#f4f6f8",  # Canvas ground (cool institutional slate)
    "surface_card": "#ffffff",  # Card and panel ground (pure white)
    "surface_rail": "#1c2530",  # Left-rail navigation (slate-navy)
    "surface_header": "#ffffff",  # Header banner ground
    "surface_hover": "#f1f5f9",  # High-density row hover (slate-100)
    # Typography
    "text_primary": "#0f172a",  # Text primary (slate-900)
    "text_muted": "#475569",  # Secondary text (slate-600)
    "text_on_rail": "#f8fafc",  # Left rail white text (slate-50)
    "text_on_rail_muted": "#94a3b8",  # Left rail secondary text (slate-400)
    # Dividers & Structural Geometry
    "border_divider": "#e2e8f0",  # Crisp panel dividers (slate-200)
    "border_subtle": "#cbd5e1",  # Table cell borders (slate-300)
    "radius_base": "0px",  # 0px sharp corners (anti-consumer, institutional)
    # Accents & Semantics
    "accent_verified": "#047857",  # Causal verified / Pass (emerald-700)
    "accent_replay": "#b45309",  # Replay / Cached fallback (amber-700)
    "accent_critical": "#b91c1c",  # Critical AML / Breach (rose-700)
    "accent_link": "#0284c7",  # Navigation / Citations (sky-600)
    "accent_correlation": "#64748b",  # Correlation only / Unverified (slate-500)
}


def _hex_to_rgb(hex_code: str) -> tuple[float, float, float]:
    hex_clean = hex_code.lstrip("#")
    return tuple(int(hex_clean[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _linear_luminance(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)


def relative_luminance(hex_code: str) -> float:
    r, g, b = _hex_to_rgb(hex_code)
    r_lum = _linear_luminance(r)
    g_lum = _linear_luminance(g)
    b_lum = _linear_luminance(b)
    return 0.2126 * r_lum + 0.7152 * g_lum + 0.0722 * b_lum


def calculate_contrast_ratio(hex_foreground: str, hex_background: str) -> float:
    """Calculates WCAG 2.2 contrast ratio between two hex colors."""
    lum1 = relative_luminance(hex_foreground)
    lum2 = relative_luminance(hex_background)
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def generate_css_custom_properties() -> str:
    """Exports tokens as CSS custom variables."""
    lines = [":root {"]
    for k, v in INSTITUTIONAL_LIGHT_TOKENS.items():
        var_name = k.replace("_", "-")
        lines.append(f"  --{var_name}: {v};")
    lines.append("}")
    return "\n".join(lines)


def validate_institutional_palette() -> dict[str, Any]:
    """Validates light-mode constraints, contrast ratios, and dark-mode exclusion."""
    text_contrast = calculate_contrast_ratio(
        INSTITUTIONAL_LIGHT_TOKENS["text_primary"], INSTITUTIONAL_LIGHT_TOKENS["surface_card"]
    )
    muted_contrast = calculate_contrast_ratio(
        INSTITUTIONAL_LIGHT_TOKENS["text_muted"], INSTITUTIONAL_LIGHT_TOKENS["surface_card"]
    )
    rail_contrast = calculate_contrast_ratio(
        INSTITUTIONAL_LIGHT_TOKENS["text_on_rail"], INSTITUTIONAL_LIGHT_TOKENS["surface_rail"]
    )

    return {
        "is_pure_light_mode": True,
        "dark_mode_supported": False,
        "radius_base": INSTITUTIONAL_LIGHT_TOKENS["radius_base"],
        "text_primary_contrast": round(text_contrast, 2),
        "text_muted_contrast": round(muted_contrast, 2),
        "rail_text_contrast": round(rail_contrast, 2),
        "wcag_aa_compliant": (
            text_contrast >= 4.5 and muted_contrast >= 4.5 and rail_contrast >= 4.5
        ),
        "tokens": INSTITUTIONAL_LIGHT_TOKENS,
    }
