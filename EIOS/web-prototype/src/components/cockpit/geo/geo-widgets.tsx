'use client';

import * as React from 'react';
import { PanelHeader } from '../ui/panel-header';
import { Chip } from '../ui/chip';
import { summarize, summarizeReference } from './geo-aggregates';
import { describeSelection, formatUsd } from './geo-format';
import type { ReferenceState } from './use-geo-reference';
import type { GeoEvidence, GeoSelection, LayerId, RiskTier } from './geo-types';

interface LensInfo {
  readonly label: string;
  readonly origin: 'Reference' | 'Fixture';
}
const LENSES: Readonly<Record<LayerId, LensInfo>> = {
  risk: { label: 'FATF risk areas', origin: 'Reference' },
  offshore: { label: 'Offshore entity centres', origin: 'Reference' },
  corridors: { label: 'Cross-border corridors', origin: 'Fixture' },
  mismatches: { label: 'IP vs KYC country', origin: 'Fixture' },
};
const REFERENCE_LENSES: readonly LayerId[] = ['risk', 'offshore'];
const TIER_BAR: Readonly<Record<RiskTier, string>> = { low: 'bg-cx-ok', medium: 'bg-cx-warn', high: 'bg-cx-bad' };
const TIERS: readonly RiskTier[] = ['high', 'medium', 'low'];
const COUNT = new Intl.NumberFormat('en-US');

export interface GeoWidgetsProps {
  readonly evidence: GeoEvidence;
  readonly reference: ReferenceState;
  readonly visible: ReadonlySet<LayerId>;
  readonly onToggle: (id: LayerId) => void;
  readonly hovered: GeoSelection;
  readonly selected: GeoSelection;
}

function referenceStatus(reference: ReferenceState): string | null {
  if (reference.status === 'loading') return 'Loading the reference layer…';
  if (reference.status === 'error') {
    return `Reference layer unavailable${reference.httpStatus ? ` (HTTP ${reference.httpStatus})` : ''}. No country data is shown.`;
  }
  return null;
}

export function GeoWidgets({ evidence, reference, visible, onToggle, hovered, selected }: GeoWidgetsProps) {
  const ref = reference.status === 'ready' ? reference.reference : null;
  const summary = summarize(evidence);
  const refSummary = summarizeReference(ref);
  const detail = describeSelection(evidence, ref, hovered ?? selected);
  const status = referenceStatus(reference);
  const maxOffshore = refSummary?.topOffshore[0]?.entities_incorporated ?? 0;

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <section aria-label="Layers" className="space-y-2">
        <PanelHeader title="Evidence lenses" icon="layers" level={4} />
        {(Object.keys(LENSES) as LayerId[]).map((id) => {
          const unavailable = REFERENCE_LENSES.includes(id) && !ref;
          return (
            <label key={id} className={`flex items-center gap-2 text-xs ${unavailable ? 'text-cx-faint' : 'cursor-pointer text-cx-ink'}`}>
              <input type="checkbox" disabled={unavailable} checked={visible.has(id) && !unavailable} onChange={() => onToggle(id)} />
              <span className="flex-1">{LENSES[id].label}</span>
              <Chip tone={LENSES[id].origin === 'Reference' ? 'ok' : 'neutral'}>{LENSES[id].origin}</Chip>
            </label>
          );
        })}
        {status && <p role="status" className="text-xs text-cx-warn">{status}</p>}
      </section>

      <section aria-label="Selection" className="space-y-2">
        <PanelHeader title={detail ? detail.title : 'Selection'} icon="touch_app" level={4} />
        {detail ? (
          <dl className="space-y-1 text-xs">
            {detail.rows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-3">
                <dt className="text-cx-muted">{label}</dt>
                <dd className="text-right font-mono text-cx-ink">{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-xs text-cx-muted">Hover or click a country or a flow on the map.</p>
        )}
      </section>

      <section aria-label="FATF lists" className="space-y-2">
        <PanelHeader title="FATF lists" icon="gavel" level={4} />
        {refSummary ? (
          <p className="text-xs text-cx-ink-soft">
            <span className="font-mono font-semibold text-cx-bad">{refSummary.fatf.call_for_action}</span> call for action ·{' '}
            <span className="font-mono font-semibold text-cx-warn">{refSummary.fatf.increased_monitoring}</span> increased monitoring
          </p>
        ) : (
          <Chip>NO_DATA</Chip>
        )}
      </section>

      <section aria-label="Offshore centres" className="space-y-2">
        <PanelHeader title="Offshore entities by jurisdiction" icon="account_balance" level={4} />
        {refSummary ? (
          refSummary.topOffshore.map((c) => (
            <div key={c.iso2} className="space-y-0.5">
              <div className="flex justify-between text-xs">
                <span className="text-cx-ink-soft">{c.name}</span>
                <span className="font-mono tabular-nums text-cx-ink">{COUNT.format(c.entities_incorporated ?? 0)}</span>
              </div>
              <div className="h-1.5 bg-cx-sub-2">
                <div className="h-full bg-cx-accent" style={{ width: `${((c.entities_incorporated ?? 0) / maxOffshore) * 100}%` }} />
              </div>
            </div>
          ))
        ) : (
          <Chip>NO_DATA</Chip>
        )}
      </section>

      <section aria-label="Corridor volume by risk tier" className="space-y-2">
        <PanelHeader title="Corridor volume by tier" icon="bar_chart" level={4} actions={<Chip>Fixture</Chip>} />
        {summary.corridorVolumeUsd === null ? (
          <Chip>NO_DATA</Chip>
        ) : (
          TIERS.map((tier) => (
            <div key={tier} className="space-y-0.5">
              <div className="flex justify-between text-xs">
                <span className="capitalize text-cx-ink-soft">{tier}</span>
                <span className="font-mono tabular-nums text-cx-ink">{formatUsd(summary.volumeByTier[tier])}</span>
              </div>
              <div className="h-1.5 bg-cx-sub-2">
                <div className={`h-full ${TIER_BAR[tier]}`} style={{ width: `${(summary.volumeByTier[tier] / summary.corridorVolumeUsd!) * 100}%` }} />
              </div>
            </div>
          ))
        )}
        <p className="text-xs text-cx-muted">
          IP ≠ KYC country: <span className="font-mono font-semibold text-cx-ink">{summary.mismatchCount}</span> accounts
        </p>
      </section>

      <section aria-label="Sources" className="mt-auto space-y-1 border-t border-cx-line-soft pt-2 text-label text-cx-muted">
        {ref &&
          Object.values(ref.sources).map((s) => (
            <p key={s.source}>
              {s.source}
              {s.as_of && <> · as of <span className="font-mono">{s.as_of}</span></>}
            </p>
          ))}
        <p>
          Customer flows: <span className="font-mono">{evidence.source}</span> · as of <span className="font-mono">{evidence.asOf}</span>
        </p>
      </section>
    </div>
  );
}
