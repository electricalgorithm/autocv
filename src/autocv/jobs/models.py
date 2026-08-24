"""Job posting model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class JobPosting(BaseModel):
    """A job posting to tailor a CV against."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    company: str | None = None
    location: str | None = None
    description: str
