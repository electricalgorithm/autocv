"""System-level test (A): a master profile that does not fit the job at all.

The scenario a resume tool most needs to survive gracefully: an applicant
with real experience in one field applying to a job in a completely
unrelated one. This asserts two things `autocv adapt` must do with real
component wiring (only the `claude` subprocess is scripted, per
tests/e2e/conftest.py): never crash on the mismatch, and — when a draft
invents something to compensate for the mismatch — have the fact-check and
editorial agents actually catch and remove it, not just claim to.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml
from typer.testing import CliRunner

from autocv.cli.main import app
from tests.e2e.conftest import (
    DRAFT_MARKER,
    EDITORIAL_MARKER,
    FACT_CHECK_MARKER,
    RESEARCH_MARKER,
    RouteResponse,
)

runner = CliRunner()

_MUSIC_PROFILE_MD = """\
## Experience

### Piano Instructor
- Organization: Riverside Music Academy
- Location: Vienna, Austria
- Start: 2015-09
- End: present

Achievements:
- Taught classical piano to over 200 students from beginner to advanced level.
- Prepared 12 students for the Vienna Conservatory entrance exam, 9 of whom were accepted.
- Organized an annual recital for 150+ attendees.

### Orchestral Pianist
- Organization: Vienna Chamber Ensemble
- Location: Vienna, Austria
- Start: 2012-01
- End: 2015-08

Achievements:
- Performed as principal pianist in over 60 chamber concerts.
- Recorded two albums of Romantic-era piano repertoire.

## Education

### Master of Music, Piano Performance
- Institution: University of Music and Performing Arts Vienna
- Location: Vienna, Austria
- Start: 2009-09
- End: 2011-06

## Skills

- Classical piano performance
- Music theory and composition
- Chamber music direction
- Private instruction
"""

_JOB_TEXT = """\
Senior Kubernetes Platform Engineer

We are looking for a Senior Kubernetes Platform Engineer to run our
container orchestration platform at scale, own our CI/CD pipelines, and
mentor other engineers on cloud-native best practices.
"""

_BASE_CV = {
    "person": {"name": "Elena Roth", "headline": "Classical Pianist & Instructor"},
    "contact": {
        "email": "elena@example.com",
        "phone": "+43 1 2345678",
        "location": "Vienna, Austria",
    },
    "summary": "Original summary.",
}

_DRAFT_YAML_WITH_FABRICATION = """
person:
  name: Placeholder
  headline: Placeholder
contact:
  email: placeholder@example.com
  phone: "+00 000 0000"
  location: Nowhere
summary: >-
  Experienced platform engineer skilled in Kubernetes, Docker, and
  cloud-native infrastructure.
experience:
  - title: Piano Instructor
    organization: Riverside Music Academy
    location: Vienna, Austria
    start: "2015-09"
    end: present
    summary: >-
      Taught classical piano and also managed Kubernetes clusters for
      the academy's IT systems.
    keywords:
      - Kubernetes
      - Classical Piano
"""

_FACT_CHECK_YAML_FLAGS_KUBERNETES = """
issues:
  - claim: Managed Kubernetes clusters for the academy's IT systems
    explanation: >-
      Not present anywhere in the master profile, which only covers
      piano performance and instruction.
  - claim: Skilled in Kubernetes, Docker, and cloud-native infrastructure
    explanation: No technology or software experience appears in the master profile.
"""

_EDITORIAL_YAML_CORRECTED = """
person:
  name: Placeholder
  headline: Placeholder
contact:
  email: placeholder@example.com
  phone: "+00 000 0000"
  location: Nowhere
summary: >-
  Accomplished classical pianist and instructor with a decade of
  experience in performance and music education.
experience:
  - title: Piano Instructor
    organization: Riverside Music Academy
    location: Vienna, Austria
    start: "2015-09"
    end: present
    summary: >-
      Taught classical piano to over 200 students and prepared 12
      for the Vienna Conservatory entrance exam.
    keywords:
      - Classical Piano
      - Music Education
"""

_RESEARCH_YAML = "summary: Builds container orchestration platforms for enterprise customers.\n"


class TestMismatchedProfile:
    """(A) `autocv adapt` with a profile unrelated to the job."""

    def test_never_crashes_and_drops_the_fabricated_claim(
        self, tmp_path: Path, mock_claude: Callable[[dict[str, RouteResponse]], None]
    ) -> None:
        def fact_check_response(system_prompt: str, user_prompt: str) -> str:
            assert "Kubernetes" in user_prompt, "draft's fabrication never reached the fact-checker"
            return _FACT_CHECK_YAML_FLAGS_KUBERNETES

        def editorial_response(system_prompt: str, user_prompt: str) -> str:
            assert "Kubernetes" in user_prompt, "fact-check issues never reached the editor"
            return _EDITORIAL_YAML_CORRECTED

        mock_claude(
            {
                DRAFT_MARKER: _DRAFT_YAML_WITH_FABRICATION,
                RESEARCH_MARKER: _RESEARCH_YAML,
                FACT_CHECK_MARKER: fact_check_response,
                EDITORIAL_MARKER: editorial_response,
            }
        )

        profile_path = tmp_path / "profile.md"
        profile_path.write_text(_MUSIC_PROFILE_MD, encoding="utf-8")
        base_path = tmp_path / "base.cvml.yaml"
        base_path.write_text(yaml.safe_dump(_BASE_CV), encoding="utf-8")
        job_path = tmp_path / "job.txt"
        job_path.write_text(_JOB_TEXT, encoding="utf-8")
        output_path = tmp_path / "tailored.cvml.yaml"

        result = runner.invoke(
            app,
            [
                "adapt",
                "--profile",
                str(profile_path),
                "--base",
                str(base_path),
                "--output",
                str(output_path),
                "--job-text-file",
                str(job_path),
            ],
        )

        assert result.exit_code == 0, result.output
        written = output_path.read_text(encoding="utf-8")
        assert "Kubernetes" not in written

        data = yaml.safe_load(written)
        # Identity is enforced from base, never trusted from the (placeholder) draft.
        assert data["person"]["name"] == "Elena Roth"
        assert data["contact"]["email"] == "elena@example.com"
        assert "music" in data["summary"].lower()
