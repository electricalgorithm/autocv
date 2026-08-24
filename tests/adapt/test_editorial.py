"""Unit tests for autocv.adapt.editorial."""

from __future__ import annotations

import pytest

from autocv.adapt.editorial import LLMEditor
from autocv.adapt.errors import AdaptationError
from autocv.adapt.models import CompanyResearch, FactCheckReport
from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile

_VALID_CVML = """
person:
  name: Someone Else
  headline: Different Title
contact:
  email: someone@else.com
  phone: "+1 000 0000"
  location: Nowhere
summary: Edited summary.
"""


class _ScriptedBackend:
    """Test double returning a fixed sequence of responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self._responses.pop(0)


class TestLLMEditor:
    """LLMEditor: synthesize the final CV, retry-once, enforce base identity."""

    def test_returns_edited_cv_on_first_attempt(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend([_VALID_CVML])

        cv = LLMEditor(backend).edit(
            base_cv, CompanyResearch(summary="x"), FactCheckReport(), profile, job, base_cv
        )

        assert cv.summary == "Edited summary."
        assert len(backend.calls) == 1

    def test_forces_base_identity_regardless_of_backend_output(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend([_VALID_CVML])

        cv = LLMEditor(backend).edit(
            base_cv, CompanyResearch(summary="x"), FactCheckReport(), profile, job, base_cv
        )

        assert cv.person == base_cv.person
        assert cv.contact == base_cv.contact
        assert cv.references == base_cv.references
        assert cv.languages == base_cv.languages

    def test_retries_once_on_malformed_output(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend(["not: [valid", _VALID_CVML])

        cv = LLMEditor(backend).edit(
            base_cv, CompanyResearch(summary="x"), FactCheckReport(), profile, job, base_cv
        )

        assert cv.summary == "Edited summary."
        assert len(backend.calls) == 2

    def test_gives_up_after_max_attempts(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend(["not: [valid", "still: [not valid"])

        with pytest.raises(AdaptationError):
            LLMEditor(backend).edit(
                base_cv, CompanyResearch(summary="x"), FactCheckReport(), profile, job, base_cv
            )

        assert len(backend.calls) == 2
