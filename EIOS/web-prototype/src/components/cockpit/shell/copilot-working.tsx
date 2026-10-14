'use client';

/** Shown while a turn is pending. A live turn takes 5 to 30 s, so it counts the seconds and promises nothing else. */

import * as React from 'react';

export function CopilotWorking() {
  const [seconds, setSeconds] = React.useState(0);
  React.useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div
      role="status"
      aria-live="polite"
      className="p-4 bg-slate-50 border border-slate-200 flex items-center gap-3 text-xs font-mono text-slate-600"
    >
      <span className="material-symbols-sharp text-blue-600 animate-spin text-base" aria-hidden="true">
        progress_activity
      </span>
      <div>
        <div>Working… {seconds} s</div>
        <div className="text-label text-slate-500">
          Reading governed data and checking every figure. An answer can take up to 30 seconds.
        </div>
      </div>
    </div>
  );
}
