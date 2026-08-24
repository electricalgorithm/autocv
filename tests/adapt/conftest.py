"""Shared fixtures for autocv.adapt tests."""

from __future__ import annotations

import pytest

from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile


@pytest.fixture
def base_cv() -> CV:
    """A minimal base CV, used for its person/contact/references/languages."""
    return CV.model_validate(
        {
            "person": {"name": "Ada Lovelace", "headline": "Software Engineer"},
            "contact": {
                "email": "ada@example.com",
                "phone": "+1 555 0100",
                "location": "London, UK",
            },
            "summary": "Original summary.",
            "references": [
                {
                    "name": "Bob",
                    "title": "Manager",
                    "organization": "Example Corp",
                    "email": "bob@example.com",
                }
            ],
            "languages": [{"name": "English", "level": "Native"}],
        }
    )


@pytest.fixture
def profile() -> MasterProfile:
    """A small master profile with one experience entry."""
    return MasterProfile.model_validate(
        {
            "experience": [
                {
                    "title": "Software Engineer",
                    "organization": "Example Corp",
                    "location": "London, UK",
                    "start": "2023-01",
                    "end": "present",
                    "achievements": ["Shipped the analytical engine v2."],
                }
            ]
        }
    )


@pytest.fixture
def job() -> JobPosting:
    """A small job posting."""
    return JobPosting(
        title="Senior Software Engineer",
        company="Example Corp",
        description="We need someone who has shipped complex systems.",
    )
