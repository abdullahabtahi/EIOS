import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

/**
 * Design-system guard. The cockpit colour budget is slate neutrals, one blue accent,
 * one red alert and green/amber for status text. These checks fail when a component
 * adds a colour outside that budget.
 */
const SRC = path.resolve(__dirname, '../..');
const CANVAS_FILES = new Set([
  'components/cockpit/common/topological-graph.tsx',
  'components/cockpit/common/churn-radar-scatter.tsx',
  'components/cockpit/common/causal-dag-canvas.tsx',
  'components/cockpit/geo/geo-map-style.ts',
]);
const ALLOWED_HUES = new Set(['slate', 'gray', 'zinc', 'neutral', 'stone', 'red', 'green', 'amber', 'blue']);
const PREFIX = '(?:text|bg|border|ring|fill|stroke|from|to|via|divide|outline|decoration|shadow|accent|caret|placeholder)';
const HUE_CLASS = new RegExp(`(?<![\\w-])${PREFIX}-([a-z]+)-\\d{2,3}\\b`, 'g');
const HEX = /#[0-9a-fA-F]{6}\b/g;

function sourceFiles(dir: string, out: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'tests' || entry.name === 'landing' || entry.name === 'api') continue;
      sourceFiles(full, out);
    } else if (entry.name.endsWith('.tsx')) out.push(full);
  }
  return out;
}

const files = sourceFiles(SRC).map((f) => ({ rel: path.relative(SRC, f), text: fs.readFileSync(f, 'utf8') }));

describe('cockpit design guard', () => {
  it('uses only the four canonical hue families (plus neutrals)', () => {
    const offenders = files.flatMap(({ rel, text }) =>
      [...text.matchAll(HUE_CLASS)].filter((m) => !ALLOWED_HUES.has(m[1])).map((m) => `${rel}: ${m[0]}`),
    );
    expect(offenders).toEqual([]);
  });

  it('keeps raw hex literals inside the canvas/SVG chart files', () => {
    const offenders = files
      .filter(({ rel }) => !CANVAS_FILES.has(rel))
      .flatMap(({ rel, text }) => [...text.matchAll(HEX)].map((m) => `${rel}: ${m[0]}`));
    expect(offenders).toEqual([]);
  });
});
