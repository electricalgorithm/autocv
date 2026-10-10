"""Exceptions raised while adapting a CV to a job posting."""

from __future__ import annotations


class BackendError(Exception):
    """Raised when an LLM backend fails to produce a response."""


class StructuredOutputError(Exception):
    """Raised when backend text cannot be parsed into the expected model."""


class ResearchError(Exception):
    """Raised when company research fails outright.

    Caught by `CVWorkflow`, which substitutes an empty `CompanyResearch`
    rather than aborting the run — see docs/DESIGN.md.
    """


class AdaptationError(Exception):
    """Raised when the adapter cannot produce a valid CVML document."""
