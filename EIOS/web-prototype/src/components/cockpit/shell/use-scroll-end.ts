import * as React from 'react';

/**
 * Keeps a message list scrolled to its newest entry. It moves only the list's own scrollTop: `scrollIntoView` also scrolls
 * every scrollable ancestor, which shifted the whole page (and the floating chat's clipped frame) when an answer arrived.
 */
export function useScrollToEnd<T extends HTMLElement>(dependency: unknown): React.RefObject<T | null> {
  const listRef = React.useRef<T>(null);
  React.useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    if (typeof list.scrollTo === 'function') list.scrollTo({ top: list.scrollHeight, behavior: 'smooth' });
    else list.scrollTop = list.scrollHeight;
  }, [dependency]);
  return listRef;
}
