'use client';

/**
 * The centre column: the dossier, or the chat about it, behind one switch. Both stay mounted so a pending answer and
 * a half-typed question survive a switch; the inactive one is only hidden.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { CopilotChat } from './copilot-chat';
import { CopilotDossier } from './copilot-dossier';

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`relative px-3 py-1 text-xs font-medium cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-cx-accent ${
        active ? 'bg-white text-cx-ink border border-cx-line' : 'text-cx-muted hover:text-cx-ink border border-transparent'
      }`}
    >
      {children}
    </button>
  );
}

export function DossierColumn() {
  const { state, openChat, showDossier } = useCockpit();
  const chatShown = state.dossierView === 'chat';
  return (
    <div className="w-full h-full min-w-0 flex flex-col bg-white">
      {/* The same height as the canvas bar beside it so the two headers read as one line; the grey ground and the plain tabs are the dossier's own. */}
      <div className="flex h-11 shrink-0 items-center justify-between gap-3 border-b border-cx-line bg-cx-sub px-3">
        <h2 className="flex min-w-0 items-center gap-2 font-mono text-xs font-bold uppercase tracking-tight text-slate-900">
          <span aria-hidden="true" className="material-symbols-sharp text-base text-cx-accent shrink-0">article</span>
          <span className="truncate">Copilot Dossier</span>
        </h2>
      <div role="tablist" aria-label="Dossier or chat" className="flex items-center gap-1">
        <Tab active={!chatShown} onClick={showDossier}>
          Dossier
        </Tab>
        <Tab active={chatShown} onClick={openChat}>
          Chat
          {state.chatUnread && (
            <span
              data-testid="chat-unread"
              role="status"
              aria-label="New answer"
              className="absolute -top-0.5 -right-0.5 size-2 bg-cx-accent rounded-full"
            />
          )}
        </Tab>
      </div>
      </div>
      <div className={`flex-1 min-h-0 ${chatShown ? 'hidden' : 'flex'}`}>
        <CopilotDossier />
      </div>
      <div className={`flex-1 min-h-0 ${chatShown ? 'flex' : 'hidden'}`}>
        <CopilotChat />
      </div>
    </div>
  );
}
