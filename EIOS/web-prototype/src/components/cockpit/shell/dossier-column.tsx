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
      className={`relative px-3 py-1 text-xs font-medium cursor-pointer transition-colors ${
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
      <div role="tablist" aria-label="Dossier or chat" className="flex items-center gap-1 px-2 py-1.5 bg-cx-sub border-b border-cx-line shrink-0">
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
      <div className={`flex-1 min-h-0 ${chatShown ? 'hidden' : 'flex'}`}>
        <CopilotDossier />
      </div>
      <div className={`flex-1 min-h-0 ${chatShown ? 'flex' : 'hidden'}`}>
        <CopilotChat />
      </div>
    </div>
  );
}
