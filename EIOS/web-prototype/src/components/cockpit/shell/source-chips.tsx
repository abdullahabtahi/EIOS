'use client';

/**
 * The regulation passages an answer quoted, as chips: document, page and the regulator's jurisdiction. Opening a chip
 * shows the passage text exactly as the document wrote it. Rendered from the backend's `sources`, never inferred.
 */

import * as React from 'react';
import type { AnswerSource } from '../state/cockpit-types';

export function SourceChips({ sources }: { sources: AnswerSource[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="pt-2 border-t border-slate-100 space-y-1.5" aria-label="Sources">
      <span className="text-label text-slate-500">Sources</span>
      <ul className="space-y-1">
        {sources.map((s) => (
          <li key={s.passageId}>
            <details className="border border-slate-200 bg-slate-50">
              <summary className="px-2 py-1 text-label cursor-pointer select-none flex flex-wrap items-center gap-x-2">
                <span className="font-bold text-slate-800">{s.title}</span>
                <span className="text-slate-500">page {s.pages}</span>
                <span className="px-1 border border-slate-300 text-slate-600 font-mono">{s.jurisdiction}</span>
              </summary>
              <p className="px-2 py-1.5 text-label text-slate-700 whitespace-pre-line border-t border-slate-200">{s.text}</p>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
