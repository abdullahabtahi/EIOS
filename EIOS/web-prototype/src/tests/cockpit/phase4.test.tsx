import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, within, act, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';
import { TriageRail } from '@/components/cockpit/shell/triage-rail';
import { OperationsBoardView } from '@/components/cockpit/workstations/operations-board';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import type { PersonaRole, TriageItem, WorkstationApiResponse } from '@/components/cockpit/state/cockpit-types';

const AS_OF = '2026-10-13T12:00:00.000Z';
const item = (id: string, severity: TriageItem['severity'], status: TriageItem['status'], ts: string): TriageItem => ({
  id, role: 'executive', title: `Title ${id}`, subtitle: `Sub ${id}`, entityId: `ENT-${id}`, entityType: 'ACCOUNT',
  priorityScore: 0.7, severity, status, timestamp: ts, tags: [], metricsSummary: {},
});

function mockResp(resp: WorkstationApiResponse) {
  global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(resp) }) as unknown as typeof fetch;
}

afterEach(() => vi.restoreAllMocks());

describe('Triage rail shows queue context: counts, lifecycle status and age', () => {
  const resp = (): WorkstationApiResponse => ({
    ...getMockWorkstationState('executive'),
    asOfTimestamp: AS_OF,
    triageItems: [
      item('a', 'CRITICAL', 'INVESTIGATING', '2026-10-13T09:00:00.000Z'),
      item('b', 'CRITICAL', 'OPEN', '2026-10-13T11:46:00.000Z'),
      item('c', 'LOW', 'STAGED', '2026-10-11T12:00:00.000Z'),
    ],
  });

  it('labels severity pills with live counts and keeps them clickable filters', async () => {
    mockResp(resp());
    render(<CockpitProvider><TriageRail /></CockpitProvider>);
    await waitFor(() => expect(screen.getByRole('button', { name: 'ALL 3' })).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'CRITICAL 2' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'HIGH 0' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'CRITICAL 2' }));
    expect(screen.getByRole('button', { name: 'CRITICAL 2' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByText('Title c')).not.toBeInTheDocument();
  });

  it('shows each row\'s lifecycle status and age relative to the data as-of time', async () => {
    mockResp(resp());
    render(<CockpitProvider><TriageRail /></CockpitProvider>);
    const rowA = (await screen.findByText('Title a')).closest('button') as HTMLElement;
    expect(within(rowA).getByText('INVESTIGATING')).toBeInTheDocument();
    expect(within(rowA).getByText('3h')).toBeInTheDocument();
    const rowC = screen.getByText('Title c').closest('button') as HTMLElement;
    expect(within(rowC).getByText('STAGED')).toBeInTheDocument();
    expect(within(rowC).getByText('2d')).toBeInTheDocument();
  });
});

describe('Persona strip is a real tablist', () => {
  it('groups the five tabs, wires aria-controls, and supports roving arrow keys', async () => {
    mockResp(getMockWorkstationState('executive'));
    render(<CockpitProvider><TripartiteShell /></CockpitProvider>);
    const list = screen.getByRole('tablist', { name: /Workstations/i });
    const tabs = within(list).getAllByRole('tab');
    expect(tabs).toHaveLength(5);
    tabs.forEach((t) => expect(t).toHaveAttribute('aria-controls', 'workstation-panel'));
    expect(tabs.filter((t) => t.getAttribute('tabindex') === '0')).toHaveLength(1);

    tabs[0].focus();
    fireEvent.keyDown(tabs[0], { key: 'ArrowRight' });
    await waitFor(() => expect(within(list).getAllByRole('tab')[1]).toHaveAttribute('aria-selected', 'true'));
    fireEvent.keyDown(within(list).getAllByRole('tab')[1], { key: 'End' });
    await waitFor(() => expect(within(list).getAllByRole('tab')[4]).toHaveAttribute('aria-selected', 'true'));
    fireEvent.keyDown(within(list).getAllByRole('tab')[4], { key: 'ArrowRight' });
    await waitFor(() => expect(within(list).getAllByRole('tab')[0]).toHaveAttribute('aria-selected', 'true'));

    const panel = document.getElementById('workstation-panel')!;
    expect(panel).toHaveAttribute('role', 'tabpanel');
    expect(panel.getAttribute('aria-labelledby')).toMatch(/^tab-/);
  });

  it('has no tab outside a tablist anywhere in the shell', () => {
    mockResp(getMockWorkstationState('executive'));
    render(<CockpitProvider><TripartiteShell /></CockpitProvider>);
    const stray = screen.getAllByRole('tab').filter((t) => !t.closest('[role="tablist"]'));
    expect(stray).toHaveLength(0);
  });
});

