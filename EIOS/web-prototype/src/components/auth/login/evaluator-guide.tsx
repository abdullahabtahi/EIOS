import * as React from 'react';

/** The evaluator guide is a Google Slides deck the owner maintains; the link is the only thing this page depends on. */
export const EVALUATOR_GUIDE_URL =
  'https://docs.google.com/presentation/d/1aIBhIUhrtcbZqNa0zcTleYwccEI6fQoT1qa8p0Ob_nU/edit?usp=sharing';

/** The one thing to press for an evaluator: where to start, what to try, and what a good result looks like. */
export function EvaluatorGuide() {
  return (
    <aside className="fde-login-guide" aria-labelledby="evaluator-guide-title" data-testid="evaluator-guide">
      <p className="fde-login-kicker">
        <span aria-hidden="true" className="fde-login-tick" />
        For evaluators
      </p>
      <h2 id="evaluator-guide-title" className="fde-login-guide-title">
        Evaluator guide
      </h2>
      <p className="fde-login-guide-body">
        A suggested path through the workstations: what to try, in what order, and what a good result looks like.
      </p>
      <a
        className="fde-login-cta"
        href={EVALUATOR_GUIDE_URL}
        target="_blank"
        rel="noopener noreferrer"
      >
        Open the evaluator guide <span aria-hidden="true">↗</span>
        <span className="fde-sr"> (opens in a new tab)</span>
      </a>
    </aside>
  );
}
