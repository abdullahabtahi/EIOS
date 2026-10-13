import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within, act } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { KineticCanvas } from '@/components/cockpit/shell/kinetic-canvas';

function RoleSwitch() {
  const { setRole } = useCockpit();
  return <button type="button" data-testid="to-ops" onClick={() => setRole('data_operations')} />;
}

function renderCanvas(props: React.ComponentProps<typeof KineticCanvas> = {}) {
  return render(
    <CockpitProvider>
      <RoleSwitch />
      <KineticCanvas {...props} />
    </CockpitProvider>,
  );
}

const tabs = () => within(screen.getByRole('tablist', { name: /canvas sections/i })).getAllByRole('tab');

describe('Kinetic Canvas studio bar', () => {
  it('shows the Kinetic Canvas title with the role, and no redundant "Mode:" readout', () => {
    renderCanvas();
    expect(screen.queryByText(/^Mode:/)).not.toBeInTheDocument();
    const title = screen.getByTestId('canvas-title');
    expect(title).toHaveTextContent(/Kinetic Canvas/i);
    expect(title).toHaveTextContent(/Executive/i);
  });

  it('groups tabs and the Feedback action on the right (no stranded middle gap)', () => {
    renderCanvas();
    const group = screen.getByTestId('canvas-actions');
    expect(within(group).getByRole('tablist', { name: /canvas sections/i })).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /Flywheel Feedback/i })).toBeInTheDocument();
  });

  it('uses short single-line section tabs only (no Diagnostics: that lives in System status)', () => {
    renderCanvas();
    expect(tabs().map((t) => t.textContent)).toEqual(['Causal DAG', 'What-If', 'Briefing', 'Trade-offs']);
    expect(tabs()[1]).toHaveAttribute('title', 'What-If Waterfall');
    expect(screen.queryByRole('tab', { name: /Diagnostics/i })).not.toBeInTheDocument();
    expect(tabs().filter((t) => t.getAttribute('aria-selected') === 'true')).toHaveLength(1);
  });

  it('hosts the pane collapse control inside the bar instead of a floating circle over the content', () => {
    const onCollapse = vi.fn();
    renderCanvas({ onCollapse });
    const btn = screen.getByRole('button', { name: /Collapse Right Canvas/i });
    expect(btn.closest('[data-testid="canvas-bar"]')).not.toBeNull();
    fireEvent.click(btn);
    expect(onCollapse).toHaveBeenCalledTimes(1);
  });

  it('supports roving arrow-key navigation across all tabs, wrapping at the ends', () => {
    renderCanvas();
    const first = tabs()[0];
    first.focus();
    fireEvent.keyDown(first, { key: 'ArrowRight' });
    expect(tabs()[1]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tabs()[1], { key: 'End' });
    expect(tabs()[3]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tabs()[3], { key: 'ArrowRight' });
    expect(tabs()[0]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tabs()[0], { key: 'ArrowLeft' });
    expect(tabs()[3]).toHaveAttribute('aria-selected', 'true');
  });

  it('only the selected tab is in the tab order (roving tabindex)', () => {
    renderCanvas();
    const t = tabs();
    expect(t.filter((x) => x.getAttribute('tabindex') === '0')).toHaveLength(1);
    expect(t[0]).toHaveAttribute('tabindex', '0');
    expect(t[1]).toHaveAttribute('tabindex', '-1');
  });

  it('re-labels tabs and title per workstation', async () => {
    renderCanvas();
    await act(async () => {
      screen.getByTestId('to-ops').click();
    });
    expect(tabs().map((t) => t.textContent)).toEqual(['SLOs', 'Red-Lines', 'DLQ', 'DR Proofs']);
    expect(screen.getByTestId('canvas-title')).toHaveTextContent(/Data Operations/i);
  });

  it('keeps Flywheel Feedback reachable and opens its modal', () => {
    renderCanvas();
    fireEvent.click(screen.getByRole('button', { name: /Flywheel Feedback/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