describe('Skip link', () => {
  it('is the first focusable element and targets the workspace region', () => {
    mockResp(getMockWorkstationState('executive'));
    render(<CockpitProvider><TripartiteShell /></CockpitProvider>);
    const link = screen.getByRole('link', { name: /Skip to workspace/i });
    expect(link).toHaveAttribute('href', '#workspace');
    const target = document.getElementById('workspace');
    expect(target).not.toBeNull();
    expect(target).toHaveAttribute('tabindex', '-1');
    const firstFocusable = document.querySelector('a[href], button, [tabindex="0"], input, select') as HTMLElement;
    expect(firstFocusable).toBe(link);
  });
});

function RoleDriver({ role }: { role: PersonaRole }) {
  const { setRole } = useCockpit();
  React.useEffect(() => { setRole(role); }, [role, setRole]);
  return null;
}

const accessibleName = (el: Element): string => {
  const clone = el.cloneNode(true) as HTMLElement;
  clone.querySelectorAll('.material-symbols-sharp, [aria-hidden="true"]').forEach((n) => n.remove());
  return (
    el.getAttribute('aria-label') ||
    el.getAttribute('aria-labelledby') ||
    el.getAttribute('title') ||
    el.getAttribute('placeholder') ||
    (el as HTMLInputElement).labels?.[0]?.textContent ||
    clone.textContent?.trim() ||
    ''
  );
};

describe('Every interactive control has an accessible name in every workstation', () => {
  it.each<PersonaRole>(['executive', 'aml_investigator', 'partner_manager', 'compliance_auditor', 'data_operations'])(
    '%s',
    async (role) => {
      mockResp(getMockWorkstationState(role));
      render(<CockpitProvider><RoleDriver role={role} /><TripartiteShell /></CockpitProvider>);
      await act(async () => { await new Promise((r) => setTimeout(r, 30)); });
      const nameless = [...document.querySelectorAll('button, input:not([type="hidden"]), select, textarea, [role="tab"], [role="button"]')]
        .filter((el) => !el.closest('[inert], [aria-hidden="true"]'))
        .filter((el) => !accessibleName(el))
        .map((el) => el.outerHTML.slice(0, 120));
      expect(nameless).toEqual([]);
    },
  );
});

describe('DLQ redrive reports the real outcome', () => {
  it('shows an inline failure (no alert, no fake success) when the redrive service is unreachable', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    global.fetch = vi.fn().mockImplementation((url: string) =>
      String(url).includes('/dlq/redrive')
        ? Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) })
        : Promise.resolve({ ok: true, json: () => Promise.resolve(getMockWorkstationState('data_operations')) }),
    ) as unknown as typeof fetch;
    render(<CockpitProvider><OperationsBoardView /></CockpitProvider>);
    fireEvent.click(screen.getAllByRole('button', { name: /Redrive Pipeline/i })[0]);
    expect(await screen.findByText(/Redrive failed/i)).toBeInTheDocument();
    expect(screen.queryByText(/Redrive dispatched/i)).not.toBeInTheDocument();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it('confirms inline only when the service accepts the request', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    global.fetch = vi.fn().mockImplementation((url: string) =>
      String(url).includes('/dlq/redrive')
        ? Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
        : Promise.resolve({ ok: true, json: () => Promise.resolve(getMockWorkstationState('data_operations')) }),
    ) as unknown as typeof fetch;
    render(<CockpitProvider><OperationsBoardView /></CockpitProvider>);
    fireEvent.click(screen.getAllByRole('button', { name: /Redrive Pipeline/i })[0]);
    expect(await screen.findByText(/Redrive dispatched/i)).toBeInTheDocument();
    expect(alertSpy).not.toHaveBeenCalled();
  });
});
