'use client';

import * as React from 'react';

/**
 * The box a question is typed in, as the leading chat products set it: one frame, a text area that grows with what is
 * typed (Enter sends, Shift+Enter starts a new line), the thing the question is about as a small chip at the bottom left,
 * and the model and the send button at the bottom right. The frame carries the focus ring, so the field inside stays plain.
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
  /** What the question is about, shown as a chip under the text. */
  readonly context?: React.ReactNode;
  /** What sits beside the send button: the model picker. */
  readonly accessory?: React.ReactNode;
  readonly inputRef?: React.RefObject<HTMLTextAreaElement | null>;
  readonly onKeyDown?: React.KeyboardEventHandler<HTMLTextAreaElement>;
}

/** [ASSUMPTION] about six lines at the text size; beyond that the field scrolls. */
const MAX_FIELD_PX = 132;

export function ChatComposer({ value, onChange, onSubmit, placeholder, ariaLabel, sendLabel, pending, context, accessory, inputRef, onKeyDown }: ChatComposerProps) {
  const own = React.useRef<HTMLTextAreaElement | null>(null);
  const field = inputRef ?? own;
  const disabled = pending || !value.trim();

  React.useLayoutEffect(() => {
    const el = field.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_FIELD_PX)}px`;
  }, [value, field]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="shrink-0 bg-white px-3 pb-3 pt-2"
    >
      <div className="border border-cx-line bg-white shadow-sm transition-[border-color,box-shadow] focus-within:border-cx-accent focus-within:shadow-md">
        <textarea
          ref={field}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            onKeyDown?.(e);
            if (e.defaultPrevented) return;
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              if (!disabled) onSubmit();
            }
          }}
          placeholder={placeholder}
          aria-label={ariaLabel}
          className="block max-h-[132px] min-h-[44px] w-full resize-none rounded-none bg-transparent px-3.5 pb-1 pt-3 text-[13px] leading-5 text-cx-ink outline-none placeholder:text-cx-muted scrollbar-thin"
        />
        <div className="flex items-center gap-2 px-2 pb-2 pt-1">
          <div className="min-w-0 flex-1">{context}</div>
          {accessory}
          <button
            type="submit"
            disabled={disabled}
            aria-label={pending ? 'Working' : sendLabel}
            title={pending ? 'Working…' : `${sendLabel} (Enter)`}
            className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-none bg-cx-ink text-white outline-none transition-colors hover:bg-black focus-visible:ring-2 focus-visible:ring-cx-accent focus-visible:ring-offset-1 disabled:cursor-default disabled:bg-cx-sub disabled:text-cx-faint disabled:hover:bg-cx-sub"
          >
            <span className={`material-symbols-sharp text-lg leading-none ${pending ? 'animate-spin motion-reduce:animate-none' : ''}`} aria-hidden="true">
              {pending ? 'progress_activity' : 'arrow_upward'}
            </span>
          </button>
        </div>
      </div>
    </form>
  );
}
