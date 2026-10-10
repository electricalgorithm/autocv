"""System-level test (C): rendering with a non-default CV template.

Confirms the template system (docs/DESIGN.md, `--template`) isn't only
exercised against the static example CV — an `autocv adapt` output must
render under every available template too, and an unknown template name
must fail the same way for adapted output as for any other CVML file.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from autocv.cli.main import app
from autocv.render.html_renderer import list_templates
from tests.e2e.conftest import (
    DRAFT_MARKER,
    EDITORIAL_MARKER,
    FACT_CHECK_MARKER,
    RESEARCH_MARKER,
    RouteResponse,
)

runner = CliRunner()

_JOB_TEXT = "Software Engineer\n\nWe build web applications."

_BASE_CV = {
    "person": {"name": "Sam Rivera", "headline": "Software Engineer"},
    "contact": {"email": "sam@example.com", "phone": "+1 555 0142", "location": "Remote"},
    "summary": "Original summary.",
}

_PROFILE_MD = """\
## Experience

### Software Engineer
- Organization: Example Corp
- Location: Remote
- Start: 2020-01
- End: present

Achievements:
- Built and shipped several web applications.
"""

_TAILORED_CVML = """
person:
  name: Placeholder
  headline: Placeholder
contact:
  email: placeholder@example.com
  phone: "+00 000 0000"
  location: Nowhere
summary: Software engineer with experience building web applications.
"""

_NO_ISSUES_YAML = "issues: []\n"

_RESEARCH_YAML = "summary: Builds web applications.\n"


@pytest.fixture
def tailored_cvml_path(
    tmp_path: Path, mock_claude: Callable[[dict[str, RouteResponse]], None]
) -> Path:
    """Produce a real `autocv adapt` output to render under each template."""
    mock_claude(
        {
            DRAFT_MARKER: _TAILORED_CVML,
            RESEARCH_MARKER: _RESEARCH_YAML,
            FACT_CHECK_MARKER: _NO_ISSUES_YAML,
            EDITORIAL_MARKER: _TAILORED_CVML,
        }
    )

    profile_path = tmp_path / "profile.md"
    profile_path.write_text(_PROFILE_MD, encoding="utf-8")
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
    return output_path


class TestAlternateTemplate:
    """(C) rendering adapted output under every available template."""

    def test_every_available_template_renders_the_adapted_cv(
        self, tailored_cvml_path: Path
    ) -> None:
        for template in list_templates():
            pdf_path = tailored_cvml_path.with_name(f"{template}.pdf")

            result = runner.invoke(
                app,
                ["render", str(tailored_cvml_path), "-o", str(pdf_path), "--template", template],
            )

            assert result.exit_code == 0, f"{template}: {result.output}"
            assert pdf_path.read_bytes().startswith(b"%PDF")

    def test_at_least_two_templates_are_available(self) -> None:
        assert len(list_templates()) >= 2

    def test_unknown_template_fails_on_adapted_output_too(self, tailored_cvml_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "render",
                str(tailored_cvml_path),
                "-o",
                str(tailored_cvml_path.with_name("out.pdf")),
                "--template",
                "does-not-exist",
            ],
        )
        assert result.exit_code == 1
