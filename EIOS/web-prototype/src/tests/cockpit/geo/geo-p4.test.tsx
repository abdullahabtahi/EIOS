import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { REFERENCE } from './reference-fixture';
import { FLOWS } from './flows-fixture';
import { OFFSHORE_NOTICE, ICIJ_URL } from '@/components/cockpit/geo/geo-format';
import { GeoLegend } from '@/components/cockpit/geo/geo-legend';
import { GeoSources } from '@/components/cockpit/geo/geo-sources';

/**
 * P-4: the map shows counts from a leak database. Being in it is not evidence of wrongdoing, so the offshore layer
 * says so, once, in its legend (the one place that is on screen whenever the layer is, in every view).
 */
describe('P-4 offshore non-implication notice', () => {
  it('states that appearing in the database is not evidence of wrongdoing', () => {
    expect(OFFSHORE_NOTICE).toMatch(/ICIJ Offshore Leaks Database/);
    expect(OFFSHORE_NOTICE).toMatch(/not evidence of wrongdoing/i);
  });

  it('is in the legend while the offshore layer is on, and not otherwise', () => {
    const { rerender } = render(<GeoLegend visible={new Set(['offshore'])} flows={FLOWS} />);
    expect(screen.getByText(OFFSHORE_NOTICE)).toBeInTheDocument();
    rerender(<GeoLegend visible={new Set(['risk'])} flows={FLOWS} />);
    expect(screen.queryByText(OFFSHORE_NOTICE)).not.toBeInTheDocument();
  });

  it('credits the ICIJ in Sources with a link to the database', () => {
    render(<GeoSources flows={FLOWS} reference={REFERENCE} />);
    const link = screen.getByRole('link', { name: /ICIJ Offshore Leaks Database/ });
    expect(link).toHaveAttribute('href', ICIJ_URL);
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });
});
