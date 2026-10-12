"""Domain exceptions for Executive Synthesis Engine (F05)."""


class SynthesisError(Exception):
    """Base exception for all synthesis engine errors."""

    pass


class CausalCycleError(SynthesisError):
    """Raised when a causal graph introduces a directed cycle."""

    pass


class CausalGateViolationError(SynthesisError):
    """Raised when an unverified or failing causal edge is asserted causally."""

    pass


class SingularMatrixError(SynthesisError):
    """Raised when structural equation fitting encounters a degenerate design matrix."""

    pass


class AttributionSumError(SynthesisError):
    """Raised when driver attribution percentages fail to sum to 100.0%."""

    pass


class ExtrapolationWarning(UserWarning):
    """Emitted when scenario shock inputs exceed historical domain bounds."""

    pass
