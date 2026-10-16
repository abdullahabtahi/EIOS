'use client';

import * as React from 'react';
import { Icon } from '@/components/ui/icon';

export type LauncherStatus = 'idle' | 'pending' | 'unread';

const STATUS_WORD: Readonly<Record<LauncherStatus, string>> = {
  idle: '',
  pending: ', answer on its way',
  unread: ', new answer',
};

/**
 * What stands for the assistant while it is closed: a button that shows it is there (a ring that pulses a few times and then
 * rests), whether an answer is on its way or waiting, and, when something is picked on the map, a question worth asking about it.
 */
export function GeoChatLauncher({ status, hint, onOpen }: { readonly status: LauncherStatus; readonly hint: string | null; readonly onOpen: (prefill?: string) => void }) {
  return (
    <div className="absolute bottom-32 right-3 z-20 flex max-w-[calc(100%-1.5rem)] items-center gap-2">
      {hint && (
        <button
          type="button"
          onClick={() => onOpen(hint)}
          className="geo-chat-in min-w-0 cursor-pointer truncate border border-cx-line bg-white px-2.5 py-1.5 text-label text-cx-ink-soft shadow-md outline-none hover:border-cx-accent hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent">
          {hint}
        </button>
      )}
      <button
        type="button"
        data-status={status}
        aria-label={`Ask the assistant${STATUS_WORD[status]}`}
        title="Ask the assistant (/)"
        onClick={() => onOpen()}
        className="relative flex shrink-0 cursor-pointer items-center gap-2 bg-cx-ink px-3.5 py-2 text-xs font-semibold text-white outline-none hover:bg-black focus-visible:ring-2 focus-visible:ring-cx-accent focus-visible:ring-offset-2">
        <span key={hint ?? 'rest'} aria-hidden="true" className="geo-ask-ping pointer-events-none absolute inset-0 border-2 border-cx-accent" />
        <Icon icon={status === 'pending' ? 'progress_activity' : 'auto_awesome'} size="sm" className={status === 'pending' ? 'animate-spin motion-reduce:animate-none' : ''} />
        Ask
        {status === 'unread' && <span aria-hidden="true" className="absolute -right-1 -top-1 size-2.5 border-2 border-white bg-cx-accent" />}
      </button>
    </div>
  );
}
