"""Unit tests for autocv.adapt.generator."""

from __future__ import annotations

import pytest

from autocv.adapt.errors import AdaptationError, BackendError
from autocv.adapt.generator import CVAdapter
from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile

_VALID_CVML = """
person:
  name: Ada Lovelace
  headline: Software Engineer
contact:
  email: ada@example.com
  phone: "+1 555 0100"
  location: London, UK
summary: Tailored summary.
"""


class _ScriptedBackend:
    """Test double returning a fixed sequence of responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self._responses.pop(0)


class _RaisingBackend:
    """Test double that always fails at the backend level."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        raise BackendError("boom")


class TestCVAdapter:
    """CVAdapter: generate, parse, validate, and retry-once-on-error."""

    def test_returns_valid_cv_on_first_attempt(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend([_VALID_CVML])

        cv = CVAdapter(backend).adapt(profile, job, base_cv)

        assert cv.summary == "Tailored summary."
        assert len(backend.calls) == 1

    def test_strips_markdown_code_fence(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend([f"```yaml\n{_VALID_CVML}\n```"])
        cv = CVAdapter(backend).adapt(profile, job, base_cv)
        assert cv.person.name == "Ada Lovelace"

    def test_retries_once_on_malformed_yaml_then_succeeds(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend(["not: valid: yaml: [", _VALID_CVML])

        cv = CVAdapter(backend).adapt(profile, job, base_cv)

        assert cv.person.name == "Ada Lovelace"
        assert len(backend.calls) == 2
        assert "previous attempt was invalid" in backend.calls[1][1]

    def test_retries_once_on_schema_violation_then_succeeds(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend(["person:\n  name: Ada\n", _VALID_CVML])
        cv = CVAdapter(backend).adapt(profile, job, base_cv)
        assert len(backend.calls) == 2
        assert cv.summary == "Tailored summary."

    def test_gives_up_after_max_attempts(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _ScriptedBackend(["not valid yaml: [", "still not valid: ["])

        with pytest.raises(AdaptationError):
            CVAdapter(backend).adapt(profile, job, base_cv)

        assert len(backend.calls) == 2

    def test_forces_base_identity_regardless_of_backend_output(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        drifted_cvml = """
person:
  name: Someone Else
  headline: Different Title
contact:
  email: someone@else.com
  phone: "+1 000 0000"
  location: Nowhere
summary: Tailored summary.
"""
        backend = _ScriptedBackend([drifted_cvml])

        cv = CVAdapter(backend).adapt(profile, job, base_cv)

        assert cv.person == base_cv.person
        assert cv.contact == base_cv.contact
        assert cv.references == base_cv.references
        assert cv.languages == base_cv.languages

    def test_backend_error_propagates_without_retry(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        backend = _RaisingBackend()

        with pytest.raises(BackendError):
            CVAdapter(backend).adapt(profile, job, base_cv)

        assert backend.calls == 1
