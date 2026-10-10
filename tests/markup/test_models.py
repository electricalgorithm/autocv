"""Unit tests for autocv.markup.models."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from autocv.markup.models import CV, Contact, ExperienceEntry, Person


class TestPerson:
    """Person model: header identity fields."""

    def test_accepts_minimal_data(self) -> None:
        person = Person(name="Ada Lovelace", headline="Software Engineer")
        assert person.name == "Ada Lovelace"
        assert person.citizenships == []
        assert person.photo is None

    def test_strips_surrounding_whitespace(self) -> None:
        person = Person(name="  Ada Lovelace  ", headline="Software Engineer")
        assert person.name == "Ada Lovelace"

    def test_rejects_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            Person(headline="Software Engineer")  # type: ignore[call-arg]

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            Person(name="Ada", headline="Engineer", hobby="chess")  # type: ignore[call-arg]

    def test_accepts_full_data(self) -> None:
        person = Person(
            name="Ada Lovelace",
            headline="Software Engineer",
            photo="assets/photo.jpg",
            birth_date="1815-12-10",
            citizenships=["British"],
            work_authorization="EU work permit",
        )
        assert person.citizenships == ["British"]


class TestContact:
    """Contact model: header contact fields."""

    def test_accepts_minimal_data(self) -> None:
        contact = Contact(email="ada@example.com", phone="+1 555 0100", location="London, UK")
        assert contact.linkedin is None
        assert contact.scholar is None

    def test_rejects_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            Contact(email="not-an-email", phone="+1 555 0100", location="London, UK")


class TestExperienceEntry:
    """ExperienceEntry model: professional experience entries."""

    def _data(self, **overrides: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "title": "Software Engineer",
            "organization": "Example Corp",
            "location": "London, UK",
            "start": "2023-01",
            "end": "present",
            "summary": "Built things.",
        }
        data.update(overrides)
        return data

    def test_accepts_present_as_end(self) -> None:
        entry = ExperienceEntry(**self._data(end="present"))
        assert entry.end == "present"

    def test_accepts_year_month_end(self) -> None:
        entry = ExperienceEntry(**self._data(end="2024-06"))
        assert entry.end == "2024-06"

    def test_defaults_keywords_to_empty_list(self) -> None:
        entry = ExperienceEntry(**self._data())
        assert entry.keywords == []

    @pytest.mark.parametrize("bad_start", ["2023", "2023/01", "23-01", "2023-13", "not-a-date"])
    def test_rejects_malformed_start(self, bad_start: str) -> None:
        with pytest.raises(ValidationError):
            ExperienceEntry(**self._data(start=bad_start))

    def test_rejects_malformed_end_not_present(self) -> None:
        with pytest.raises(ValidationError):
            ExperienceEntry(**self._data(end="ongoing"))

    def test_accepts_highlights_without_summary(self) -> None:
        data = self._data(highlights=["Shipped X."])
        del data["summary"]
        entry = ExperienceEntry(**data)
        assert entry.summary is None
        assert entry.highlights == ["Shipped X."]

    def test_rejects_missing_summary_and_highlights(self) -> None:
        data = self._data()
        del data["summary"]
        with pytest.raises(ValidationError, match="summary or at least one highlight"):
            ExperienceEntry(**data)


class TestCV:
    """CV model: full document composition."""

    def test_minimal_document_defaults_lists_to_empty(
        self, minimal_cv_data: dict[str, Any]
    ) -> None:
        cv = CV.model_validate(minimal_cv_data)
        assert cv.experience == []
        assert cv.skills == []
        assert cv.certifications == []

    def test_accepts_certifications(self, minimal_cv_data: dict[str, Any]) -> None:
        minimal_cv_data["certifications"] = ["Introduction to Git"]
        cv = CV.model_validate(minimal_cv_data)
        assert cv.certifications == ["Introduction to Git"]

    def test_full_document_round_trips_through_dump(self, full_cv_data: dict[str, Any]) -> None:
        cv = CV.model_validate(full_cv_data)
        dumped = cv.model_dump(mode="json")
        reloaded = CV.model_validate(dumped)
        assert reloaded == cv

    def test_rejects_unknown_top_level_field(self, minimal_cv_data: dict[str, Any]) -> None:
        minimal_cv_data["hobbies"] = ["chess"]
        with pytest.raises(ValidationError):
            CV.model_validate(minimal_cv_data)

    def test_rejects_missing_person(self, minimal_cv_data: dict[str, Any]) -> None:
        del minimal_cv_data["person"]
        with pytest.raises(ValidationError):
            CV.model_validate(minimal_cv_data)
