"""Unit tests for autocv.profile.parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocv.profile.errors import ProfileSourceError, ProfileValidationError
from autocv.profile.parser import MarkdownProfileSource, load_profile


class TestMarkdownProfileSource:
    """MarkdownProfileSource: loads and validates a master profile from disk."""

    def test_loads_full_document(self, tmp_path: Path, full_profile_md: str) -> None:
        path = tmp_path / "profile.md"
        path.write_text(full_profile_md, encoding="utf-8")

        profile = MarkdownProfileSource(path).load()

        assert len(profile.experience) == 2
        assert profile.experience[0].title == "Software Engineer"
        assert profile.experience[0].organization_url == "https://example.com"
        assert profile.experience[0].keywords == ["Python", "Kubernetes"]
        assert profile.experience[0].achievements == [
            "Cut deploy time from 40 minutes to 6 by moving CI to buildkite.",
            "Led the migration of the billing service to Kubernetes.",
        ]
        assert profile.education[0].degree == "BEng. Computer Engineering"
        assert profile.skills == ["Python", "Kubernetes", "Team leadership"]
        assert profile.certifications == [
            "Certified Kubernetes Administrator",
            "AWS Certified Solutions Architect",
        ]
        assert profile.publications[0].title == "Paper Title"
        assert profile.projects[0].categories == ["Web", "Embedded"]
        assert profile.projects[0].stack == ["Python", "MQTT"]
        assert profile.projects[0].achievements == [
            "Built a broker-enforced schema layer for MQTT topics."
        ]

    def test_empty_document_yields_empty_profile(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.md"
        path.write_text("", encoding="utf-8")
        profile = MarkdownProfileSource(path).load()
        assert profile.experience == []
        assert profile.skills == []
        assert profile.certifications == []

    def test_missing_file_raises_source_error(self, tmp_path: Path) -> None:
        with pytest.raises(ProfileSourceError):
            MarkdownProfileSource(tmp_path / "missing.md").load()

    def test_unknown_section_raises_source_error(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.md"
        path.write_text("## Hobbies\n- Chess\n", encoding="utf-8")
        with pytest.raises(ProfileSourceError, match="unknown section"):
            MarkdownProfileSource(path).load()

    def test_entry_heading_outside_section_raises_source_error(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.md"
        path.write_text("### Software Engineer\n- Organization: X\n", encoding="utf-8")
        with pytest.raises(ProfileSourceError):
            MarkdownProfileSource(path).load()

    def test_bullet_outside_entry_raises_source_error(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.md"
        path.write_text("## Experience\n- Organization: X\n", encoding="utf-8")
        with pytest.raises(ProfileSourceError):
            MarkdownProfileSource(path).load()

    def test_missing_required_field_raises_validation_error(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.md"
        path.write_text(
            "## Experience\n\n### Software Engineer\n- Organization: X\n",
            encoding="utf-8",
        )
        with pytest.raises(ProfileValidationError):
            MarkdownProfileSource(path).load()

    def test_achievements_under_education_raises_validation_error(self, tmp_path: Path) -> None:
        path = tmp_path / "profile.md"
        path.write_text(
            "## Education\n\n"
            "### BEng.\n"
            "- Institution: X\n"
            "- Location: Y\n"
            "- Start: 2020-01\n"
            "- End: 2022-01\n\n"
            "Achievements:\n"
            "- Not allowed here.\n",
            encoding="utf-8",
        )
        with pytest.raises(ProfileValidationError):
            MarkdownProfileSource(path).load()


class TestLoadProfile:
    """load_profile: module-level convenience wrapper."""

    def test_loads_valid_document(self, tmp_path: Path, full_profile_md: str) -> None:
        path = tmp_path / "profile.md"
        path.write_text(full_profile_md, encoding="utf-8")
        profile = load_profile(path)
        assert len(profile.projects) == 1
