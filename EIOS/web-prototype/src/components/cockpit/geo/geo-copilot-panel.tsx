'use client';

import * as React from 'react';
import { Chip } from '../ui/chip';
import { Icon } from '@/components/ui/icon';

const EXAMPLES = [
  'Which corridors carry the most high-risk volume?',
  'Show accounts whose IP country differs from KYC',
  'Which accounts register in one country but log in from another?',
] as const;

/**
 * Placeholder for the geo agent: states plainly that it is not connected and never fakes an answer (honesty rule).
 * Collapsed to one bar by default so it does not cover the map while there is nothing to ask yet.
 */
export function GeoCopilotPanel() {
  const [open, setOpen] = React.useState(false);
  return (
    <aside aria-label="Geo copilot" className="w-72 border border-cx-line bg-white shadow-md">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-cx-accent">
        <Icon icon="auto_awesome" size="sm" className="text-cx-accent" />
        <span className="flex-1 text-title font-sans font-semibold text-cx-ink">Geo copilot</span>
        <Chip tone="warn">Not connected</Chip>
        <Icon icon={open ? 'expand_less' : 'expand_more'} size="sm" className="text-cx-muted" />
      </button>
      {open && (
        <div className="space-y-3 border-t border-cx-line-soft p-3">
          <p className="text-xs text-cx-muted">The geo agent is not wired yet. These are the questions it will answer from engine tools.</p>
          <ul className="space-y-1.5">
            {EXAMPLES.map((q) => (
              <li key={q}>
                <button type="button" disabled className="w-full border border-cx-line bg-cx-sub px-2 py-1.5 text-left text-xs text-cx-faint">
                  {q}
                </button>
              </li>
            ))}
          </ul>
          <input
            disabled
            aria-label="Message geo copilot"
            placeholder="Message geo copilot…"
            className="w-full border border-cx-line bg-cx-sub px-2 py-1.5 text-xs"
          />
        </div>
      )}
    </aside>
  );
}
