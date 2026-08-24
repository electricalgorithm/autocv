"""Shared ``YYYY-MM`` date validation for CVML and master profile schemas."""

from __future__ import annotations

import re

_YEAR_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def require_year_month(value: str) -> str:
    """Validate a ``YYYY-MM`` string.

    Args:
        value: Candidate date string.

    Returns:
        The unchanged value if valid.

    Raises:
        ValueError: If ``value`` is not ``YYYY-MM``.
    """
    if not _YEAR_MONTH_RE.match(value):
        raise ValueError(f"expected 'YYYY-MM', got {value!r}")
    return value


def require_year_month_or_present(value: str) -> str:
    """Validate a ``YYYY-MM`` string or the literal ``present``.

    Args:
        value: Candidate end-date string.

    Returns:
        The unchanged value if valid.

    Raises:
        ValueError: If ``value`` is neither ``YYYY-MM`` nor ``present``.
    """
    if value == "present":
        return value
    return require_year_month(value)
