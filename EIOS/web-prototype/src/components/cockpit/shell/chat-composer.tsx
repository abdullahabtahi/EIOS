'use client';

import * as React from 'react';

/**
 * The box a question is typed in: one frame holding the text field, and under it the model picker and a small send
 * button (Enter sends too). The frame carries the focus ring, so the field inside stays plain.
 */
export interface ChatComposerProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
  readonly placeholder: string;
  readonly ariaLabel: string;
  /** Name of the send button for assistive tech; the visible control is an icon. */
  readonly sendLabel: string;
  readonly pending: boolean;
  /** What sits beside the send button: the model picker. */
  readonly accessory?: React.ReactNode;
  readonly inputRef?: React.RefObject<HTMLInputElement | null>;
  readonly onKeyDown?: React.KeyboardEventHandler<HTMLInputElement>;
}

export function ChatComposer({ value, onChange, onSubmit, placeholder, ariaLabel, sendLabel, pending, accessory, inputRef, onKeyDown }: ChatComposerProps) {
  const disabled = pending || !value.trim();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="shrink-0 border-t border-cx-line bg-white p-3"
    >
      <div className="border border-cx-line bg-white transition-colors focus-within:border-cx-accent focus-within:ring-1 focus-within:ring-cx-accent">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          aria-label={ariaLabel}
          className="block w-full rounded-none bg-transparent px-3 pb-1 pt-2.5 text-xs text-cx-ink outline-none placeholder:text-cx-muted"
        />
        <div className="flex items-center justify-end gap-1 px-1.5 pb-1.5">
          {accessory}
          <button
            type="submit"
            disabled={disabled}
            aria-label={pending ? 'Working' : sendLabel}
            title={pending ? 'Working…' : `${sendLabel} (Enter)`}
            className="flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-none bg-cx-ink text-white outline-none hover:bg-black focus-visible:ring-2 focus-visible:ring-cx-accent focus-visible:ring-offset-1 disabled:cursor-default disabled:bg-cx-sub-2 disabled:text-cx-faint"
          >
            <span className={`material-symbols-sharp text-base leading-none ${pending ? 'animate-spin motion-reduce:animate-none' : ''}`} aria-hidden="true">
              {pending ? 'progress_activity' : 'keyboard_return'}
            </span>
          </button>
        </div>
      </div>
    </form>
  );
}
