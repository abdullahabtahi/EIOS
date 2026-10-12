"""Open-decision check: fails when code or config assumes the outcome of a decision still open.

Run with ``python -m tools.open_decision_check [--repo-root DIR]``; exits 0 pass, 1 findings,
2 tool or configuration error. Every decision lives in ``config/open_decisions.yaml``; the tool
itself names no decision.
"""
