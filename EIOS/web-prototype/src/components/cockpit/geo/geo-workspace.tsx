'use client';

import * as React from 'react';
import { buildLayers, type HighlightArc, type HoverPoint } from './geo-layers';
import { cameraFor, cameraForCodes, type CameraTarget } from './geo-camera';
import { useGeoAccount } from './geo-account';
import { describeSelection } from './geo-format';
import { focusFor } from './geo-focus';
import { formatGeoUrl, parseGeoUrl } from './geo-url';
import { GeoLegend } from './geo-legend';
import { GeoMap } from './geo-map';
import { GeoPanel } from './geo-panel';
import { GeoTooltip } from './geo-tooltip';
import { GeoViewSwitcher } from './geo-view-switcher';
import { DEFAULT_VIEW, viewOf, type ViewId } from './geo-views';
import { dataOf, useGeoResource } from './use-geo-resource';
import type { GeoAccount, GeoFlows, GeoReference, GeoSelection, LayerId } from './geo-types';
import { Icon } from '@/components/ui/icon';

interface Hover {
  readonly selection: NonNullable<GeoSelection>;
  readonly point: HoverPoint;
}

/**
 * Map-first workspace. It opens on one question (the corridors view) with only that view's marks drawn; the panel
 * on the right lists where to look first. Hover previews a mark, click pins it, Esc puts it down.
 */
