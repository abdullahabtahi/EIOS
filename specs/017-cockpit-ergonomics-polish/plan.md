# Implementation Plan: Institutional Cockpit Ergonomics, Sovereign Light & Tripartite Synchronization (017-cockpit-ergonomics-polish)

**Branch**: `017-cockpit-ergonomics-polish` | **Date**: 2026-10-10 | **Spec**: [specs/017-cockpit-ergonomics-polish/spec.md](spec.md)

---

## 1. Summary

Implement a focused design-and-architecture upgrade to FEIOS Operator Cockpit addressing the 4 priority findings from the Impeccable critique:
1. **Spatial Fluidity**: Transform fixed 300px + 560px panels into responsive flex allocations (`w-72 2xl:w-80` rail, `w-[440px] xl:w-[480px] 2xl:w-[540px]` dossier, `flex-1 min-w-[460px]` canvas) with universal collapse controls (`lg:flex`) eliminating 1280px canvas cramping.
2. **100% Palantir Sovereign Light Shell Chrome**: Re-theme `HeaderNav` and `GovernedActionShelf` from dark slate (`#0f172a`/`#020617`) to pure institutional light mode (`#ffffff` surface, `#e2e8f0` structural dividers, `#0f172a` text, `#106ba3` active states).
3. **Tripartite State Synchronization**: Unify selected triage item state so selecting an entity in Left Rail coordinates the Center Dossier and Right Kinetic Canvas in real time.
4. **Tactile What-If Affordances & Shortcuts**: Provide a "Reset to Baseline (0 bps)" snap button, preset chips (`-25 bps`, `0 bps`, `+25 bps`), global keyboard listeners (`[`, `]`, `?`), and a sleek Shortcuts modal.
5. **Craft-Floor Browser Surfaces**: Themed slim scrollbars (`scrollbar-thin`), `tabular-nums` on figures, and WCAG 2.2 AA compliant focus rings.

---

## 2. Technical Context

* **Frontend**: Next.js 16 (App Router), React 19, TypeScript 5.8, Tailwind CSS v4, Lucide / Material Symbols Sharp.
* **Testing**: Vitest (`bun run test`), TypeScript (`bun x tsc --noEmit`), Chrome DevTools MCP browser testing.
* **Backend**: Python 3.14, FastAPI, Pytest (`pytest tests/cockpit/ -v`).
* **Design System**: Palantir Sovereign Light Mode, 0px sharp radii, `#ffffff` card surfaces, `#f4f6f8` ground, `#e2e8f0` structural hairline borders.

---

## 3. Component Architecture & State Flow

```mermaid
graph TD
    subgraph Cockpit Context State
        State[CockpitState: activeRole, selectedTriageId, leftRailCollapsed, rightCanvasCollapsed, isSimulatedOutage]
        SelectAction[selectTriageItem(id)] --> |Synchronizes| ActiveDossier[Active Dossier Payload]
        SelectAction --> |Highlights Node| CanvasState[Kinetic Canvas Focused Node]
    end

    subgraph Shell Presentation
        Header[HeaderNav: Pure Sovereign Light #ffffff]
        LeftRail[TriageRail: w-72 2xl:w-80 + Collapse Chevron]
        CenterDossier[CopilotDossier: w-[440px]-w-[540px] + Custom Scrollbars]
        RightCanvas[KineticCanvas: flex-1 min-w-[460px] + Auto-fit Grid]
        ActionShelf[GovernedActionShelf: Pure Sovereign Light #ffffff Two-Phase Tray]
        ShortcutsModal[KeyboardShortcutsModal: ?, [, ], 1-5, Cmd+K]
    end

    State --> Header
    State --> LeftRail
    State --> CenterDossier
    State --> RightCanvas
    State --> ActionShelf
    State --> ShortcutsModal
```

---

## 4. Affected Files & Touchpoints

