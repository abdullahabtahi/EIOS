'use client';

import * as React from 'react';
import { PanelHeader } from '../ui/panel-header';
import { Chip } from '../ui/chip';
import { summarize, summarizeReference } from './geo-aggregates';
import { describeSelection, formatUsd } from './geo-format';
import { dataOf, type ResourceState } from './use-geo-resource';
import type { GeoFlows, GeoReference, GeoSelection, LayerId, RiskTier } from './geo-types';

type Origin = 'Reference' | 'Engine';
const LENSES: Readonly<Record<LayerId, { readonly label: string; readonly origin: Origin }>> = {
  risk: { label: 'FATF risk areas', origin: 'Reference' },
  offshore: { label: 'Offshore entity centres', origin: 'Reference' },
  corridors: { label: 'Cross-border corridors', origin: 'Engine' },
  mismatches: { label: 'IP vs KYC country', origin: 'Engine' },
};
const FLOW_LENSES: readonly LayerId[] = ['corridors', 'mismatches'];
const TIER_BAR: Readonly<Record<RiskTier, string>> = { low: 'bg-cx-ok', medium: 'bg-cx-warn', high: 'bg-cx-bad' };
const TIERS: readonly RiskTier[] = ['high', 'medium', 'low'];
const COUNT = new Intl.NumberFormat('en-US');

export interface GeoWidgetsProps {
  readonly flows: ResourceState<GeoFlows>;
  readonly reference: ResourceState<GeoReference>;
  readonly visible: ReadonlySet<LayerId>;
  readonly onToggle: (id: LayerId) => void;
  readonly hovered: GeoSelection;
  readonly selected: GeoSelection;
}

function unavailable(label: string, state: ResourceState<unknown>): string | null {
  if (state.status === 'loading') return `Loading ${label}…`;
  if (state.status === 'error') return `${label[0].toUpperCase()}${label.slice(1)} unavailable${state.httpStatus ? ` (HTTP ${state.httpStatus})` : ''}. Nothing from it is shown.`;
  return null;
}

function Bar({ label, value, share, tone }: { label: string; value: string; share: number; tone: string }) {
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs">
        <span className="text-cx-ink-soft">{label}</span>
        <span className="font-mono tabular-nums text-cx-ink">{value}</span>
      </div>
      <div className="h-1.5 bg-cx-sub-2">
        <div className={`h-full ${tone}`} style={{ width: `${share * 100}%` }} />
      </div>
    </div>
  );
}

export function GeoWidgets({ flows, reference, visible, onToggle, hovered, selected }: GeoWidgetsProps) {
  const ref = dataOf(reference);
  const fl = dataOf(flows);
  const flowsReady = fl !== null && ref !== null; // flows are placed on the map using the reference layer
  const summary = summarize(fl);
  const refSummary = summarizeReference(ref);
  const detail = describeSelection(fl, ref, hovered ?? selected);
  const messages = [unavailable('reference layer', reference), unavailable('customer flows', flows)].filter(Boolean);
  const maxOffshore = refSummary?.topOffshore[0]?.entities_incorporated ?? 0;

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <section aria-label="Layers" className="space-y-2">
        <PanelHeader title="Evidence lenses" icon="layers" level={4} />
        {(Object.keys(LENSES) as LayerId[]).map((id) => {
          const off = FLOW_LENSES.includes(id) ? !flowsReady : !ref;
          return (
            <label key={id} className={`flex items-center gap-2 text-xs ${off ? 'text-cx-faint' : 'cursor-pointer text-cx-ink'}`}>
              <input type="checkbox" disabled={off} checked={visible.has(id) && !off} onChange={() => onToggle(id)} />
              <span className="flex-1">{LENSES[id].label}</span>
              <Chip tone={LENSES[id].origin === 'Reference' ? 'ok' : 'neutral'}>{LENSES[id].origin}</Chip>
            </label>
          );
        })}
        {messages.map((m) => (
          <p key={m} role="status" className="text-xs text-cx-warn">{m}</p>
        ))}
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

      <section aria-label="Corridor volume by risk tier" className="space-y-2">
        <PanelHeader title="Corridor volume by tier" icon="bar_chart" level={4} actions={<Chip>Engine</Chip>} />
        {!summary || summary.corridorVolumeUsd === null ? (
          <Chip>NO_DATA</Chip>
        ) : !summary.exposure ? (
          <p className="text-xs text-cx-muted">Tiers unavailable: the reference layer is needed to rate corridors.</p>
        ) : (
          TIERS.map((tier) => (
            <Bar key={tier} label={tier[0].toUpperCase() + tier.slice(1)} value={formatUsd(summary.exposure![tier])}
              share={summary.exposure![tier] / summary.corridorVolumeUsd!} tone={TIER_BAR[tier]} />
          ))
        )}
        {summary && (
          <p className="text-xs text-cx-muted">
            IP ≠ KYC country: <span className="font-mono font-semibold text-cx-ink">{COUNT.format(summary.flaggedAccounts)}</span> accounts flagged
          </p>
        )}
      </section>

      <section aria-label="Top corridors" className="space-y-2">
        <PanelHeader title="Top corridors" icon="swap_horiz" level={4} />
        {summary ? (
          <ol className="space-y-1">
            {summary.topCorridors.map((c) => (
              <li key={`${c.origin}>${c.destination}`} className="flex justify-between text-xs">
                <span className="font-mono text-cx-ink-soft">{c.origin} → {c.destination}</span>
                <span className="font-mono tabular-nums text-cx-ink">{formatUsd(c.volume_usd)}</span>
              </li>
            ))}
          </ol>
        ) : (
          <Chip>NO_DATA</Chip>
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
            <Bar key={c.iso2} label={c.name} value={COUNT.format(c.entities_incorporated ?? 0)}
              share={(c.entities_incorporated ?? 0) / maxOffshore} tone="bg-cx-accent" />
          ))
        ) : (
          <Chip>NO_DATA</Chip>
        )}
      </section>

      <section aria-label="Sources" className="mt-auto space-y-1 border-t border-cx-line-soft pt-2 text-label text-cx-muted">
        {ref &&
          Object.values(ref.sources).map((s) => (
            <p key={s.source}>
              {s.source}
              {s.as_of && <> · as of <span className="font-mono">{s.as_of}</span></>}
            </p>
          ))}
        {fl && (
          <p>
            {fl.source} · as of <span className="font-mono">{fl.as_of.slice(0, 10)}</span>
          </p>
        )}
      </section>
    </div>
  );
}
