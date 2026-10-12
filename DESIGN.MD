# FEIOS Design System

## The Visual World: Sovereign Light

This document outlines the strict visual constraints for the **Financial Enterprise Intelligence Operating System (FEIOS)**. The aesthetic is institutional, high-trust, editorial, and starkly analytical—specifically the "Sovereign Light" mode. It is designed to feel like an institutional executive intelligence dossier merged with a high-performance operating system.

### Core Philosophy
- **Light Mode Only**: The interface is strictly 100% light mode.
- **Data over Chrome**: UI borders are subtle (`var(--color-border)`), backgrounds are pristine (`#fafafa` paper-white), and content is the focal point.
- **No Glows or Neons**: Eliminate all cyber-slop (drop-shadow glows, neon cyan/magenta).
- **Subtle Micro-interactions**: Animations are limited to polished, expensive-feeling snappy state changes (`ease-out`, 150-250ms).

### 1. Typography
- **Headlines**: Inter, Helvetica, or system sans-serif (Alliance fallbacks). Tight tracking, high contrast (`#111111`).
- **Body**: Minimalist sans-serif (`#444444`). High readability.
- **Monospace/Numbers**: IBM Plex Mono or standard monospace for metrics, hashes, and code blocks (`#222222`).

### 2. Color Palette (Light Mode)

#### Backgrounds
- `background`: `#fdfdfd` (Pristine, almost-white with a hint of warmth)
- `surface-base`: `#ffffff` (Pure white for elevated cards)
- `surface-raised`: `#f5f5f5` (For subtle offset containers)

#### Text & Strokes
- `brand-primary`: `#111111` (Deep charcoal, nearly black for headlines and primary text)
- `brand-secondary`: `#666666` (Medium gray for secondary text and metadata)
- `brand-tertiary`: `#999999` (Light gray for disabled states and subtle labels)
- `border`: `#e5e5e5` (Soft, barely-there structural borders)

#### Status / Accents (Subtle & Professional)
- `status-success`: `#0e6935` (Deep, trusted green)
- `status-warning`: `#b36b00` (Earthy, institutional gold)
- `status-danger`: `#a11f1f` (Muted crimson)
- `brand-accent`: `#1c4587` (A deep, institutional navy blue for primary CTA highlights, replacing any bright cyan)

### 3. Structural Rules
- **Spacing**: Strict 4px/8px baseline grid (`var(--spacing-md)` = `24px`).
- **Borders**: 1px solid `#e5e5e5`. No gradients on borders.
- **Shadows**: Extremely subtle and realistic. Drop shadows are used strictly for elevation (`shadow-sm`, `shadow-md` for modals), never for glows.
- **Radii**: 2px or 4px (`var(--radius-sm)`, `var(--radius-md)`). Square, sharp, institutional corners.

### 4. Animations
- **Durations**: Fast (150ms to 300ms max).
- **Easing**: Crisp (`cubic-bezier(0.2, 0, 0, 1)` or standard `ease-out`).
- **Properties**: Opacity (fades) and Transform (slight scale or Y-translate). No continuous pulsing or spinning (unless specifically loading data).

### Usage Notes for Agents
Before editing any component, reference these tokens. Do not introduce raw Hex values in components; always map to the `var(--color-...)` tokens defined in `globals.css`. Ensure everything feels light, airy, and hyper-professional.