'use client';

import * as React from 'react';
import { PanelHeader } from '../ui/panel-header';
import { Chip } from '../ui/chip';

const EXAMPLES = [
  'Which corridors carry the most high-risk volume?',
  'Show accounts whose IP country differs from KYC',
  'What changed in the Cyprus to Panama corridor?',
] as const;

/** Placeholder for the geo agent: states plainly that it is not connected, never fakes an answer (honesty rule). */
export function GeoCopilotPanel() {
  return (
    <aside aria-label="Geo copilot" className="flex w-72 flex-col gap-3 border border-cx-line bg-white p-3 shadow-md">
      <PanelHeader title="Geo copilot" icon="auto_awesome" level={4} actions={<Chip tone="warn">Not connected</Chip>} />
      <p className="text-xs text-cx-muted">
        The geo agent is not wired yet. These are the questions it will answer from engine tools.
      </p>
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
        className="border border-cx-line bg-cx-sub px-2 py-1.5 text-xs"
      />
    </aside>
  );
}
