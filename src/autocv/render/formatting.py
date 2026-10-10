"""Display formatting helpers used by the CV template."""

from __future__ import annotations

from datetime import date, datetime


def format_month(value: str) -> str:
    """Format a CVML ``YYYY-MM`` value, or the literal ``present``.

    Args:
        value: A ``YYYY-MM`` string or the literal ``present``.

    Returns:
        ``Present`` for the literal, otherwise ``Mon YYYY``.
    """
    if value == "present":
        return "Present"
    return datetime.strptime(value, "%Y-%m").strftime("%b %Y")


def format_date(value: date) -> str:
    """Format an ISO date for header display.

    Args:
        value: The date to format.

    Returns:
        ``DD Mon YYYY``, e.g. ``02 Nov 2001``.
    """
    return value.strftime("%d %b %Y")
