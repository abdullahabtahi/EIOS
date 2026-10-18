import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within, act } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';
import { AppNavRail } from '@/components/cockpit/shell/app-nav-rail';
import { APP_HOME_HREF } from '@/components/cockpit/shell/app-nav-items';

const OPEN_INTENT_MS = 120;
const CLOSE_GRACE_MS = 280;

function Probe() {
  const { state, toggleSimulatedOutage } = useCockpit();
  return (
    <>
      <span data-testid="active-role">{state.activeRole}</span>
      <span data-testid="command-open">{state.dossierView}</span>
      <button type="button" data-testid="force-outage" onClick={() => toggleSimulatedOutage(true)} />
    </>
  );
}

function renderRail(props: React.ComponentProps<typeof AppNavRail> = {}) {
  return render(
    <CockpitProvider>
      <AppNavRail {...props} />
      <Probe />
    </CockpitProvider>,
  );
}

const rail = () => document.querySelector('[data-slot="app-nav-rail"]') as HTMLElement;

function hoverRail() {
  fireEvent.pointerEnter(rail());
  act(() => {
    vi.advanceTimersByTime(OPEN_INTENT_MS + 1);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe('AppNavRail: always-visible icon strip that expands on hover', () => {
  it('is present and operable at rest (collapsed, not hidden or inert)', () => {
    renderRail();
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
    expect(rail()).not.toHaveAttribute('inert');
    expect(rail()).not.toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByRole('button', { name: /Workstations/ })).toBeInTheDocument();
  });

  it('dims the workspace behind the expanded panel so it reads as an intentional layer', () => {
    renderRail();
    const scrim = () => document.querySelector('[data-slot="app-nav-scrim"]') as HTMLElement;
    expect(scrim()).toHaveAttribute('data-state', 'collapsed');
    expect(scrim()).toHaveAttribute('aria-hidden', 'true');
    hoverRail();
    expect(scrim()).toHaveAttribute('data-state', 'expanded');
  });

  it('no longer renders the old edge tab or hot zone', () => {
    renderRail();
    expect(screen.queryByRole('button', { name: 'Open navigation' })).not.toBeInTheDocument();
    expect(document.querySelector('[data-slot="app-nav-hotzone"]')).not.toBeInTheDocument();
  });

  it('expands after hover intent', () => {
    renderRail();
    fireEvent.pointerEnter(rail());
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
    act(() => {
      vi.advanceTimersByTime(OPEN_INTENT_MS + 1);
    });
    expect(rail()).toHaveAttribute('data-state', 'expanded');
  });

  it('does not expand if the pointer leaves before intent elapses', () => {
    renderRail();
    fireEvent.pointerEnter(rail());
    fireEvent.pointerLeave(rail());
    act(() => {
      vi.advanceTimersByTime(OPEN_INTENT_MS * 3);
    });
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
  });

  it('expands immediately when keyboard focus enters the strip', () => {
    renderRail();
    fireEvent.focus(screen.getByRole('button', { name: /Workstations/ }));
    expect(rail()).toHaveAttribute('data-state', 'expanded');
  });

  it('collapses after a grace period once the pointer leaves, and stays open if it returns', () => {
    renderRail();
    hoverRail();
    fireEvent.pointerLeave(rail());
    act(() => {
      vi.advanceTimersByTime(CLOSE_GRACE_MS - 50);
    });
    fireEvent.pointerEnter(rail());
    act(() => {
      vi.advanceTimersByTime(CLOSE_GRACE_MS * 2);
    });
    expect(rail()).toHaveAttribute('data-state', 'expanded');

    fireEvent.pointerLeave(rail());
    act(() => {
      vi.advanceTimersByTime(CLOSE_GRACE_MS + 1);
    });
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
  });

  it('collapses on Escape', () => {
    renderRail();
    hoverRail();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
  });

  it('toggles with the backslash key and ignores it while typing in a field', () => {
    render(
      <CockpitProvider>
        <AppNavRail />
        <input data-testid="field" />
      </CockpitProvider>,
    );
    fireEvent.keyDown(window, { key: '\\' });
    expect(rail()).toHaveAttribute('data-state', 'expanded');
    fireEvent.keyDown(window, { key: '\\' });
    expect(rail()).toHaveAttribute('data-state', 'collapsed');

    fireEvent.keyDown(screen.getByTestId('field'), { key: '\\' });
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
  });

  it('collapses on an outside pointer press (touch)', () => {
    renderRail();
    hoverRail();
    fireEvent.pointerDown(document.body);
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
  });
});

describe('AppNavRail: content', () => {
  it('lists Workstations, a Geospatial link, and OpenBB flagged SOON', () => {
    renderRail();
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(nav).getByRole('button', { name: /Workstations/ })).toBeInTheDocument();
    const geo = within(nav).getByRole('link', { name: /Geospatial/ });
    expect(geo).toHaveAttribute('href', '/cockpit/geospatial');
    expect(within(geo).queryByText('SOON')).not.toBeInTheDocument();
    const bb = within(nav).getByRole('button', { name: /OpenBB/ });
    expect(bb).toHaveAttribute('aria-disabled', 'true');
    expect(within(bb).getByText('SOON')).toBeInTheDocument();
  });

  it('lists Geospatial first, then Workstations, and lands sign-in on the first section', () => {
    renderRail();
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    const ids = within(nav)
      .getAllByTestId(/^nav-app-/)
      .map((el) => el.getAttribute('data-testid'));
    expect(ids).toEqual(['nav-app-geospatial', 'nav-app-workstations', 'nav-app-openbb']);
    expect(APP_HOME_HREF).toBe('/cockpit/geospatial');
  });

  it('marks the section it is told is current, and links back to the cockpit from elsewhere', () => {
    renderRail({ currentId: 'geospatial' });
    expect(screen.getByTestId('nav-app-geospatial')).toHaveAttribute('aria-current', 'page');
    expect(screen.getByTestId('nav-app-workstations')).toHaveAttribute('href', '/cockpit');
  });

  it('does not duplicate the header persona switcher (no per-persona rows)', () => {
    renderRail();
    expect(screen.queryByTestId('nav-workstation-executive')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /AML Investigator/ })).not.toBeInTheDocument();
  });

  it('marks Workstations current; selecting it keeps the persona and collapses the rail', () => {
    renderRail();
    hoverRail();
    const ws = screen.getByTestId('nav-app-workstations');
    expect(ws).toHaveAttribute('aria-current', 'page');
    fireEvent.click(ws);
    expect(screen.getByTestId('active-role')).toHaveTextContent('executive');
    expect(rail()).toHaveAttribute('data-state', 'collapsed');
  });

  it('does nothing when a SOON section is clicked', () => {
    renderRail();
    fireEvent.click(screen.getByRole('button', { name: /OpenBB/ }));
    expect(screen.getByTestId('active-role')).toHaveTextContent('executive');
  });

  it('shows operator identity and live pipeline telemetry', () => {
    renderRail();
    expect(within(rail()).getByTestId('nav-pipeline-status')).toHaveTextContent(/Pipeline:\s*(Live|Syncing)/);
    expect(within(rail()).getByTestId('nav-pipeline-status')).toHaveTextContent(/RTT/);
    expect(within(rail()).getByTestId('nav-operator-name')).not.toBeEmptyDOMElement();
  });

  it('reports Replay when an outage is simulated', () => {
    renderRail();
    fireEvent.click(screen.getByTestId('force-outage'));
    expect(within(rail()).getByTestId('nav-pipeline-status')).toHaveTextContent(/Replay/);
  });

  it('Ask copilot works straight from the collapsed strip', () => {
    renderRail();
    fireEvent.click(within(rail()).getByRole('button', { name: /Ask copilot/ }));
    expect(screen.getByTestId('command-open')).toHaveTextContent('chat');
  });

  it('Keyboard Shortcuts works straight from the collapsed strip', () => {
    const onOpenShortcuts = vi.fn();
    renderRail({ onOpenShortcuts });
    fireEvent.click(within(rail()).getByRole('button', { name: /Keyboard Shortcuts/ }));
    expect(onOpenShortcuts).toHaveBeenCalledTimes(1);
  });
});

describe('AppNavRail inside the cockpit shell', () => {
  it('sits at the left edge beside the header column without displacing the persona strip', () => {
    render(
      <CockpitProvider>
        <TripartiteShell />
      </CockpitProvider>,
    );
    expect(document.querySelector('[data-slot="app-nav-rail"]')).toBeInTheDocument();
    expect(screen.getByTestId('tab-executive')).toBeInTheDocument();
    expect(screen.getByTestId('tab-data_operations')).toBeInTheDocument();
  });
});
