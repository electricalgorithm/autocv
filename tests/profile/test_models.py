"""Unit tests for autocv.profile.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autocv.profile.models import MasterProfile, ProfileExperience


class TestProfileExperience:
    """ProfileExperience: professional experience entries with achievements."""

    def _data(self, **overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "title": "Software Engineer",
            "organization": "Example Corp",
            "location": "Berlin, Germany",
            "start": "2023-01",
            "end": "present",
        }
        data.update(overrides)
        return data

    def test_defaults_achievements_to_empty_list(self) -> None:
        entry = ProfileExperience(**self._data())
        assert entry.achievements == []

    def test_accepts_achievements(self) -> None:
        entry = ProfileExperience(**self._data(achievements=["Shipped X", "Led Y"]))
        assert entry.achievements == ["Shipped X", "Led Y"]

    def test_rejects_malformed_start(self) -> None:
        with pytest.raises(ValidationError):
            ProfileExperience(**self._data(start="not-a-date"))


class TestMasterProfile:
    """MasterProfile: the applicant's full experience pool."""

    def test_all_sections_default_to_empty(self) -> None:
        profile = MasterProfile()
        assert profile.experience == []
        assert profile.skills == []

    def test_rejects_unknown_top_level_field(self) -> None:
        with pytest.raises(ValidationError):
            MasterProfile.model_validate({"hobbies": ["chess"]})
