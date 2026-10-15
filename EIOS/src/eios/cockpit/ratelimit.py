"""Protect the Gen AI spend: cap how often each operator, and the whole instance, can ask the copilot a question.

Built on the `limits` library (moving windows, the engine behind Flask-Limiter and SlowAPI) rather than hand-rolled
counters. Only the copilot route is limited: it is the one path that calls the model, and the reviewer accounts are shared
and public. Counters live in this instance's memory; with a few instances the real ceiling is that many times the figure,
and `max_instances` plus the budget alert are the outer bound. A refusal is a plain `429` with `Retry-After`.

Limits are `limits` rate strings in the environment so an owner can tune them without a build:
`EIOS_RATE_COPILOT_PER_USER` (default "20/minute;600/day"), `EIOS_RATE_COPILOT_GLOBAL` ("3000/day"), and
`EIOS_RATE_LIMITS=off` to disable (tests, local work). `slowapi` was considered and not used: it wraps the same `limits`
engine but needs a request parameter on the route and a key function that cannot see the verified operator without a hop
through request state, so here it would add about as much glue as it removes. Counters in memory are the thin choice; a
shared store (`limits` supports Redis, e.g. Memorystore) is the path if instances multiply.
"""

from __future__ import annotations

import logging
import math
import os
import time
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from limits import RateLimitItem, parse_many
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from eios.cockpit.auth import Operator, current_operator

_LOG = logging.getLogger("eios.ratelimit")
_OFF = {"off", "0", "false", "no"}
_STORAGE = MemoryStorage()
LIMITER = MovingWindowRateLimiter(_STORAGE)


def reset() -> None:
    """Forget every count (tests)."""
    _STORAGE.reset()


PER_USER_DEFAULT = "20/minute;600/day"  # [ASSUMPTION] a few judges sharing three accounts: firm on spend, loose for a demo
GLOBAL_DEFAULT = "3000/day"  # [ASSUMPTION] the whole instance, whoever asks


@lru_cache(maxsize=16)
def _items(spec: str, fallback: str) -> tuple[RateLimitItem, ...]:
    """Parse a limit setting once. A typo is logged loudly and replaced by the default: a bad setting must never turn
    into an error on every question, and it must never silently remove the limit either."""
    try:
        return tuple(parse_many(spec))
    except ValueError:
        _LOG.error("invalid rate limit %r; using the default %r", spec, fallback)
        return tuple(parse_many(fallback))


async def limit_copilot(operator: Operator | None = Depends(current_operator)) -> None:
    if os.environ.get("EIOS_RATE_LIMITS", "on").strip().lower() in _OFF:
        return
    who = operator.uid if operator else "anonymous"  # dev with auth off has one anonymous caller
    per_user = _items(
        os.environ.get("EIOS_RATE_COPILOT_PER_USER", PER_USER_DEFAULT), PER_USER_DEFAULT
    )
    overall = _items(os.environ.get("EIOS_RATE_COPILOT_GLOBAL", GLOBAL_DEFAULT), GLOBAL_DEFAULT)
    checks = [(item, "copilot", who) for item in per_user] + [
        (item, "copilot", "*") for item in overall
    ]
    if all(LIMITER.test(*c) for c in checks):
        for c in checks:
            LIMITER.hit(*c)  # all-or-nothing: a refused request is counted nowhere
        return
    wait = max(
        max(1, math.ceil(LIMITER.get_window_stats(*c).reset_time - time.time()))
        for c in checks
        if not LIMITER.test(*c)
    )
    _LOG.warning("copilot rate limit reached for %s; retry in %ss", who, wait)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Too many questions in a short time. Try again in {wait} s.",
        headers={"Retry-After": str(wait)},
    )
