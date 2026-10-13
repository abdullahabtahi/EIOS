import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { Chip } from '@/components/cockpit/ui/chip';
import { PanelHeader } from '@/components/cockpit/ui/panel-header';

describe('Chip', () => {
  it('renders its label as a single text node (screen-reader friendly)', () => {
    render(<Chip tone="ok">4 staged</Chip>);
    expect(screen.getByText('4 staged')).toBeInTheDocument();
  });

  it('exposes the tone for styling hooks and tests without leaking raw colours', () => {
    const { rerender } = render(<Chip tone="bad">BREACHED</Chip>);
    expect(screen.getByText('BREACHED')).toHaveAttribute('data-tone', 'bad');
    rerender(<Chip tone="warn">EXPIRED</Chip>);
    expect(screen.getByText('EXPIRED')).toHaveAttribute('data-tone', 'warn');
    rerender(<Chip>neutral by default</Chip>);
    expect(screen.getByText('neutral by default')).toHaveAttribute('data-tone', 'neutral');
  });

  it('only uses cx-* design tokens, never arbitrary hex classes', () => {
    render(<Chip tone="info">x</Chip>);
    expect(screen.getByText('x').className).not.toMatch(/\[#/);
    expect(screen.getByText('x').className).toMatch(/cx-/);
  });
});

describe('PanelHeader', () => {
  it('renders a level-3 title plus optional actions', () => {
    render(<PanelHeader icon="speed" title="Data Product SLA" actions={<button type="button">Act</button>} />);
    expect(screen.getByRole('heading', { level: 3, name: 'Data Product SLA' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Act' })).toBeInTheDocument();
  });

  it('uses the title type style (Inter semibold), not mono caps', () => {
    render(<PanelHeader title="Plain title" />);
    const h = screen.getByRole('heading', { name: 'Plain title' });
    expect(h.className).toMatch(/text-title/);
    expect(h.className).not.toMatch(/uppercase|font-mono/);
  });

  it('supports a custom heading level', () => {
    render(<PanelHeader title="Sub" level={4} />);
    expect(screen.getByRole('heading', { level: 4, name: 'Sub' })).toBeInTheDocument();
  });
});
