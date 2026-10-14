import * as React from 'react';

/**
 * The few Markdown forms the assistant writes: paragraphs, "- " and "* " bullets, "1." lists, "> " quoted passages,
 * **bold** and _italic_.
 * Built from React elements, never from HTML strings, so a draft cannot inject markup.
 */

const INLINE = /(\*\*[^*]+\*\*|(?<![A-Za-z0-9])__[^_]+__(?![A-Za-z0-9])|(?<![A-Za-z0-9])_[^_\s][^_]*_(?![A-Za-z0-9]))/g;

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
          return (
            <blockquote key={i} className="border-l-2 border-cx-line pl-3 text-cx-muted">
              {block.lines.map((l, j) => <p key={j}>{l}</p>)}
            </blockquote>
          );
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
