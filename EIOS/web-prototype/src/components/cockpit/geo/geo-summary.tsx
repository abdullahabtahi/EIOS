import * as React from 'react';
import { Chip } from '../ui/chip';
import { summarize, summarizeReference } from './geo-aggregates';
import type { BasisId } from './geo-basis';
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

/** Who the lens can judge at all: a client with too few events is not assessable, and saying so is part of the answer. */
export function Coverage({ assessable, clients }: { readonly assessable: number | null | undefined; readonly clients: number | undefined }) {
  if (assessable == null || !clients) return null;
  return (
    <p className="text-label text-cx-muted">
      This lens can judge <span className="font-mono tabular-nums text-cx-ink-soft">{COUNT.format(assessable)}</span> of{' '}
      <span className="font-mono tabular-nums text-cx-ink-soft">{COUNT.format(clients)}</span> clients; the rest have too few events to tell.
    </p>
  );
}

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
export function GeoSummary({ view, flows, reference, basis = 'fatf' }: { readonly view: ViewId; readonly flows: GeoFlows | null; readonly reference: GeoReference | null; readonly basis?: BasisId }) {
  if (view === 'jurisdictions') {
    const r = summarizeReference(reference);
    if (!r) return <Chip>NO_DATA</Chip>;
    if (basis === 'eu') {
      return (
        <p className="text-xs text-cx-ink-soft">
          <Strong>{r.eu.listed}</Strong> on the EU list · <Strong>{r.eu.alsoFatf}</Strong> also on a FATF list · <Strong>{r.eu.euOnly}</Strong> only the EU names
        </p>
      );
    }
    if (basis === 'basel') {
      return (
        <p className="text-xs text-cx-ink-soft">
          <Strong>{r.basel.rated}</Strong> countries scored: <Strong>{r.basel.higher}</Strong> higher risk, <Strong>{r.basel.medium}</Strong> medium,{' '}
          <Strong>{r.basel.lower}</Strong> lower. The rest are not in the public index.
        </p>
      );
    }
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
      <div className="space-y-1.5">
        <p className="text-xs text-cx-ink-soft">
          <Strong>{COUNT.format(s.flaggedAccounts)}</Strong> accounts flagged across <Strong>{COUNT.format(flows!.mismatch_pairs.length)}</Strong> country pairs
        </p>
        <Coverage assessable={flows!.coverage?.mismatch_assessable} clients={flows!.coverage?.clients} />
      </div>
    );
  }
  if (s.corridorVolumeUsd === null) return <Chip>NO_DATA</Chip>;
  if (!s.exposure) return <p className="text-xs text-cx-muted">Tiers unavailable: the reference layer is needed to rate corridors.</p>;
  return (
    <div className="space-y-2">
      <ExposureBar exposure={s.exposure} total={s.corridorVolumeUsd} />
      <Coverage assessable={flows!.coverage?.corridor_assessable} clients={flows!.coverage?.clients} />
    </div>
  );
}
