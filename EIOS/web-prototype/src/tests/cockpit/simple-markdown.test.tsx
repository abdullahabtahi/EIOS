import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { SimpleMarkdown } from '@/components/cockpit/common/simple-markdown';

describe('SimpleMarkdown', () => {
  it('turns **bold** into bold text with no literal asterisks', () => {
    const { container } = render(<SimpleMarkdown source="A **loud** word" />);
    expect(container.querySelector('strong')).toHaveTextContent('loud');
    expect(container.textContent).not.toContain('*');
  });

  it('renders bullets as a list and keeps the text of each item', () => {
    render(<SimpleMarkdown source={'Top partners:\n- **PTR-882** at risk\n* PTR-723 next'} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('PTR-882')).toBeInTheDocument();
  });

  it('renders a numbered list and italic text', () => {
    const { container } = render(<SimpleMarkdown source={'1. first\n2. second\n\n_as of today_'} />);
    expect(container.querySelector('ol')).not.toBeNull();
    expect(container.querySelector('em')).toHaveTextContent('as of today');
  });

  it('never turns markup in the text into elements', () => {
    const { container } = render(<SimpleMarkdown source={'<img src=x onerror=alert(1)> <b>hi</b>'} />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('b')).toBeNull();
    expect(container.textContent).toContain('<b>hi</b>');
  });

  it('keeps snake_case words intact', () => {
    const { container } = render(<SimpleMarkdown source="days_to_intervention_deadline is set" />);
    expect(container.querySelector('em')).toBeNull();
    expect(container.textContent).toBe('days_to_intervention_deadline is set');
  });
});
