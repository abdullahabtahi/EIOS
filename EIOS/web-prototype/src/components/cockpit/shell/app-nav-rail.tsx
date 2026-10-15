'use client';

/**
 * EIOS Global Navigation Rail (dark institutional chrome).
 * A permanent 48px full-height icon strip at the left edge. Hovering (or focusing)
 * it expands the same element to a 232px labelled panel as an overlay, so the
 * workspace never reflows. Icons stay pinned to a 48px column, so nothing jumps.
 * Lists top-level sections only; personas are switched from the header strip.
 * Built on the Icon component with the cockpit's chrome tokens.
 */

import * as React from 'react';
import { Icon } from '@/components/ui/icon';
import { useCockpit } from '../state/cockpit-context';
import Link from 'next/link';
import { APP_NAV_ITEMS, DEFAULT_APP_NAV_ID, type AppNavId } from './app-nav-items';
import { useNavReveal } from './use-nav-reveal';
import { getPipelineStatus, type PipelineTone } from '../state/pipeline-status';

const TONE_DOT: Record<PipelineTone, string> = {
  ok: 'bg-green-400',
  warn: 'bg-amber-400',
  bad: 'bg-red-400',
  neutral: 'bg-slate-400',
};

const ROW =
  'group/row w-full flex items-center text-left text-xs outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-chrome-accent';
const ICON_COL = 'w-12 shrink-0 flex items-center justify-center';
const LABEL =
  'flex-1 min-w-0 pr-3 whitespace-nowrap opacity-0 transition-opacity duration-150 group-data-[state=expanded]/rail:opacity-100 motion-reduce:transition-none';
const KBD =
  'px-1 py-0.5 bg-white/8 border border-white/15 text-label font-mono text-slate-300 leading-none';

function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el || !el.tagName) return false;
  return el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable;
}

