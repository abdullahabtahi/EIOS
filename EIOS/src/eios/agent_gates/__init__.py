"""Runtime-neutral quality gates for the conversational assistant (spec 022).

`core/` holds the deterministic judges. It is standard-library only so the same files run inside the
Google eval CLI (which executes metric code in its own Python 3.12 process) and in our CI.
"""
