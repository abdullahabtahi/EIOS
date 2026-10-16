'use client';

import * as React from 'react';
import { Icon } from '@/components/ui/icon';

/** The glyph the cockpit rail already uses for "Ask copilot", so the assistant has one face wherever it appears. */
export const ASSISTANT_ICON = 'terminal';

export type LauncherStatus = 'idle' | 'pending' | 'unread';

const STATUS_WORD: Readonly<Record<LauncherStatus, string>> = {
  idle: '',
  pending: ', answer on its way',
  unread: ', new answer',
};

/**
 * What stands for the assistant while it is closed: a button that shows it is there (a ring that pulses a few times and then
 * rests; round, like a floating action), whether an answer is on its way or waiting, and, when something is picked on the map, a question worth asking about it.
 */
export function GeoChatLauncher({ status, hint, onOpen }: { readonly status: LauncherStatus; readonly hint: string | null; readonly onOpen: (prefill?: string) => void }) {
  return (
    <div className="absolute bottom-32 right-3 z-20 flex max-w-[calc(100%-1.5rem)] items-center gap-2">
      {hint && (
        <button
          type="button"
          onClick={() => onOpen(hint)}
          className="geo-chat-in min-w-0 cursor-pointer truncate rounded-full border border-cx-line bg-white px-3 py-1.5 text-label text-cx-ink-soft shadow-md outline-none hover:border-cx-accent hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent">
          {hint}
        </button>
      )}
      <button
        type="button"
        data-status={status}
        aria-label={`Ask the assistant${STATUS_WORD[status]}`}
        title="Ask the assistant (/)"
        onClick={() => onOpen()}
        className="relative flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full border border-chrome-line bg-cockpit-rail text-chrome-accent shadow-lg outline-none transition-[transform,filter] hover:scale-105 hover:brightness-125 focus-visible:ring-2 focus-visible:ring-chrome-accent focus-visible:ring-offset-2 motion-reduce:transition-none motion-reduce:hover:scale-100">
        <span key={hint ?? 'rest'} aria-hidden="true" className="geo-ask-ping pointer-events-none absolute -inset-px rounded-full border-2 border-chrome-accent" />
        <Icon icon={status === 'pending' ? 'progress_activity' : ASSISTANT_ICON} className={status === 'pending' ? 'animate-spin motion-reduce:animate-none' : ''} />
        {status === 'unread' && <span aria-hidden="true" className="absolute right-0 top-0 size-3 rounded-full border-2 border-cockpit-rail bg-chrome-accent" />}
      </button>
    </div>
  );
}