export function GeoWorkspace({ initialSearch }: { readonly initialSearch?: string } = {}) {
  const reference = useGeoResource<GeoReference>('/api/cockpit/geo/reference');
  const flows = useGeoResource<GeoFlows>('/api/cockpit/geo/flows');
  // The address bar is the state's home: a shared link opens on the same view and pick.
  // The server passes the search string so its render and the browser's agree; without it (tests, embeds) read the URL.
  const [initial] = React.useState(() =>
    parseGeoUrl(initialSearch ?? (typeof window === 'undefined' ? '' : window.location.search)),
  );
  const [view, setView] = React.useState<ViewId>(initial.view ?? DEFAULT_VIEW);
  const [visible, setVisible] = React.useState<ReadonlySet<LayerId>>(viewOf(initial.view ?? DEFAULT_VIEW).layers);
  const [hover, setHover] = React.useState<Hover | null>(null);
  const [selected, setSelected] = React.useState<GeoSelection>(initial.selection);
  const [target, setTarget] = React.useState<CameraTarget | null>(null);
  const flownToInitial = React.useRef(false);
  const mapBox = React.useRef<HTMLDivElement>(null);

  const referenceData = dataOf(reference);
  const flowData = dataOf(flows);

  const changeView = React.useCallback(
    (id: ViewId) => {
      const focus = focusFor(id, flowData, referenceData);
      setView(id);
      setVisible(viewOf(id).layers);
      setSelected(null);
      setHover(null);
      setTarget(focus ? { kind: 'point', ...focus } : null); // each view opens on its own framing; a view with no data leaves the camera alone
    },
    [flowData, referenceData],
  );
  const toggle = React.useCallback((id: LayerId) => {
    setVisible((prev) => (prev.has(id) ? new Set([...prev].filter((x) => x !== id)) : new Set([...prev, id])));
  }, []);
  const clear = React.useCallback(() => setSelected(null), []);
  const pickAccount = React.useCallback((id: string) => setSelected({ kind: 'account', id }), []);
  const account = useGeoAccount(selected?.kind === 'account' ? selected.id : null);
  const accountData = account?.status === 'ready' ? account.data : null;

  // An account is framed once its evidence arrives: its home and every country it logs in from.
  const framed = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (!accountData || framed.current === accountData.account_id) return;
    framed.current = accountData.account_id;
    const codes = [accountData.kyc_country, ...accountData.login_countries.map((c) => c.iso2)];
    setTarget(cameraForCodes(codes, referenceData));
  }, [accountData, referenceData]);

  const highlight = React.useMemo(() => highlightFor(selected, flowData, accountData), [selected, flowData, accountData]);
  const pickFromList = React.useCallback(
    (selection: NonNullable<GeoSelection>) => {
      setSelected(selection);
      setTarget(cameraFor(selection, flowData, referenceData));
    },
    [flowData, referenceData],
  );

  React.useEffect(() => {
    const next = formatGeoUrl(window.location.search, view, selected);
    if (next !== window.location.search) window.history.replaceState(window.history.state, '', `${window.location.pathname}${next}`);
  }, [view, selected]);

  // A pick that came in with the URL is flown to once its data can place it.
  const initialTarget = React.useMemo(
    () => (initial.selection ? cameraFor(initial.selection, flowData, referenceData) : null),
    [initial.selection, flowData, referenceData],
  );
  React.useEffect(() => {
    if (flownToInitial.current || !initialTarget) return;
    flownToInitial.current = true;
    setTarget(initialTarget);
  }, [initialTarget]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setSelected(null);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const onHover = React.useCallback((selection: GeoSelection, point?: HoverPoint) => {
    setHover(selection && point ? { selection, point } : null);
  }, []);

  // The map's size, so a tooltip can flip away from an edge.
  const [box, setBox] = React.useState({ width: 0, height: 0 });
  React.useEffect(() => {
    const el = mapBox.current;
    if (!el) return;
    const measure = () => setBox({ width: el.clientWidth, height: el.clientHeight });
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const layers = React.useMemo(
    () => buildLayers(flowData, referenceData, visible, selected, { onHover, onSelect: setSelected }, highlight),
    [flowData, referenceData, visible, selected, onHover, highlight],
  );
  const focus = React.useMemo(() => focusFor(view, flowData, referenceData), [view, flowData, referenceData]);

  const tip = hover ? describeSelection(flowData, referenceData, hover.selection) : null;
  const waitingOnFlows = view !== 'jurisdictions' && flows.status === 'loading';

  return (
    <div className="flex h-full min-h-0 flex-col lg:flex-row">
      <div ref={mapBox} className="relative min-h-0 min-w-0 flex-[3] lg:flex-1">
        <GeoMap layers={layers} focus={focus} target={target} />
        <div className="absolute left-3 top-3 z-10">
          <GeoViewSwitcher current={view} onChange={changeView} />
        </div>
        {waitingOnFlows && (
          <p role="status" className="absolute left-1/2 top-3 z-10 flex -translate-x-1/2 items-center gap-2 border border-cx-line bg-white px-3 py-1.5 text-xs text-cx-ink-soft shadow-md">
            <Icon icon="progress_activity" size="sm" className="animate-spin text-cx-accent motion-reduce:animate-none" />
            Reading customer flows from the engine…
          </p>
        )}
        <div className="pointer-events-none absolute bottom-6 left-3 z-10">
          <GeoLegend visible={visible} flows={flowData} />
        </div>
        {tip && hover && <GeoTooltip view={tip} point={hover.point} bounds={box} />}
      </div>
      <div className="min-h-0 flex-[2] border-t border-cx-line bg-white lg:w-[22rem] lg:flex-none lg:border-l lg:border-t-0">
        <GeoPanel
          view={viewOf(view)}
          flows={flows}
          reference={reference}
          visible={visible}
          onToggle={toggle}
          selected={selected}
          onSelect={pickFromList}
          onClear={clear}
          onPickAccount={pickAccount}
          account={account}
        />
      </div>
    </div>
  );
}

/** Arcs for the current pick: a shared exit and the homes of its users, or an account's home and its login countries. */
function highlightFor(selected: GeoSelection, flows: GeoFlows | null, account: GeoAccount | null): readonly HighlightArc[] {
  if (selected?.kind === 'gateway') {
    const g = flows?.gateways?.find((x) => x.gateway_id === selected.id);
    return g ? g.home_countries.map((h) => ({ from: h.iso2, to: g.country, weight: h.accounts })) : [];
  }
  if (selected?.kind === 'account' && account && account.account_id === selected.id) {
    return account.login_countries
      .filter((c) => c.iso2 !== account.kyc_country)
      .map((c) => ({ from: account.kyc_country, to: c.iso2, weight: c.sessions }));
  }
  return [];
}
