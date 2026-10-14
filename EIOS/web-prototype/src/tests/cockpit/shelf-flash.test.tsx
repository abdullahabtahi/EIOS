import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { GovernedActionShelf } from '@/components/cockpit/shell/governed-action-shelf';
import { EXECUTIVE_FIXTURE, getMockWorkstationState } from '@/components/cockpit/state/fixtures';

function Stager() {
  const { stageAction } = useCockpit();
  return (
    <button type="button" data-testid="stage" onClick={() => stageAction({ ...EXECUTIVE_FIXTURE.stagedActionCards[0], intentId: `new-${Math.random()}` })} />
  );
}

beforeEach(() => {
  vi.useFakeTimers();
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ ...getMockWorkstationState('executive'), stagedActionCards: [] }),
  }) as unknown as typeof fetch;
});
afterEach(() => vi.useRealTimers());

describe('the action shelf', () => {
  it('flashes briefly when a new action is staged from elsewhere, then settles', async () => {
    render(
      <CockpitProvider>
        <GovernedActionShelf />
        <Stager />
      </CockpitProvider>,
    );
    await act(async () => {});
    const shelf = screen.getByRole('region', { name: /Governed Action Shelf/i });
    expect(shelf).not.toHaveAttribute('data-flash');
    fireEvent.click(screen.getByTestId('stage'));
    expect(shelf).toHaveAttribute('data-flash', 'true');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(shelf).not.toHaveAttribute('data-flash');
  });
});
