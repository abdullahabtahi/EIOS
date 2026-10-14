import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { SourceChips } from '@/components/cockpit/shell/source-chips';
import { SimpleMarkdown } from '@/components/cockpit/common/simple-markdown';
import { normalizeSource } from '@/lib/server/normalize';

const raw = {
  passage_id: 'MT-FIAU-IP1.c41',
  document_id: 'MT-FIAU-IP1',
  title: 'FIAU Implementing Procedures, Part I',
  jurisdiction: 'MT',
  pages: '41-42',
  text: 'A subject person shall report as soon as practicable.',
  data_origin: 'live',
};

describe('normalizeSource', () => {
  it('maps the backend passage to the cockpit shape', () => {
    expect(normalizeSource(raw)).toEqual({
      passageId: 'MT-FIAU-IP1.c41',
      documentId: 'MT-FIAU-IP1',
      title: 'FIAU Implementing Procedures, Part I',
      jurisdiction: 'MT',
      pages: '41-42',
      text: 'A subject person shall report as soon as practicable.',
      dataOrigin: 'live',
    });
  });

  it('drops a source that names no passage, title or text instead of inventing one', () => {
    expect(normalizeSource({ ...raw, passage_id: '' })).toBeUndefined();
    expect(normalizeSource({ ...raw, text: '' })).toBeUndefined();
    expect(normalizeSource({ ...raw, title: '' })).toBeUndefined();
    expect(normalizeSource(null)).toBeUndefined();
  });
});

describe('SourceChips', () => {
  it('shows document, page and jurisdiction, and opens to the passage text', () => {
    render(<SourceChips sources={[normalizeSource(raw)!]} />);
    expect(screen.getByText('FIAU Implementing Procedures, Part I')).toBeInTheDocument();
    expect(screen.getByText('page 41-42')).toBeInTheDocument();
    expect(screen.getByText('MT')).toBeInTheDocument();
    fireEvent.click(screen.getByText('FIAU Implementing Procedures, Part I'));
    expect(screen.getByText('A subject person shall report as soon as practicable.')).toBeInTheDocument();
  });

  it('renders nothing when the answer quoted nothing', () => {
    const { container } = render(<SourceChips sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('SimpleMarkdown long quotes', () => {
  it('collapses a long passage to a preview, keeps the credit line visible and opens to the whole text', () => {
    const long = 'A subject person shall report. '.repeat(40).trim();
    render(<SimpleMarkdown source={`> ${long}\n> — Doc, p. 3 (MT)`} />);
    expect(screen.getByText('— Doc, p. 3 (MT)')).toBeInTheDocument();
    const details = document.querySelector('details');
    expect(details).not.toBeNull();
    expect(details?.querySelector('summary')?.textContent).toContain('Show full passage');
    expect(details?.textContent).toContain(long);
  });

  it('leaves a short quotation as plain text', () => {
    render(<SimpleMarkdown source={'> Short rule.\n> — Doc, p. 1 (MT)'} />);
    expect(document.querySelector('details')).toBeNull();
  });
});

describe('SimpleMarkdown quotes', () => {
  it('renders "> " lines as one quotation and never as a link', () => {
    render(<SimpleMarkdown source={'The guidance says:\n\n> A rule [click](http://x.invalid).\n> — Doc, p. 3 (MT)\n\nDone.'} />);
    const quote = document.querySelector('blockquote');
    expect(quote).not.toBeNull();
    expect(quote?.textContent).toContain('A rule [click](http://x.invalid).');
    expect(quote?.textContent).toContain('— Doc, p. 3 (MT)');
    expect(document.querySelector('a')).toBeNull();
    expect(screen.getByText('Done.')).toBeInTheDocument();
  });
});
