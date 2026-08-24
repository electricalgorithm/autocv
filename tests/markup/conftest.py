"""Shared fixtures for autocv.markup tests."""

from __future__ import annotations

from typing import Any

import pytest


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
def full_cv_data(minimal_cv_data: dict[str, Any]) -> dict[str, Any]:
    """Minimal data set plus every optional/list section populated."""
    data = dict(minimal_cv_data)
    data["experience"] = [
        {
            "title": "Software Engineer",
            "organization": "Example Corp",
            "location": "London, UK",
            "start": "2023-01",
            "end": "present",
            "summary": "Built things.",
            "keywords": ["Python"],
        }
    ]
    data["education"] = [
        {
            "degree": "BEng.",
            "institution": "Example University",
            "location": "London, UK",
            "start": "2018-09",
            "end": "2022-07",
            "detail": "First-class honours.",
        }
    ]
    data["skills"] = ["Python", "Leadership"]
    data["certifications"] = ["Certified Kubernetes Administrator"]
    data["publications"] = [{"title": "A Paper", "venue": "A Journal", "date": "2024-01"}]
    data["projects"] = [{"title": "A Project", "categories": ["Web"], "stack": ["Python"]}]
    data["references"] = [
        {
            "name": "Bob",
            "title": "Manager",
            "organization": "Example Corp",
            "email": "bob@example.com",
        }
    ]
    data["languages"] = [{"name": "English", "level": "Native"}]
    return data
