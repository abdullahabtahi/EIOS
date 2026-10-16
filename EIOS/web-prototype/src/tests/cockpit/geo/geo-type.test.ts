import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const DIR = join(process.cwd(), 'src/components/cockpit/geo');
const CSS = readFileSync(join(process.cwd(), 'src/app/globals.css'), 'utf8');

describe('the geospatial page is set in Inter alone', () => {
  it('asks for no monospace face in any of its own components', () => {
    const offenders = readdirSync(DIR)
      .filter((f) => /\.(tsx?|css)$/.test(f))
      .filter((f) => /font-mono|font-code|monospace/.test(readFileSync(join(DIR, f), 'utf8')));
    expect(offenders).toEqual([]);
  });

  it('turns the shared chat components inside it to Inter too, without touching them elsewhere', () => {
    expect(CSS).toMatch(/\.geo-inter\s+\.font-mono[^{]*\{[^}]*font-family:\s*var\(--font-paragraph\)/);
    expect(readFileSync(join(DIR, 'geo-workspace.tsx'), 'utf8')).toContain('geo-inter');
  });
});
