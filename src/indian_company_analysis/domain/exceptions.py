"""Domain-specific failures exposed by deterministic workflows."""


class AnalysisError(Exception):
    """Base class for controlled analysis failures."""


class ProvenanceError(AnalysisError):
    """Raised when an input cannot be traced to declared evidence."""


class MissingMetricError(AnalysisError):
    """Raised when a workflow's required source metric is unavailable."""
