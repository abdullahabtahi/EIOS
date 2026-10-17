import * as React from 'react';

/**
 * The few Markdown forms the assistant writes: paragraphs, "- " and "* " bullets, "1." lists, "> " quoted passages,
 * **bold** and _italic_.
 * Built from React elements, never from HTML strings, so a draft cannot inject markup.
 */

const INLINE = /(\*\*[^*\n]+\*\*|(?<![A-Za-z0-9])__[^_\n]+__(?![A-Za-z0-9])|(?<![A-Za-z0-9])_[^_\s\n][^_\n]*?_(?![A-Za-z0-9]))/g;

function inline(text: string): React.ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('__') && part.endsWith('__') && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('_') && part.endsWith('_') && part.length > 2) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

/** A quotation longer than this opens collapsed to a preview; the credit line below it always stays visible. */
const QUOTE_PREVIEW_CHARS = 320;

function Quote({ lines }: { lines: string[] }) {
  const credit = lines.length > 1 && lines[lines.length - 1].startsWith('—') ? lines[lines.length - 1] : null;
  const body = credit ? lines.slice(0, -1) : lines;
  const full = body.filter((l) => l.trim()).join(' ');
  const preview = full.slice(0, QUOTE_PREVIEW_CHARS).trimEnd();
  const text =
    full.length <= QUOTE_PREVIEW_CHARS ? (
      body.map((l, j) => <p key={j}>{l}</p>)
    ) : (
      <details>
        <summary className="cursor-pointer select-none">
          {preview}… <span className="text-cx-accent">Show full passage</span>
        </summary>
        <p className="pt-1">{full.slice(preview.length).trimStart()}</p>
      </details>
    );
  return (
    <blockquote className="border-l-2 border-cx-line pl-3 text-cx-muted space-y-1">
      {text}
      {credit && <p className="text-label">{credit}</p>}
    </blockquote>
  );
}

const BULLET = /^\s*[-*]\s+(.*)$/;
const NUMBERED = /^\s*\d{1,3}[.)]\s+(.*)$/;
const QUOTE = /^\s*>\s?(.*)$/;

type Block = { kind: 'p' | 'ul' | 'ol' | 'quote'; lines: string[] };

function blocks(source: string): Block[] {
  const out: Block[] = [];
  for (const line of source.split('\n')) {
    if (!line.trim()) {
      out.push({ kind: 'p', lines: [] });
      continue;
    }
    const quote = QUOTE.exec(line);
    const bullet = quote ? null : BULLET.exec(line);
    const numbered = quote || bullet ? null : NUMBERED.exec(line);
    const kind = quote ? 'quote' : bullet ? 'ul' : numbered ? 'ol' : 'p';
    const text = quote?.[1] ?? bullet?.[1] ?? numbered?.[1] ?? line.trim();
    const last = out[out.length - 1];
    if (last && last.kind === kind && last.lines.length > 0) last.lines.push(text);
    else out.push({ kind, lines: [text] });
  }
  return out.filter((b) => b.lines.length > 0);
}

export function SimpleMarkdown({ source, className = '' }: { source: string; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {blocks(source).map((block, i) => {
        if (block.kind === 'ul') {
          return (
            <ul key={i} className="list-disc pl-5 space-y-1">
              {block.lines.map((l, j) => <li key={j}>{inline(l)}</li>)}
            </ul>
          );
        }
        if (block.kind === 'quote') {
          return <Quote key={i} lines={block.lines} />;
        }
        if (block.kind === 'ol') {
          return (
            <ol key={i} className="list-decimal pl-5 space-y-1">
              {block.lines.map((l, j) => <li key={j}>{inline(l)}</li>)}
            </ol>
          );
        }
        return <p key={i}>{block.lines.map((l, j) => <React.Fragment key={j}>{j > 0 && <br />}{inline(l)}</React.Fragment>)}</p>;
      })}
    </div>
  );
}
