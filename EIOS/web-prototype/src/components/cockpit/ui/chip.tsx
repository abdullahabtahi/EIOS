import * as React from 'react';

export type ChipTone = 'neutral' | 'info' | 'ok' | 'warn' | 'bad' | 'accent';

const TONE: Record<ChipTone, string> = {
  neutral: 'bg-cx-sub text-cx-muted border-cx-line',
  info: 'bg-cx-info-bg text-cx-accent border-cx-info-line',
  ok: 'bg-cx-ok-bg text-cx-ok border-cx-ok-line',
  warn: 'bg-cx-warn-bg text-cx-warn border-cx-warn-line',
  bad: 'bg-cx-bad-bg text-cx-bad border-cx-bad-line',
  accent: 'bg-cx-accent text-white border-cx-accent',
};

export interface ChipProps extends React.ComponentProps<'span'> {
  readonly tone?: ChipTone;
}

/** Small status / count / tag label. Single text node, token colours only, 11px floor. */
export function Chip({ tone = 'neutral', className = '', children, ...rest }: ChipProps) {
  return (
    <span
      data-tone={tone}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 border text-label font-mono font-bold uppercase whitespace-nowrap ${TONE[tone]} ${className}`}
      {...rest}
    >
      {children}
    </span>
  );
}
