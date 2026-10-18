import { describe, expect, it } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import type { PersonaRole } from '@/components/cockpit/state/cockpit-types';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';

function RoleButtons() {
  const { setRole } = useCockpit();
  const roles: PersonaRole[] = ['executive', 'aml_investigator', 'partner_manager'];
  return (
    <>
      {roles.map((r) => (
        <button key={r} type="button" data-testid={`go-${r}`} onClick={() => setRole(r)}>
          {r}
        </button>
      ))}
    </>
  );
}

const go = (role: PersonaRole) => act(async () => { fireEvent.click(screen.getByTestId(`go-${role}`)); });
const railOpen = () => screen.queryByRole('button', { name: /Collapse Left Rail/i }) !== null;

describe('the triage rail default', () => {
  it('starts closed on the executive workstation and open on the others', async () => {
    render(
      <CockpitProvider>
        <RoleButtons />
        <TripartiteShell />
      </CockpitProvider>,
    );
    expect(railOpen()).toBe(false);
    expect(screen.getByRole('button', { name: /Expand Left Rail/i })).toBeInTheDocument();
    await go('aml_investigator');
    expect(railOpen()).toBe(true);
    await go('partner_manager');
    expect(railOpen()).toBe(true);
  });

  it('keeps a pick made on one workstation to that workstation', async () => {
    render(
      <CockpitProvider>
        <RoleButtons />
        <TripartiteShell />
      </CockpitProvider>,
    );
    await go('aml_investigator');
    fireEvent.click(screen.getByRole('button', { name: /Collapse Left Rail/i }));
    expect(railOpen()).toBe(false);
    await go('partner_manager');
    expect(railOpen()).toBe(true);
    await go('aml_investigator');
    expect(railOpen()).toBe(false);
    await go('executive');
    fireEvent.click(screen.getByRole('button', { name: /Expand Left Rail/i }));
    expect(railOpen()).toBe(true);
  });
});
