import { describe, it, expect, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import React from 'react';

vi.mock('@/components/cockpit/geo/geo-config', () => ({ readMapsConfig: () => ({ apiKey: 'test-key', mapId: null }) }));
vi.mock('@vis.gl/react-google-maps', () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Map: () => <div data-testid="google-map" />,
  useMap: () => null,
}));
vi.mock('@/components/cockpit/geo/geo-deck-overlay', () => ({ GeoDeckOverlay: () => null }));

import { GeoMap } from '@/components/cockpit/geo/geo-map';

describe('the map when Google rejects the request', () => {
  it('says so in the cockpit own words and offers a reload, instead of Google\'s "Oops"', () => {
    render(<GeoMap layers={[]} />);
    expect(screen.getByTestId('google-map')).toBeInTheDocument();
    act(() => (window as unknown as { gm_authFailure: () => void }).gm_authFailure());
    expect(screen.getByRole('status')).toHaveTextContent('The map could not load');
    expect(screen.getByRole('button', { name: 'Reload the page' })).toBeInTheDocument();
    expect(screen.queryByTestId('google-map')).toBeNull();
  });
});
