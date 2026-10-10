"""System-level test (B): a large master profile against a near-empty base CV.

Stresses two things at once: the Markdown profile parser at real scale (a
few dozen entries, not the handful used in unit tests), and the opposite
extreme of task (A)'s content mismatch — an applicant who has supplied
almost nothing beyond a name and contact details. `autocv adapt` and
`autocv render` must both still produce valid output: no crash from a
large prompt, and no crash from missing optional identity fields (photo,
citizenships, references, languages).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml
from typer.testing import CliRunner

from autocv.cli.main import app
from autocv.profile.parser import load_profile
from tests.e2e.conftest import (
    DRAFT_MARKER,
    EDITORIAL_MARKER,
    FACT_CHECK_MARKER,
    RESEARCH_MARKER,
    RouteResponse,
)

runner = CliRunner()

_EXPERIENCE_COUNT = 14
_PROJECT_COUNT = 6


def _build_large_profile_md() -> str:
    """Build a master profile with many experience entries and projects.

    Returns:
        The profile document text.
    """
    lines = ["## Experience", ""]
    for i in range(_EXPERIENCE_COUNT):
        year = 2010 + i
        lines += [
            f"### Software Engineer, Team {i}",
            f"- Organization: Company {i}",
            "- Location: Remote",
            f"- Start: {year}-01",
            f"- End: {year}-12",
            "- Keywords: Python, Distributed Systems",
            "",
            "Achievements:",
            f"- Shipped feature {i} used by thousands of customers.",
            f"- Reduced latency of service {i} by {10 + i}%.",
            "",
        ]
    lines += ["## Education", ""]
    lines += [
        "### BSc. Computer Science",
        "- Institution: State University",
        "- Location: Remote",
        "- Start: 2006-09",
        "- End: 2010-06",
        "",
    ]
    lines += ["## Skills", ""]
    lines += [f"- Skill {i}" for i in range(20)]
    lines += [""]
    lines += ["## Projects", ""]
    for i in range(_PROJECT_COUNT):
        lines += [
            f"### Project {i}",
            "- Categories: Open Source",
            "- Stack: Python",
            "",
            "Achievements:",
            f"- Built project {i} from scratch.",
            "",
        ]
    return "\n".join(lines)


_JOB_TEXT = "Software Engineer\n\nWe build distributed systems at scale."

_MINIMAL_BASE_CV = {
    "person": {"name": "Jordan Lee", "headline": "Software Engineer"},
    "contact": {"email": "jordan@example.com", "phone": "+1 555 0199", "location": "Remote"},
    "summary": "Original summary.",
}

_DRAFT_YAML = """
person:
  name: Placeholder
  headline: Placeholder
contact:
  email: placeholder@example.com
  phone: "+00 000 0000"
  location: Nowhere
summary: Software engineer with a decade of experience across many teams.
"""

_NO_ISSUES_YAML = "issues: []\n"

_RESEARCH_YAML = "summary: Builds distributed systems.\n"

_EDITORIAL_YAML = """
person:
  name: Placeholder
  headline: Placeholder
contact:
  email: placeholder@example.com
  phone: "+00 000 0000"
  location: Nowhere
summary: Software engineer with a decade of experience shipping distributed systems.
"""


class TestLargeProfileParsesAtScale:
    """(B) the Markdown parser handles a profile with many entries."""

    def test_parses_every_entry(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.md"
        path.write_text(_build_large_profile_md(), encoding="utf-8")

        profile = load_profile(path)

        assert len(profile.experience) == _EXPERIENCE_COUNT
        assert len(profile.projects) == _PROJECT_COUNT
        assert len(profile.skills) == 20
        assert (
            profile.experience[0].achievements[0]
            == "Shipped feature 0 used by thousands of customers."
        )


class TestMinimalBaseIdentity:
    """(B) `autocv adapt`/`render` with a base CV that has almost nothing."""

    def test_adapt_succeeds_with_large_profile_and_minimal_base(
        self, tmp_path: Path, mock_claude: Callable[[dict[str, RouteResponse]], None]
    ) -> None:
        mock_claude(
            {
                DRAFT_MARKER: _DRAFT_YAML,
                RESEARCH_MARKER: _RESEARCH_YAML,
                FACT_CHECK_MARKER: _NO_ISSUES_YAML,
                EDITORIAL_MARKER: _EDITORIAL_YAML,
            }
        )

        profile_path = tmp_path / "profile.md"
        profile_path.write_text(_build_large_profile_md(), encoding="utf-8")
        base_path = tmp_path / "base.cvml.yaml"
        base_path.write_text(yaml.safe_dump(_MINIMAL_BASE_CV), encoding="utf-8")
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
        data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
        assert data["person"]["name"] == "Jordan Lee"
        assert data["person"].get("photo") is None
        assert data.get("references", []) == []
        assert data.get("languages", []) == []

    def test_render_succeeds_with_no_photo_or_optional_fields(
        self, tmp_path: Path, mock_claude: Callable[[dict[str, RouteResponse]], None]
    ) -> None:
        mock_claude(
            {
                DRAFT_MARKER: _DRAFT_YAML,
                RESEARCH_MARKER: _RESEARCH_YAML,
                FACT_CHECK_MARKER: _NO_ISSUES_YAML,
                EDITORIAL_MARKER: _EDITORIAL_YAML,
            }
        )

        profile_path = tmp_path / "profile.md"
        profile_path.write_text(_build_large_profile_md(), encoding="utf-8")
        base_path = tmp_path / "base.cvml.yaml"
        base_path.write_text(yaml.safe_dump(_MINIMAL_BASE_CV), encoding="utf-8")
        job_path = tmp_path / "job.txt"
        job_path.write_text(_JOB_TEXT, encoding="utf-8")
        tailored_path = tmp_path / "tailored.cvml.yaml"

        runner.invoke(
            app,
            [
                "adapt",
                "--profile",
                str(profile_path),
                "--base",
                str(base_path),
                "--output",
                str(tailored_path),
                "--job-text-file",
                str(job_path),
            ],
        )

        pdf_path = tmp_path / "tailored.pdf"
        result = runner.invoke(app, ["render", str(tailored_path), "-o", str(pdf_path)])

        assert result.exit_code == 0, result.output
        assert pdf_path.read_bytes().startswith(b"%PDF")
