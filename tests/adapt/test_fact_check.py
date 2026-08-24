"""Unit tests for autocv.adapt.fact_check."""

from __future__ import annotations

import pytest

from autocv.adapt.errors import StructuredOutputError
from autocv.adapt.fact_check import LLMFactChecker
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile

_NO_ISSUES_YAML = "issues: []\n"
_ONE_ISSUE_YAML = """
issues:
  - claim: Led a team of 50 engineers
    explanation: Not present in the master profile.
"""


class _ScriptedBackend:
    """Test double returning a fixed sequence of responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self._responses.pop(0)


class TestLLMFactChecker:
    """LLMFactChecker: generate, parse, validate, retry-once-on-error."""

    def test_returns_report_with_no_issues(self, profile: MasterProfile, base_cv: CV) -> None:
        backend = _ScriptedBackend([_NO_ISSUES_YAML])
        report = LLMFactChecker(backend).check(base_cv, profile)
        assert report.passed is True
        assert len(backend.calls) == 1

    def test_returns_report_with_issues(self, profile: MasterProfile, base_cv: CV) -> None:
        backend = _ScriptedBackend([_ONE_ISSUE_YAML])
        report = LLMFactChecker(backend).check(base_cv, profile)
        assert report.passed is False
        assert report.issues[0].claim == "Led a team of 50 engineers"

    def test_retries_once_on_malformed_output(self, profile: MasterProfile, base_cv: CV) -> None:
        backend = _ScriptedBackend(["not: [valid", _NO_ISSUES_YAML])
        report = LLMFactChecker(backend).check(base_cv, profile)
        assert report.passed is True
        assert len(backend.calls) == 2
        assert "previous attempt was invalid" in backend.calls[1][1]

    def test_gives_up_after_max_attempts(self, profile: MasterProfile, base_cv: CV) -> None:
        backend = _ScriptedBackend(["not: [valid", "still: [not valid"])
        with pytest.raises(StructuredOutputError):
            LLMFactChecker(backend).check(base_cv, profile)
        assert len(backend.calls) == 2
