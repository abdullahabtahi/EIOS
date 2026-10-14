"""Text that originated outside the system is bounded and flagged (spec 023 FR-008)."""

MAX_EXCERPT_CHARS = 280  # [ASSUMPTION] long enough to read a message, too short to carry a payload


def bound_excerpt(text: str, limit: int = MAX_EXCERPT_CHARS) -> str:
    """The text cut to `limit` characters on a whitespace boundary, with an ellipsis if cut."""
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    cut = clean[: limit - 1].rsplit(" ", 1)[0] or clean[: limit - 1]
    return f"{cut}…"
