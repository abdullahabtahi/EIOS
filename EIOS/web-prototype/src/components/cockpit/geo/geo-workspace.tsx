'use client';

import * as React from 'react';
import type { ViewCommand } from '../state/cockpit-types';
import { DEFAULT_BASIS, type BasisId } from './geo-basis';
import { buildLayers, type HighlightArc, type HoverPoint, type ListChangeMarks } from './geo-layers';
import { cameraFor, cameraForCodes, type CameraTarget } from './geo-camera';
import { useGeoAccount } from './geo-account';
import { GeoAsk } from './geo-ask';
import { describeSelection } from './geo-format';
import { focusFor } from './geo-focus';
import { beforeTiers, changeCount, changeNotes, withChangeNote } from './geo-compare';
import { type CompareSide, GeoCompareBar } from './geo-compare-bar';
import { GeoListChangePanel } from './geo-list-change';
import { geoSuggestions, mapContextOf, type MapState, moveLabel, stateAfterMove } from './geo-moves';
import { GeoMoveToast } from './geo-move-toast';
import { formatGeoUrl, parseGeoUrl } from './geo-url';
import { GeoLegend } from './geo-legend';
import { GeoMap } from './geo-map';
import { GeoPanel } from './geo-panel';
import { GeoChatLauncher, type LauncherStatus } from './geo-chat-launcher';
import { GeoChatWindow } from './geo-chat-window';
import { useChatDock } from './use-chat-dock';
import { GeoTooltip } from './geo-tooltip';
import { GeoViewSwitcher } from './geo-view-switcher';
import { DEFAULT_VIEW, viewOf, type ViewId } from './geo-views';
import { dataOf, useGeoResource } from './use-geo-resource';
import { useListChange } from './use-list-change';
import type { GeoAccount, GeoFlows, GeoListChange, GeoReference, GeoSelection, LayerId, ListId } from './geo-types';
import { Icon } from '@/components/ui/icon';

interface Hover {
  readonly selection: NonNullable<GeoSelection>;
  readonly point: HoverPoint;
}

interface MoveNotice {
  readonly label: string;
  readonly auto: boolean;
}

const MAX_HISTORY = 20;