1. [`FEIOS/web-prototype/src/components/cockpit/shell/header-nav.tsx`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/components/cockpit/shell/header-nav.tsx)
   - Re-theme from dark slate (`bg-slate-900 border-slate-700 text-white`) to light mode (`bg-white border-b border-slate-200 text-slate-900`).
   - Clean light telemetry badge with pulsing emerald indicator and dark tabular figures.
   - Distinct cobalt underline/pill for active persona tabs.
   - Add keyboard shortcut trigger (`?` Help icon button).

2. [`FEIOS/web-prototype/src/components/cockpit/shell/governed-action-shelf.tsx`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/components/cockpit/shell/governed-action-shelf.tsx)
   - Re-theme from dark slate (`bg-slate-900 text-white`) to light mode (`bg-white border-t border-slate-300 text-slate-900 shadow-md`).
   - Action intent cards render on `#ffffff` with `#e2e8f0` borders, `#0f172a` titles, `#0d8050` verified signatures, and clear primary/secondary buttons.
   - Add confirmation state for `Clear All`.

3. [`FEIOS/web-prototype/src/components/cockpit/shell/tripartite-shell.tsx`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/components/cockpit/shell/tripartite-shell.tsx)
   - Adjust widths: Left rail `w-72 2xl:w-80`, Center dossier `w-[440px] xl:w-[480px] 2xl:w-[540px]`, Right canvas `flex-1 min-w-[460px]`.
   - Update collapse chevron classes from `hidden 2xl:flex` to `hidden lg:flex` so collapse is universally accessible on all screens $\ge 1024\text{px}$.
   - Add global keyboard event listeners for `[` (toggle left rail), `]` (toggle right canvas), and `?` (open shortcuts modal).

4. [`FEIOS/web-prototype/src/components/cockpit/shell/kinetic-canvas.tsx`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/components/cockpit/shell/kinetic-canvas.tsx)
   - Prevent header wrapping on viewports $\le 1366\text{px}$.
   - Make telemetry cards and Red-Line test cards use responsive auto-fit grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`) to prevent text truncation.

5. [`FEIOS/web-prototype/src/components/cockpit/common/what-if-slider.tsx`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/components/cockpit/common/what-if-slider.tsx)
   - Add "Reset to Baseline (0 bps)" snap button.
   - Add preset buttons for `-25 bps`, `0 bps`, `+25 bps`.

6. [`FEIOS/web-prototype/src/components/cockpit/common/keyboard-shortcuts-modal.tsx`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/components/cockpit/common/keyboard-shortcuts-modal.tsx)
   - New institutional modal displaying operational keybindings with Esc to dismiss.

7. [`FEIOS/web-prototype/src/components/cockpit/state/cockpit-context.tsx`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/components/cockpit/state/cockpit-context.tsx)
   - Enhance `selectTriageItem` to synchronize selected entity ID across active dossier and kinetic canvas focused node.

8. [`FEIOS/web-prototype/src/app/globals.css`](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/web-prototype/src/app/globals.css)
   - Add custom hairline scrollbar utilities (`scrollbar-thin`, `scrollbar-thumb-slate-300`, `scrollbar-track-transparent`).

---

## 5. Verification & Testing Plan

1. **Vitest Unit/Component Tests**: Update or add tests verifying new controls (What-If reset button, keyboard shortcuts, light shell classes). Ensure all 19+ tests pass.
2. **TypeScript Compilation**: `bun x tsc --noEmit` must pass with 0 errors.
3. **Backend Tests**: `pytest tests/cockpit/ -v` must pass 58/58 tests.
4. **Live Browser Verification (Chrome DevTools MCP)**:
   - Verify layout at $1280 \times 800$ (no wrap, no overflow, no truncation).
   - Verify panel collapse via chevrons and keyboard shortcuts (`[`, `]`).
   - Verify 100% Palantir Sovereign Light visual harmony (take screenshot).
   - Verify What-If reset button snaps slider back to 0.
   - Verify `impeccable detect` returns 0 violations.
