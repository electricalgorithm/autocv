"""Unit tests for autocv.cli.main."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from autocv.cli.main import app

runner = CliRunner()

_MINIMAL_CV = {
    "person": {"name": "Ada Lovelace", "headline": "Software Engineer"},
    "contact": {"email": "ada@example.com", "phone": "+1 555 0100", "location": "London, UK"},
    "summary": "A pioneering software engineer.",
}

_MINIMAL_PROFILE_MD = """\
## Experience

### Software Engineer
- Organization: Example Corp
- Location: London, UK
- Start: 2023-01
- End: present

Achievements:
- Shipped the analytical engine v2.
"""

_TAILORED_CVML = """\
person:
  name: Ada Lovelace
  headline: Software Engineer
contact:
  email: ada@example.com
  phone: "+1 555 0100"
  location: London, UK
summary: Tailored summary.
"""

_RESEARCH_YAML = "summary: Builds developer tools.\n"

_FACT_CHECK_YAML = "issues: []\n"


def _completed(
    stdout: str = _TAILORED_CVML, returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def _mock_agentic_subprocess(mocker: MockerFixture) -> None:
    """Mock every `claude` subprocess call, routing by which agent is asking.

    The adapt command now runs the full draft/research/fact-check/editorial
    workflow, each a separate ``claude -p`` call with a different schema in
    its system prompt; a single canned response can't satisfy all of them.
    """

    def handler(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        system_prompt = command[command.index("--system-prompt") + 1]
        if '"products"' in system_prompt:
            stdout = _RESEARCH_YAML
        elif '"issues"' in system_prompt:
            stdout = _FACT_CHECK_YAML
        else:
            stdout = _TAILORED_CVML
        return _completed(stdout=stdout)

    mocker.patch("autocv.adapt.backends.subprocess.run", side_effect=handler)


class TestRenderCommand:
    """`autocv render`: CVML file to PDF."""

    def test_renders_valid_cvml_to_pdf(self, tmp_path: Path) -> None:
        source = tmp_path / "cv.cvml.yaml"
        source.write_text(yaml.safe_dump(_MINIMAL_CV), encoding="utf-8")
        output = tmp_path / "cv.pdf"

        result = runner.invoke(app, ["render", str(source), "--output", str(output)])

        assert result.exit_code == 0
        assert output.read_bytes().startswith(b"%PDF")

    def test_renders_with_alternate_template(self, tmp_path: Path) -> None:
        source = tmp_path / "cv.cvml.yaml"
        source.write_text(yaml.safe_dump(_MINIMAL_CV), encoding="utf-8")
        output = tmp_path / "cv.pdf"

        result = runner.invoke(
            app, ["render", str(source), "-o", str(output), "--template", "compact"]
        )

        assert result.exit_code == 0
        assert output.read_bytes().startswith(b"%PDF")

    def test_unknown_template_exits_nonzero(self, tmp_path: Path) -> None:
        source = tmp_path / "cv.cvml.yaml"
        source.write_text(yaml.safe_dump(_MINIMAL_CV), encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "render",
                str(source),
                "-o",
                str(tmp_path / "cv.pdf"),
                "--template",
                "does-not-exist",
            ],
        )

        assert result.exit_code == 1

    def test_missing_source_file_exits_nonzero(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["render", str(tmp_path / "missing.cvml.yaml"), "-o", str(tmp_path / "cv.pdf")]
        )
        assert result.exit_code == 1

    def test_invalid_schema_exits_nonzero(self, tmp_path: Path) -> None:
        source = tmp_path / "cv.cvml.yaml"
        source.write_text(yaml.safe_dump({"person": {"name": "Ada"}}), encoding="utf-8")

        result = runner.invoke(app, ["render", str(source), "-o", str(tmp_path / "cv.pdf")])

        assert result.exit_code == 1

    def test_missing_referenced_photo_exits_nonzero(self, tmp_path: Path) -> None:
        data = dict(_MINIMAL_CV)
        data["person"] = dict(data["person"], photo="missing.jpg")
        source = tmp_path / "cv.cvml.yaml"
        source.write_text(yaml.safe_dump(data), encoding="utf-8")

        result = runner.invoke(app, ["render", str(source), "-o", str(tmp_path / "cv.pdf")])

        assert result.exit_code == 1


class _Fixtures:
    """Shared setup for TestAdaptCommand: valid profile and base CV files."""

    @staticmethod
    def profile_path(tmp_path: Path) -> Path:
        path = tmp_path / "profile.md"
        path.write_text(_MINIMAL_PROFILE_MD, encoding="utf-8")
        return path

    @staticmethod
    def base_path(tmp_path: Path) -> Path:
        path = tmp_path / "base.cvml.yaml"
        path.write_text(yaml.safe_dump(_MINIMAL_CV), encoding="utf-8")
        return path

    @staticmethod
    def job_text_path(tmp_path: Path) -> Path:
        path = tmp_path / "job.txt"
        path.write_text("We need a software engineer.", encoding="utf-8")
        return path


class TestAdaptCommand:
    """`autocv adapt`: job posting + master profile to a tailored CVML file."""

    def _args(self, tmp_path: Path, output: Path, **extra: str) -> list[str]:
        args = [
            "adapt",
            "--profile",
            str(_Fixtures.profile_path(tmp_path)),
            "--base",
            str(_Fixtures.base_path(tmp_path)),
            "--output",
            str(output),
            "--job-text-file",
            str(_Fixtures.job_text_path(tmp_path)),
        ]
        for key, value in extra.items():
            args += [f"--{key.replace('_', '-')}", value]
        return args

    def test_writes_tailored_cvml(self, tmp_path: Path, mocker: MockerFixture) -> None:
        _mock_agentic_subprocess(mocker)
        output = tmp_path / "tailored.cvml.yaml"

        result = runner.invoke(app, self._args(tmp_path, output))

        assert result.exit_code == 0
        written = yaml.safe_load(output.read_text(encoding="utf-8"))
        assert written["summary"] == "Tailored summary."
        assert written["person"]["name"] == "Ada Lovelace"

    def test_both_job_url_and_job_text_file_exits_nonzero(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        _mock_agentic_subprocess(mocker)
        output = tmp_path / "tailored.cvml.yaml"

        result = runner.invoke(
            app, [*self._args(tmp_path, output), "--job-url", "https://example.com/jobs/1"]
        )

        assert result.exit_code == 1

    def test_missing_profile_exits_nonzero(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "adapt",
                "--profile",
                str(tmp_path / "missing.profile.md"),
                "--base",
                str(_Fixtures.base_path(tmp_path)),
                "--output",
                str(tmp_path / "out.cvml.yaml"),
                "--job-text-file",
                str(_Fixtures.job_text_path(tmp_path)),
            ],
        )
        assert result.exit_code == 1

    def test_unknown_backend_exits_nonzero(self, tmp_path: Path) -> None:
        output = tmp_path / "tailored.cvml.yaml"
        result = runner.invoke(app, self._args(tmp_path, output, backend="not-a-backend"))
        assert result.exit_code == 1

    def test_gemini_backend_without_api_key_exits_nonzero(self, tmp_path: Path) -> None:
        output = tmp_path / "tailored.cvml.yaml"
        result = runner.invoke(app, [*self._args(tmp_path, output, backend="gemini")])
        assert result.exit_code == 1

    def test_backend_failure_exits_nonzero(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=_completed(stdout="", returncode=1),
        )
        output = tmp_path / "tailored.cvml.yaml"

        result = runner.invoke(app, self._args(tmp_path, output))

        assert result.exit_code == 1
