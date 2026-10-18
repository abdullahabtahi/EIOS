'use client';

import * as React from 'react';
import { Icon } from '@/components/ui/icon';

/**
 * The box a question is typed in, as the leading chat products set it: one frame with a text area that grows with what is
 * typed (Enter sends, Shift+Enter starts a new line), and a small enter icon at its end; under the frame, on one quiet line, what the question is about (left) and the model (right).
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
  /** What sits under the frame at the right: the model picker. */
  readonly accessory?: React.ReactNode;
  /** What sits inside the frame, before the send icon: the model picker where the panel has no line to spare under it. */
  readonly inlineAccessory?: React.ReactNode;
  readonly inputRef?: React.RefObject<HTMLTextAreaElement | null>;
  readonly onKeyDown?: React.KeyboardEventHandler<HTMLTextAreaElement>;
}

/** [ASSUMPTION] about six lines at the text size; beyond that the field scrolls. */
const MAX_FIELD_PX = 132;

export function ChatComposer({ value, onChange, onSubmit, placeholder, ariaLabel, sendLabel, pending, context, accessory, inlineAccessory, inputRef, onKeyDown }: ChatComposerProps) {
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
      <div className="flex items-end border border-cx-line bg-white shadow-sm transition-[border-color,box-shadow] focus-within:border-cx-accent focus-within:shadow-md">
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
          className="block max-h-[132px] min-h-[44px] min-w-0 flex-1 resize-none rounded-none bg-transparent px-3.5 py-3 text-[13px] leading-5 text-cx-ink outline-none placeholder:text-cx-muted scrollbar-thin"
        />
        {inlineAccessory && <div className="mb-1.5 flex shrink-0 items-center">{inlineAccessory}</div>}
        <button
          type="submit"
          disabled={disabled}
          aria-label={pending ? 'Working' : sendLabel}
          title={pending ? 'Working…' : `${sendLabel} (Enter)`}
          className="my-1.5 mr-1.5 flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-none text-cx-ink outline-none transition-colors hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-cx-accent disabled:cursor-default disabled:text-cx-faint disabled:hover:bg-transparent"
        >
          <Icon icon={pending ? 'progress_activity' : 'keyboard_return'} size="sm" className={pending ? 'animate-spin motion-reduce:animate-none' : ''} />
        </button>
      </div>
      {(context || accessory) && (
        <div className="mt-1.5 flex min-h-6 items-center gap-2 px-0.5">
          <div className="min-w-0 flex-1">{context}</div>
          {accessory}
        </div>
      )}
    </form>
  );
}
