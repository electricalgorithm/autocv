"""Exceptions raised while loading master profile documents."""

from __future__ import annotations


class ProfileSourceError(Exception):
    """Raised when a master profile file cannot be read or parsed."""


class ProfileValidationError(Exception):
    """Raised when parsed profile data does not satisfy the profile schema."""
