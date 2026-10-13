import * as React from 'react';

export interface PanelHeaderProps {
  readonly title: string;
  readonly icon?: string;
  readonly iconClassName?: string;
  readonly level?: 3 | 4;
  readonly actions?: React.ReactNode;
}

/**
 * Standard panel header: Inter semibold title (hierarchy), actions on the right,
 * wraps instead of clipping. Mono is reserved for data, IDs and metrics.
 */
export function PanelHeader({ title, icon, iconClassName = 'text-cx-accent', level = 3, actions }: PanelHeaderProps) {
  const Heading = level === 3 ? 'h3' : 'h4';
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 border-b border-cx-line-soft pb-2.5">
      <div className="flex items-center gap-2 min-w-0">
        {icon && <span aria-hidden="true" className={`material-symbols-sharp text-base ${iconClassName}`}>{icon}</span>}
        <Heading className="text-title font-sans font-semibold tracking-normal text-cx-ink">{title}</Heading>
      </div>
      {actions && <div className="flex items-center gap-1.5 flex-wrap">{actions}</div>}
    </div>
  );
}