function NavRows({ currentId, onSelect }: { currentId: AppNavId; onSelect: () => void }) {
  return (
    <ul className="py-2">
      {APP_NAV_ITEMS.map((item) => {
        const isCurrent = item.id === currentId;
        const className = `${ROW} h-11 ${
          !item.available
            ? 'cursor-not-allowed text-slate-400'
            : isCurrent
              ? 'bg-chrome-active text-white font-semibold cursor-pointer'
              : 'cursor-pointer text-slate-200 hover:bg-chrome-hover hover:text-white'
        }`;
        const body = (
          <>
            <span className={ICON_COL}>
              <Icon
                icon={item.icon}
                size="sm"
                className={isCurrent ? 'text-chrome-accent' : item.available ? 'text-slate-300' : 'text-slate-500'}
              />
            </span>
            <span className={`${LABEL} flex items-center gap-2`}>
              <span className="flex-1 min-w-0">
                <span className="block truncate">{item.label}</span>
                <span className="block truncate text-label font-normal text-slate-400">{item.description}</span>
              </span>
              {!item.available && (
                <span className="px-1 py-0.5 border border-white/20 text-label font-mono font-bold tracking-wider text-slate-300 leading-none">
                  SOON
                </span>
              )}
            </span>
          </>
        );
        return (
          <li key={item.id}>
            {item.available && item.href && !isCurrent ? (
              <Link
                href={item.href}
                data-testid={`nav-app-${item.id}`}
                onClick={onSelect}
                className={className}>
                {body}
              </Link>
            ) : (
              <button
                type="button"
                data-testid={`nav-app-${item.id}`}
                aria-current={isCurrent ? 'page' : undefined}
                aria-disabled={item.available ? undefined : true}
                onClick={item.available ? onSelect : undefined}
                className={className}>
                {body}
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function RailFooter({ onCommandBar, onShortcuts }: { onCommandBar: () => void; onShortcuts?: () => void }) {
  const { state } = useCockpit();
  const pipeline = getPipelineStatus(state);
  const replaying = pipeline.label === 'Replay';
  const footerRow = `${ROW} h-10 cursor-pointer text-slate-200 hover:bg-chrome-hover hover:text-white`;

  return (
    <div className="border-t border-chrome-line">
      <button type="button" onClick={onCommandBar} className={footerRow}>
        <span className={ICON_COL}>
          <Icon icon="terminal" size="sm" className="text-chrome-accent" />
        </span>
        <span className={`${LABEL} flex items-center`}>
          <span className="flex-1">Ask copilot</span>
          <kbd className={KBD}>⌘K</kbd>
        </span>
      </button>

      {onShortcuts && (
        <button type="button" onClick={onShortcuts} className={footerRow}>
          <span className={ICON_COL}>
            <Icon icon="keyboard" size="sm" className="text-slate-300" />
          </span>
          <span className={`${LABEL} flex items-center`}>
            <span className="flex-1">Keyboard Shortcuts</span>
            <kbd className={KBD}>?</kbd>
          </span>
        </button>
      )}

      <div className="h-14 flex items-center border-t border-chrome-line">
        <span className={ICON_COL}>
          <span className="relative">
            <span className="size-7 bg-white/10 border border-white/15 text-white flex items-center justify-center font-mono font-bold text-label">
              {state.operator.officerId.slice(0, 2)}
            </span>
            <span
              className={`absolute -right-1 -bottom-1 size-2 rounded-full border-2 border-cockpit-rail ${TONE_DOT[pipeline.tone]}`}
              title={`Pipeline: ${pipeline.label}`}
            />
          </span>
        </span>
        <span className={`${LABEL} text-left`}>
          <span data-testid="nav-operator-name" className="block truncate text-label font-bold text-white leading-tight">
            {state.operator.name}
          </span>
          <span className="block truncate text-label font-mono uppercase tracking-wider text-slate-400 leading-tight">
            {state.operator.clearanceLevel.replace(/_/g, ' ')}
          </span>
          <span data-testid="nav-pipeline-status" className="block truncate text-label font-mono text-slate-300 leading-tight mt-0.5">
            Pipeline: <span className="font-semibold text-white">{pipeline.label}</span>
            <span className="mx-1 text-slate-600">|</span>
            RTT: <span className="font-semibold tabular-nums text-white">{replaying ? '—' : `${state.systemLatencyMs}ms`}</span>
          </span>
        </span>
      </div>
    </div>
  );
}

export function AppNavRail({
  onOpenShortcuts,
  currentId = DEFAULT_APP_NAV_ID,
}: { onOpenShortcuts?: () => void; currentId?: AppNavId } = {}) {
  const { openChat } = useCockpit();
  const { open, openNow, closeNow, toggle, scheduleOpen, scheduleClose, cancelScheduled } = useNavReveal();
  const rootRef = React.useRef<HTMLDivElement>(null);
  const pointerInside = React.useRef(false);

  React.useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        closeNow();
        return;
      }
      if (e.key === '\\' && !e.metaKey && !e.ctrlKey && !e.altKey && !isTypingTarget(e.target)) {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, closeNow, toggle]);

  React.useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target;
      if (target instanceof Node && rootRef.current?.contains(target)) return;
      closeNow();
    };
    document.addEventListener('pointerdown', onPointerDown, true);
    return () => document.removeEventListener('pointerdown', onPointerDown, true);
  }, [open, closeNow]);

  const handleBlur = (e: React.FocusEvent) => {
    const next = e.relatedTarget as Node | null;
    if (next && rootRef.current?.contains(next)) return;
    if (!pointerInside.current) scheduleClose();
  };

  return (
    <div
      ref={rootRef}
      data-slot="app-nav"
      className="relative z-[45] h-full w-12 shrink-0"
      onFocus={openNow}
      onBlur={handleBlur}>
      {/* Dims the workspace while expanded so the overlay reads as a deliberate layer */}
      <div
        data-slot="app-nav-scrim"
        data-state={open ? 'expanded' : 'collapsed'}
        aria-hidden="true"
        className={`fixed inset-0 bg-slate-950/40 pointer-events-none transition-opacity duration-200 motion-reduce:transition-none ${
          open ? 'opacity-100' : 'opacity-0'
        }`}
      />
      <aside
        data-slot="app-nav-rail"
        data-state={open ? 'expanded' : 'collapsed'}
        aria-label="Global navigation"
        onPointerEnter={() => {
          pointerInside.current = true;
          if (open) cancelScheduled();
          else scheduleOpen();
        }}
        onPointerLeave={() => {
          pointerInside.current = false;
          if (open) scheduleClose();
          else cancelScheduled();
        }}
        className={`group/rail absolute inset-y-0 left-0 flex max-w-[85vw] flex-col overflow-hidden bg-cockpit-rail text-slate-200 border-r border-chrome-line select-none transition-[width,box-shadow] duration-200 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none ${
          open ? 'w-[232px] shadow-xl' : 'w-12 shadow-none'
        }`}>
        {/* Brand row aligns with the header's first row */}
        <div className="h-11 shrink-0 flex items-center border-b border-chrome-line">
          <span className={ICON_COL}>
            <span className="size-6 bg-white text-slate-900 flex items-center justify-center font-mono font-bold text-xs tracking-tight">
              E
            </span>
          </span>
          <span className={`${LABEL} flex items-center justify-between`}>
            <span className="font-mono font-bold tracking-widest text-xs text-white uppercase">EIOS</span>
            <kbd className={KBD} title="Toggle navigation">\</kbd>
          </span>
        </div>

        <nav aria-label="Primary" className="flex-1 overflow-y-auto overflow-x-hidden">
          <NavRows currentId={currentId} onSelect={closeNow} />
        </nav>

        <RailFooter
          onCommandBar={() => {
            openChat();
            closeNow();
          }}
          onShortcuts={
            onOpenShortcuts
              ? () => {
                  onOpenShortcuts();
                  closeNow();
                }
              : undefined
          }
        />
      </aside>
    </div>
  );
}