/**
 * Map-first workspace. It opens on one question (the corridors view) with only that view's marks drawn; the panel
 * on the right lists where to look first, or holds the assistant. Hover previews a mark, click pins it, Esc puts it
 * down. The assistant moves the map only to objects its tools returned; every move says so and can be undone.
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
  const [basis, setBasis] = React.useState<BasisId>(initial.basis ?? DEFAULT_BASIS);
  const [hover, setHover] = React.useState<Hover | null>(null);
  const [selected, setSelected] = React.useState<GeoSelection>(initial.selection);
  const [target, setTarget] = React.useState<CameraTarget | null>(null);
  const [compare, setCompare] = React.useState<ListId | null>(null);
  const [side, setSide] = React.useState<CompareSide>('after');
  const dock = useChatDock();
  const [asking, setAsking] = React.useState(false);
  const [unread, setUnread] = React.useState(false);
  const [intent, setIntent] = React.useState<{ id: number; text?: string } | null>(null);
  const [history, setHistory] = React.useState<readonly MapState[]>([]);
  const [notice, setNotice] = React.useState<MoveNotice | null>(null);
  const flownToInitial = React.useRef(false);
  const mapBox = React.useRef<HTMLDivElement>(null);

  const referenceData = dataOf(reference);
  const flowData = dataOf(flows);
  // Both lists' latest changes are read once the Jurisdictions view is open, so each list can say how many countries it moved.
  const onJurisdictions = view === 'jurisdictions';
  const fatfChange = useListChange(onJurisdictions ? 'fatf' : null);
  const euChange = useListChange(onJurisdictions ? 'eu' : null);
  const changes = { fatf: fatfChange, eu: euChange };
  const listChange = compare ? changes[compare] : null;
  const changeCounts: Partial<Record<ListId, number>> = {
    ...(fatfChange?.status === 'ready' ? { fatf: changeCount(fatfChange.data) } : {}),
    ...(euChange?.status === 'ready' ? { eu: changeCount(euChange.data) } : {}),
  };

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

  // The map's state as one value: what a move changes, what Back restores, and what a question carries.
  const mapState = React.useMemo<MapState>(() => ({ view, selected, basis }), [view, selected, basis]);
  const restore = React.useCallback(
    (state: MapState) => {
      setView(state.view);
      setVisible(viewOf(state.view).layers);
      setBasis(state.basis);
      setSelected(state.selected);
      setHover(null);
      const focus = focusFor(state.view, flowData, referenceData);
      setTarget(cameraFor(state.selected, flowData, referenceData) ?? (focus ? { kind: 'point', ...focus } : null));
    },
    [flowData, referenceData],
  );
  const applyMove = React.useCallback(
    (move: ViewCommand, auto: boolean) => {
      setHistory((past) => [...past, mapState].slice(-MAX_HISTORY));
      restore(stateAfterMove(mapState, move));
      framed.current = null; // an account the assistant points at is framed again, even if it was framed before
      setNotice({ label: moveLabel(move), auto });
    },
    [mapState, restore],
  );
  const goBack = React.useCallback(() => {
    const previous = history[history.length - 1];
    if (!previous) return;
    setHistory(history.slice(0, -1));
    restore(previous);
    setNotice(null);
  }, [history, restore]);

  React.useEffect(() => {
    const next = formatGeoUrl(window.location.search, view, selected, basis);
    if (next !== window.location.search) window.history.replaceState(window.history.state, '', `${window.location.pathname}${next}`);
  }, [view, selected, basis]);

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
    // Escape puts the pick down, but not while someone is typing: in the Ask box or a filter it belongs to that field.
    const onKey = (e: KeyboardEvent) => {
      const el = e.target instanceof HTMLElement ? e.target : null;
      const typing = !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));
      if (e.key === 'Escape' && !typing) setSelected(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // The assistant opens ready for a question: with the text given (a hint), or empty (the slash key, the launcher).
  const show = dock.show;
  const openChat = React.useCallback(
    (prefill?: string) => {
      show();
      setUnread(false);
      setIntent((prev) => ({ id: (prev?.id ?? 0) + 1, ...(prefill !== undefined ? { text: prefill } : {}) }));
    },
    [show],
  );
  // An answer that lands while the window is closed is marked on the launcher until it is opened; the closure that
  // delivers it was made when the question was asked, so it reads the mode from here, not from its own render.
  const modeNow = React.useRef(dock.mode);
  React.useEffect(() => {
    modeNow.current = dock.mode;
  }, [dock.mode]);
  const answered = React.useCallback(() => {
    if (modeNow.current === 'closed') setUnread(true);
  }, []);
  React.useEffect(() => {
    const onSlash = (e: KeyboardEvent) => {
      if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
      const el = e.target instanceof HTMLElement ? e.target : null;
      if (el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName))) return;
      e.preventDefault();
      openChat();
    };
    window.addEventListener('keydown', onSlash);
    return () => window.removeEventListener('keydown', onSlash);
  }, [openChat]);
  const launcherStatus: LauncherStatus = asking ? 'pending' : unread ? 'unread' : 'idle';
  const hint = selected ? (geoSuggestions(selected)[0] ?? null) : null;

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
  // The map outlines what the latest change of the list in view named, whether or not the comparison is open.
  const outlineList: ListId | null = compare ?? (basis === 'fatf' || basis === 'eu' ? basis : null);
  const outlined = outlineList ? changes[outlineList] : null;
  const outlineData = outlined?.status === 'ready' ? outlined.data : null;
  const marks = React.useMemo(() => (view === 'jurisdictions' ? marksOf(outlineData) : null), [view, outlineData]);
  const notes = React.useMemo(() => (view === 'jurisdictions' && outlineData ? changeNotes(outlineData) : null), [view, outlineData]);
  const earlier = React.useMemo(
    () => (view === 'jurisdictions' && side === 'before' && listChange?.status === 'ready' ? beforeTiers(listChange.data) : null),
    [view, side, listChange],
  );
  const layers = React.useMemo(
    () => buildLayers(flowData, referenceData, visible, selected, { onHover, onSelect: setSelected }, highlight, basis, marks, earlier),
    [flowData, referenceData, visible, selected, onHover, highlight, basis, marks, earlier],
  );
  const focus = React.useMemo(() => focusFor(view, flowData, referenceData), [view, flowData, referenceData]);

  const described = hover ? describeSelection(flowData, referenceData, hover.selection) : null;
  const tip = described && hover?.selection?.kind === 'country' ? withChangeNote(described, notes?.get(hover.selection.id)) : described;
  const waitingOnFlows = view !== 'jurisdictions' && flows.status === 'loading';
  const listChangeSlot = compare ? (
    <GeoListChangePanel state={listChange} onSelect={pickFromList} />
  ) : null;
  // The comparison belongs to one list: moving the basis to the other list moves it, and Basel has no change to compare.
  const changeBasis = (id: BasisId) => {
    setBasis(id);
    setCompare((now) => (now && (id === 'fatf' || id === 'eu') ? id : null));
  };
  const openCompare = (id: ListId) => {
    setBasis(id);
    setCompare(id);
    setSide('after');
  };
  const setMode = (changing: boolean) => (changing ? openCompare(basis === 'fatf' || basis === 'eu' ? basis : 'fatf') : setCompare(null));
  const compareLabel = listChange?.status === 'ready' ? listChange.data.after.label : 'Reading the change…';

  return (
    <div className="geo-inter relative flex h-full min-h-0 flex-col lg:flex-row">
      <GeoChatWindow mode={dock.mode} pos={dock.pos} bounds={box} onMove={dock.move} onSettle={dock.settle} onDock={dock.dock} onFloat={dock.float} onClose={dock.close}>
        <GeoAsk context={mapContextOf(mapState)} selected={selected} onMove={applyMove} onPending={setAsking} onAnswered={answered} intent={intent} />
      </GeoChatWindow>
      <div ref={mapBox} role="region" aria-label="World map" aria-describedby="geo-map-help" className="relative min-h-0 min-w-0 flex-[3] lg:flex-1">
        <p id="geo-map-help" className="sr-only">
          The map draws what the side panel lists. Use the list to move through countries and corridors with the arrow keys; the map itself pans with the arrow keys and zooms with plus and minus.
        </p>
        <GeoMap layers={layers} focus={focus} target={target} />
        <div className="absolute left-3 top-3 z-10">
          <GeoViewSwitcher current={view} onChange={changeView} />
        </div>
        {compare && view === 'jurisdictions' && (
          <div className="absolute left-3 top-14 z-10">
            <GeoCompareBar side={side} onSide={setSide} label={compareLabel} />
          </div>
        )}
        {waitingOnFlows && (
          <p role="status" className="absolute left-1/2 top-3 z-10 flex -translate-x-1/2 items-center gap-2 border border-cx-line bg-white px-3 py-1.5 text-xs text-cx-ink-soft shadow-md">
            <Icon icon="progress_activity" size="sm" className="animate-spin text-cx-accent motion-reduce:animate-none" />
            Reading customer flows from the engine…
          </p>
        )}
        <div className="pointer-events-none absolute bottom-6 left-3 z-10">
          <GeoLegend visible={visible} flows={flowData} basis={basis} outlines={marks ? { added: marks.added.size > 0, removed: marks.removed.size > 0 } : null} />
        </div>
        {dock.mode === 'closed' && <GeoChatLauncher status={launcherStatus} hint={hint} onOpen={openChat} />}
        {tip && hover && <GeoTooltip view={tip} point={hover.point} bounds={box} />}
        {notice && (
          <GeoMoveToast label={notice.label} auto={notice.auto} canGoBack={history.length > 0} onBack={goBack} onDismiss={() => setNotice(null)} />
        )}
      </div>
      <div className="min-h-0 flex-[2] border-t border-cx-line bg-white lg:w-[24rem] lg:flex-none lg:border-l lg:border-t-0">
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
          basis={basis}
          onBasis={changeBasis}
          changeCounts={changeCounts}
          comparing={compare}
          onMode={setMode}
          changeNote={(iso2) => notes?.get(iso2)}
          listChange={listChangeSlot}
        />
      </div>
    </div>
  );
}

/** The countries a list change names, for the map's outlines; null until the change has loaded. */
function marksOf(change: GeoListChange | null): ListChangeMarks | null {
  if (!change) return null;
  return {
    added: new Set(change.added.countries.map((c) => c.iso2)),
    removed: new Set(change.removed.countries.map((c) => c.iso2)),
  };
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
