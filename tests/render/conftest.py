"""Shared fixtures for autocv.render tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from autocv.markup.models import CV


@pytest.fixture
def minimal_cv_data() -> dict[str, Any]:
    """Smallest data set that satisfies the CV schema."""
    return {
        "person": {"name": "Ada Lovelace", "headline": "Software Engineer"},
        "contact": {
            "email": "ada@example.com",
            "phone": "+1 555 0100",
            "location": "London, UK",
        },
        "summary": "A pioneering software engineer.",
    }


@pytest.fixture
def cv_data() -> dict[str, Any]:
    """A CV data set covering every section, without a photo."""
    return {
        "person": {"name": "Ada Lovelace", "headline": "Software Engineer"},
        "contact": {
            "email": "ada@example.com",
            "phone": "+1 555 0100",
            "location": "London, UK",
            "linkedin": "adalovelace",
            "github": "adalovelace",
            "website": "ada.example.com",
            "scholar": "https://scholar.google.com/citations?user=adalovelace",
        },
        "summary": "A pioneering software engineer.",
        "experience": [
            {
                "title": "Software Engineer",
                "organization": "Example Corp",
                "organization_url": "https://example.com",
                "location": "London, UK",
                "start": "2023-01",
                "end": "present",
                "summary": "Built things.",
                "keywords": ["Python", "Analytical Engines"],
            }
        ],
        "education": [
            {
                "degree": "BEng.",
                "institution": "Example University",
                "location": "London, UK",
                "start": "2018-09",
                "end": "2022-07",
                "detail": "First-class honours.",
            }
        ],
        "skills": ["Python", "Leadership"],
        "certifications": ["Certified Kubernetes Administrator"],
        "publications": [{"title": "A Paper", "venue": "A Journal", "date": "2024-01"}],
        "projects": [{"title": "A Project", "categories": ["Web"], "stack": ["Python"]}],
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


@pytest.fixture
def cv(cv_data: dict[str, Any]) -> CV:
    """A validated CV covering every section, without a photo."""
    return CV.model_validate(cv_data)


@pytest.fixture
def assets_dir(tmp_path: Path) -> Path:
    """An empty directory to resolve (absent) relative assets against."""
    return tmp_path
