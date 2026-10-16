'use client';

import * as React from 'react';
import type { BasisId } from './geo-basis';
import { GeoAddressCheck } from './geo-address-check';
import { GeoBasisSwitcher } from './geo-basis-switcher';
import { withChangeNote } from './geo-compare';
import { describeSelection } from './geo-format';
import { GeoAccountDetail } from './geo-account-detail';
import { GeoDetail } from './geo-detail';
import { GeoLayerToggles } from './geo-layer-toggles';
import { GeoLeadList } from './geo-lead-list';
import { leadsFor } from './geo-leads';
import { GeoSources } from './geo-sources';
import { GeoStatus } from './geo-status';
import { GeoSummary } from './geo-summary';
import { VIEW_PANEL_ID, viewTabId } from './geo-view-switcher';
import { dataOf, type ResourceState } from './use-geo-resource';
import type { GeoAccount, GeoFlows, GeoReference, GeoSelection, LayerId, ListId } from './geo-types';
import type { GeoView } from './geo-views';

export interface GeoPanelProps {
  readonly view: GeoView;
  readonly flows: ResourceState<GeoFlows>;
  readonly reference: ResourceState<GeoReference>;
  readonly visible: ReadonlySet<LayerId>;
  readonly onToggle: (id: LayerId) => void;
  readonly selected: GeoSelection;
  readonly onSelect: (selection: NonNullable<GeoSelection>) => void;
  readonly onClear: () => void;
  readonly onPickAccount: (id: string) => void;
  /** The picked account's evidence, when the pick is an account. */
  readonly account: ResourceState<GeoAccount> | null;
  /** Which list colours the Jurisdictions map, and the way to change it. */
  readonly basis: BasisId;
  readonly onBasis: (id: BasisId) => void;
  /** Countries each list's latest change names, the list whose change is open (null: the lists as they stand), and how to switch. */
  readonly changeCounts?: Readonly<Partial<Record<ListId, number>>>;
  readonly comparing?: ListId | null;
  readonly onMode?: (changing: boolean) => void;
  /** What the latest change did to a country, in a line; undefined when it names none. */
  readonly changeNote?: (iso2: string) => string | undefined;
  /** The list-change comparison, shown in the Jurisdictions view (what the latest FATF or EU change does to us). */
  readonly listChange?: React.ReactNode;
}

/** Lenses that cannot draw without their data: a flow needs the engine and the reference layer (which places the countries). */
export function disabledLayers(flows: GeoFlows | null, reference: GeoReference | null): ReadonlySet<LayerId> {
  const off = new Set<LayerId>();
  if (!reference) (['risk', 'offshore'] as const).forEach((id) => off.add(id));
  if (!flows || !reference) (['corridors', 'mismatches'] as const).forEach((id) => off.add(id));
  return off;
}

/**
 * The right-hand panel, read top to bottom: the question this view answers, how big the picture is, the picked
 * mark in full, then where to look first. Layers and sources sit below, collapsed.
 */
export function GeoPanel({ view, flows, reference, visible, onToggle, selected, onSelect, onClear, onPickAccount, account, basis, onBasis, changeCounts = {}, comparing = null, onMode, changeNote, listChange }: GeoPanelProps) {
  const ref = dataOf(reference);
  const fl = dataOf(flows);
  const leads = leadsFor(view.id, fl, ref, basis);
  const described = describeSelection(fl, ref, selected);
  const detail = described && selected?.kind === 'country' ? withChangeNote(described, changeNote?.(selected.id)) : described;
  const changing = view.id === 'jurisdictions' && comparing !== null;
  const changeCount = basis === 'fatf' || basis === 'eu' ? changeCounts[basis] : undefined;
  const needs: readonly { readonly label: string; readonly state: ResourceState<unknown> }[] =
    view.id === 'jurisdictions'
      ? [{ label: 'reference layer', state: reference }]
      : [{ label: 'customer flows', state: flows }, { label: 'reference layer', state: reference }];
  const waiting = needs.filter((n) => n.state.status !== 'ready');
  // Every failure is named; a load in progress is one placeholder, not two.
  const shownWaiting = [...waiting.filter((n) => n.state.status === 'error'), ...waiting.filter((n) => n.state.status === 'loading').slice(0, 1)];

  return (
    <div id={VIEW_PANEL_ID} role="tabpanel" aria-labelledby={viewTabId(view.id)} className="flex h-full flex-col overflow-y-auto">
      <div className="space-y-5 p-4">
        <header className="space-y-3">
          <h2 className="text-pretty text-sm font-semibold leading-snug text-cx-ink">{view.question}</h2>
          {view.id === 'jurisdictions' && ref && (
            <GeoBasisSwitcher current={basis} onChange={onBasis} changeCount={changeCount} changing={changing} onToggleChange={onMode ? () => onMode(!changing) : undefined} />
          )}
          {changing && listChange}
          {waiting.length === 0 && !changing && <GeoSummary view={view.id} flows={fl} reference={ref} basis={basis} />}
          {view.id === 'logins' && (
            <details className="border border-cx-line bg-cx-sub">
              <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-cx-ink-soft outline-none hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent">
                Check an IP address
              </summary>
              <div className="px-3 pb-3">
                <GeoAddressCheck
                  onShowCountry={(iso2) => onSelect({ kind: 'country', id: iso2 })}
                  knownCountries={ref ? new Set(ref.countries.map((c) => c.iso2)) : undefined}
                />
              </div>
            </details>
          )}
        </header>

        {waiting.length > 0 ? (
          <div className="space-y-3">
            {shownWaiting.map((n) => (
              <GeoStatus key={n.label} label={n.label} state={n.state} />
            ))}
          </div>
        ) : (
          <>
            {selected?.kind === 'account' && account ? (
              <GeoAccountDetail accountId={selected.id} state={account} onClear={onClear} onPickAccount={onPickAccount} />
            ) : (
              detail && <GeoDetail view={detail} onClear={onClear} onPickAccount={onPickAccount} onOpenChange={onMode ? () => onMode(true) : undefined} />
            )}
            {!changing && (
              <section aria-label="Where to look first" className="space-y-1">
                <h3 className="text-title font-sans font-semibold text-cx-ink">Where to look first</h3>
                {leads ? <GeoLeadList leads={leads} selected={selected} onSelect={onSelect} /> : null}
              </section>
            )}
          </>
        )}
      </div>
      <div className="mt-auto">
        <GeoLayerToggles visible={visible} disabled={disabledLayers(fl, ref)} onToggle={onToggle} />
        <GeoSources flows={fl} reference={ref} />
      </div>
    </div>
  );
}
