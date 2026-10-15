import * as React from 'react';
import { Chip } from '../ui/chip';
import { summarize, summarizeReference } from './geo-aggregates';
import { formatUsd } from './geo-format';
import type { GeoFlows, GeoReference, RiskTier } from './geo-types';
import type { ViewId } from './geo-views';

const COUNT = new Intl.NumberFormat('en-US');
const TIERS: readonly { readonly id: RiskTier; readonly label: string; readonly bar: string }[] = [
  { id: 'high', label: 'High', bar: 'bg-cx-bad' },
  { id: 'medium', label: 'Medium', bar: 'bg-cx-warn-solid' },
  { id: 'low', label: 'Low', bar: 'bg-slate-300' },
];

const Strong = ({ children }: { children: React.ReactNode }) => <span className="font-mono font-semibold tabular-nums text-cx-ink">{children}</span>;

function ExposureBar({ exposure, total }: { readonly exposure: Readonly<Record<RiskTier, number>>; readonly total: number }) {
  return (
    <div className="space-y-2">
      <div role="img" aria-label="Corridor volume by risk tier" className="flex h-2 bg-cx-sub-2">
        {TIERS.map((t) => (
          <div key={t.id} className={t.bar} style={{ width: `${(exposure[t.id] / total) * 100}%` }} />
        ))}
      </div>
      <dl className="grid grid-cols-3 gap-2 text-label">
        {TIERS.map((t) => (
          <div key={t.id}>
            <dt className="flex items-center gap-1.5 text-cx-muted">
              <span aria-hidden="true" className={`size-1.5 ${t.bar}`} />
              {t.label}
            </dt>
            <dd className="font-mono text-xs font-semibold tabular-nums text-cx-ink">{formatUsd(exposure[t.id])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** One line or one bar that says how big the picture is for the open view; absent data is NO_DATA, never zero. */
export function GeoSummary({ view, flows, reference }: { readonly view: ViewId; readonly flows: GeoFlows | null; readonly reference: GeoReference | null }) {
  if (view === 'jurisdictions') {
    const r = summarizeReference(reference);
    if (!r) return <Chip>NO_DATA</Chip>;
    return (
      <p className="text-xs text-cx-ink-soft">
        <Strong>{r.fatf.call_for_action}</Strong> on the call-for-action list · <Strong>{r.fatf.increased_monitoring}</Strong> under increased monitoring
      </p>
    );
  }
  const s = summarize(flows);
  if (!s) return <Chip>NO_DATA</Chip>;
  if (view === 'logins') {
    return s.flaggedAccounts === 0 && flows!.mismatch_pairs.length === 0 ? (
      <Chip>NO_DATA</Chip>
    ) : (
      <p className="text-xs text-cx-ink-soft">
        <Strong>{COUNT.format(s.flaggedAccounts)}</Strong> accounts flagged across <Strong>{COUNT.format(flows!.mismatch_pairs.length)}</Strong> country pairs
      </p>
    );
  }
  if (s.corridorVolumeUsd === null) return <Chip>NO_DATA</Chip>;
  if (!s.exposure) return <p className="text-xs text-cx-muted">Tiers unavailable: the reference layer is needed to rate corridors.</p>;
  return <ExposureBar exposure={s.exposure} total={s.corridorVolumeUsd} />;
}
