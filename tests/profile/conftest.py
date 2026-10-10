"""Shared fixtures for autocv.profile tests."""

from __future__ import annotations

import pytest

_FULL_PROFILE_MD = """\
## Experience

### Software Engineer
- Organization: Example Corp
- Organization URL: https://example.com
- Location: Berlin, Germany
- Start: 2023-01
- End: present
- Keywords: Python, Kubernetes

Achievements:
- Cut deploy time from 40 minutes to 6 by moving CI to buildkite.
- Led the migration of the billing service to Kubernetes.

### Junior Engineer
- Organization: Old Corp
- Location: Berlin, Germany
- Start: 2020-01
- End: 2022-12

Achievements:
- Wrote the first version of the billing service.

## Education

### BEng. Computer Engineering
- Institution: Example University
- Institution URL: https://example.edu
- Location: Berlin, Germany
- Start: 2018-09
- End: 2022-07
- Detail: First-class honours.

## Skills

- Python
- Kubernetes
- Team leadership

## Certifications

- Certified Kubernetes Administrator
- AWS Certified Solutions Architect

## Publications

### Paper Title
- Venue: Conference Name
- Date: 2024-01
- URL: https://example.com/paper

## Projects

### Project Name
- Categories: Web, Embedded
- Stack: Python, MQTT
- URL: https://github.com/example
- Detail: 100+ stars on GitHub

Achievements:
- Built a broker-enforced schema layer for MQTT topics.
"""


@pytest.fixture
def full_profile_md() -> str:
    """A master profile document exercising every section and optional field."""
    return _FULL_PROFILE_MD
