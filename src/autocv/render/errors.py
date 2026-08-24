"""Exceptions raised while rendering a CV."""

from __future__ import annotations


class RenderError(Exception):
    """Raised when a CV cannot be rendered to a document."""
