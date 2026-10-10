"""Exceptions raised while loading CVML documents."""

from __future__ import annotations


class CVSourceError(Exception):
    """Raised when a CVML file cannot be read or parsed as YAML."""


class CVValidationError(Exception):
    """Raised when parsed CVML data does not satisfy the CV schema."""
