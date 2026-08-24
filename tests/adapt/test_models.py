"""Unit tests for autocv.adapt.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autocv.adapt.models import CompanyResearch, FactCheckIssue, FactCheckReport


class TestCompanyResearch:
    """CompanyResearch: research-agent findings about the hiring company."""

    def test_defaults_lists_to_empty(self) -> None:
        research = CompanyResearch(summary="A cloud infrastructure company.")
        assert research.products == []
        assert research.sources == []

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            CompanyResearch.model_validate({"summary": "x", "founded": 1999})


class TestFactCheckReport:
    """FactCheckReport: fact-checker output over a draft CV."""

    def test_passed_true_when_no_issues(self) -> None:
        assert FactCheckReport().passed is True

    def test_passed_false_when_issues_present(self) -> None:
        report = FactCheckReport(
            issues=[FactCheckIssue(claim="Led a team of 50", explanation="Not in profile")]
        )
        assert report.passed is False
