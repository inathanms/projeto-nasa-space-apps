"""Failures classified by their effect on a sequence request."""


class ArchiveUnavailable(RuntimeError):
    """IRSA did not provide a usable response."""


class SearchTimeout(RuntimeError):
    """The request exhausted its time budget."""


class InsufficientCoverage(RuntimeError):
    """No comparable pair passed the observation and pixel checks."""
