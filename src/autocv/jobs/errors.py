"""Exceptions raised while fetching job postings."""

from __future__ import annotations


class JobFetchError(Exception):
    """Raised when a job posting cannot be fetched or parsed."""
