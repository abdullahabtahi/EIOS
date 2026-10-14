import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { MetricProvenanceBadge } from '@/components/cockpit/common/metric-provenance';
import type { MetricProvenance } from '@/components/cockpit/state/cockpit-types';

const metric = (overrides: Partial<MetricProvenance> = {}): MetricProvenance => ({
  metricId: 'aml.dossier:CR84920:discrepancy_multiplier',
  name: 'discrepancy multiplier',
  rawValue: 16,
  formattedValue: '16x',
  unit: 'multiplier',
  semanticDefinitionVersion: '',
  asOfTimestamp: '2026-10-14T03:57:10+00:00',
  originEngine: 'cockpit.aml.get_entity_dossier',
  stewardRole: 'cockpit.aml.get_entity_dossier',
  citation: '[ILLUSTRATIVE]',
  isCached: false,
  ...overrides,
});

describe('the provenance badge claims only what the backend said', () => {
  it('keeps the figure clean (no demo or illustrative chip) and does not repeat the unit the value carries', () => {
    render(<MetricProvenanceBadge metric={metric({ dataOrigin: 'fixture' })} displayMode="badge" />);
    expect(screen.queryByText('demo')).not.toBeInTheDocument();
    expect(screen.queryByText('[ILLUSTRATIVE]')).not.toBeInTheDocument();
    expect(screen.queryByText('multiplier')).not.toBeInTheDocument();
  });

  it('still shows other citation types on the figure', () => {
    render(<MetricProvenanceBadge metric={metric({ citation: '[TARGET]' })} displayMode="badge" />);
    expect(screen.getByText('[TARGET]')).toBeInTheDocument();
  });

  it('shows no verified tick for a figure that names no source', () => {
    render(<MetricProvenanceBadge metric={metric({ originEngine: '', stewardRole: '' })} displayMode="badge" />);
    expect(screen.queryByText('verified')).not.toBeInTheDocument();
  });

  it('never says real-time synchronized for demo data, and says not stated when the origin is unknown', () => {
    const { unmount } = render(<MetricProvenanceBadge metric={metric({ dataOrigin: 'fixture' })} displayMode="badge" />);
    fireEvent.click(screen.getByText('16x'));
    expect(screen.queryByText(/real-time synchronized/i)).not.toBeInTheDocument();
    expect(screen.getByText(/demo data/i)).toBeInTheDocument();
    unmount();

    render(<MetricProvenanceBadge metric={metric()} displayMode="badge" />);
    fireEvent.click(screen.getByText('16x'));
    expect(screen.queryByText(/real-time synchronized/i)).not.toBeInTheDocument();
    expect(screen.getByText(/origin not stated/i)).toBeInTheDocument();
  });
});
