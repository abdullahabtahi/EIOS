import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, within, act } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { GovernedActionShelf } from '@/components/cockpit/shell/governed-action-shelf';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';
import { PaneResizer } from '@/components/cockpit/shell/pane-resizer';
import { EXECUTIVE_FIXTURE, getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import type { ActionIntentCard } from '@/components/cockpit/state/cockpit-types';

const card = (id: string, lifecycleState: ActionIntentCard['lifecycleState']): ActionIntentCard => ({
  ...EXECUTIVE_FIXTURE.stagedActionCards[0],
  intentId: id,
  lifecycleState,
});

function mockFetch(cards: ActionIntentCard[]) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ ...getMockWorkstationState('executive'), stagedActionCards: cards }),
  }) as unknown as typeof fetch;
}

function Stager({ action }: { action: ActionIntentCard }) {
  const { stageAction } = useCockpit();
  return <button type="button" data-testid="stage" onClick={() => stageAction(action)} />;
}

describe('Governed Action Shelf: collapsed by default, expands as an overlay drawer', () => {
  beforeEach(() => mockFetch([card('a1', 'EXPIRED'), card('a2', 'STAGED')]));

  it('starts as a slim bar with counts and no cards in the DOM', async () => {
    render(
      <CockpitProvider>
        <GovernedActionShelf />
      </CockpitProvider>,
    );
    await act(async () => {});
    const shelf = screen.getByRole('region', { name: /Governed Action Shelf/i });
    expect(within(shelf).getByText(/2 staged/i)).toBeInTheDocument();
    expect(within(shelf).getByText(/1 expired/i)).toBeInTheDocument();
    expect(within(shelf).queryByTestId('action-card-a1')).not.toBeInTheDocument();
    expect(within(shelf).getByRole('button', { name: /expand/i })).toHaveAttribute('aria-expanded', 'false');
  });

  it('opens a drawer (absolutely positioned, so panes never resize) and shows cards', async () => {
    render(
      <CockpitProvider>
        <GovernedActionShelf />
      </CockpitProvider>,
    );
    await act(async () => {});
    fireEvent.click(screen.getByRole('button', { name: /expand/i }));
    const drawer = document.querySelector('[data-slot="action-drawer"]') as HTMLElement;
    expect(drawer).toBeInTheDocument();
    expect(drawer.className).toMatch(/absolute/);
    expect(within(drawer).getByTestId('action-card-a1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /collapse/i })).toHaveAttribute('aria-expanded', 'true');
  });

  it('auto-opens when an operator stages a new action', async () => {
    mockFetch([]);
    render(
      <CockpitProvider>
        <Stager action={card('fresh', 'STAGED')} />
        <GovernedActionShelf />
      </CockpitProvider>,
    );
    await act(async () => {});
    expect(document.querySelector('[data-slot="action-drawer"]')).not.toBeInTheDocument();
    await act(async () => {
      screen.getByTestId('stage').click();
    });
    expect(screen.getByTestId('action-card-fresh')).toBeInTheDocument();
  });

  it('drops the "Principle II" jargon banner from the bar (kept as a tooltip)', async () => {
    render(
      <CockpitProvider>
        <GovernedActionShelf />
      </CockpitProvider>,
    );
    await act(async () => {});
    expect(screen.queryByText(/Principle II: Two-Phase Commit Required/i)).not.toBeInTheDocument();
  });
});

describe('PaneResizer', () => {
  function Harness({ start = 400 }: { start?: number }) {
    const [w, setW] = React.useState(start);
    return (
      <>
        <PaneResizer label="Resize dossier" value={w} min={300} max={600} defaultValue={420} onChange={setW} />
        <span data-testid="w">{w}</span>
      </>
    );
  }

  it('is an accessible vertical separator exposing its value range', () => {
    render(<Harness />);
    const sep = screen.getByRole('separator', { name: 'Resize dossier' });
    expect(sep).toHaveAttribute('aria-orientation', 'vertical');
    expect(sep).toHaveAttribute('aria-valuenow', '400');
    expect(sep).toHaveAttribute('aria-valuemin', '300');
    expect(sep).toHaveAttribute('aria-valuemax', '600');
    expect(sep).toHaveAttribute('tabindex', '0');
  });

  it('resizes with arrow keys, clamps to bounds, and resets on Enter / double-click', () => {
    render(<Harness />);
    const sep = screen.getByRole('separator');
    fireEvent.keyDown(sep, { key: 'ArrowRight' });
    expect(screen.getByTestId('w')).toHaveTextContent('416');
    fireEvent.keyDown(sep, { key: 'ArrowLeft', shiftKey: true });
    expect(screen.getByTestId('w')).toHaveTextContent('336');
    fireEvent.keyDown(sep, { key: 'Home' });
    expect(screen.getByTestId('w')).toHaveTextContent('300');
    fireEvent.keyDown(sep, { key: 'ArrowLeft' });
    expect(screen.getByTestId('w')).toHaveTextContent('300');
    fireEvent.keyDown(sep, { key: 'End' });
    expect(screen.getByTestId('w')).toHaveTextContent('600');
    fireEvent.doubleClick(sep);
    expect(screen.getByTestId('w')).toHaveTextContent('420');
  });

  it('resizes by dragging with the pointer', () => {
    render(<Harness />);
    const sep = screen.getByRole('separator');
    fireEvent.pointerDown(sep, { clientX: 500, pointerId: 1 });
    fireEvent.pointerMove(window, { clientX: 560 });
    expect(screen.getByTestId('w')).toHaveTextContent('460');
    fireEvent.pointerUp(window);
    fireEvent.pointerMove(window, { clientX: 700 });
    expect(screen.getByTestId('w')).toHaveTextContent('460');
  });
});

describe('Tripartite shell dossier pane is resizable and remembered', () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockFetch([]);
  });

  it('renders a dossier separator and persists a keyboard resize', async () => {
    const { unmount } = render(
      <CockpitProvider>
        <TripartiteShell />
      </CockpitProvider>,
    );
    await act(async () => {});
    const sep = screen.getByRole('separator', { name: /Resize dossier/i });
    const before = Number(sep.getAttribute('aria-valuenow'));
    fireEvent.keyDown(sep, { key: 'ArrowRight' });
    const after = Number(screen.getByRole('separator', { name: /Resize dossier/i }).getAttribute('aria-valuenow'));
    expect(after).toBe(before + 16);
    unmount();

    render(
      <CockpitProvider>
        <TripartiteShell />
      </CockpitProvider>,
    );
    await act(async () => {});
    expect(Number(screen.getByRole('separator', { name: /Resize dossier/i }).getAttribute('aria-valuenow'))).toBe(after);
  });
});
