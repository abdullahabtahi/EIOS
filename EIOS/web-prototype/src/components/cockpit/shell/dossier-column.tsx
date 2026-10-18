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
      className={`relative shrink-0 whitespace-nowrap border px-3 py-1 text-label font-mono cursor-pointer outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
        active ? 'bg-white border-cx-line shadow-xs font-bold text-cx-ink' : 'border-transparent text-slate-600 hover:text-cx-ink'
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
      {/* The same height, ground and segmented control as the canvas bar beside it, so the two headers read as one line. */}
      <div className="flex h-11 shrink-0 items-center border-b border-slate-200 bg-white px-3">
      <div role="tablist" aria-label="Dossier or chat" className="flex items-center bg-cx-sub p-0.5 border border-cx-line">
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
