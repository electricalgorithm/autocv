"""Unit tests for autocv.adapt.workflow."""

from __future__ import annotations

import asyncio
import time

import pytest

from autocv.adapt.errors import ResearchError
from autocv.adapt.models import CompanyResearch, FactCheckReport
from autocv.adapt.workflow import CVWorkflow
from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile

_DELAY = 0.2


class _StubDrafter:
    def __init__(self, cv: CV) -> None:
        self._cv = cv
        self.calls = 0

    def adapt(self, profile: MasterProfile, job: JobPosting, base: CV) -> CV:
        self.calls += 1
        return self._cv


class _SleepingResearcher:
    def __init__(self, delay: float = _DELAY, result: CompanyResearch | None = None) -> None:
        self._delay = delay
        self._result = result or CompanyResearch(summary="Findings.")
        self.calls = 0

    def research(self, job: JobPosting) -> CompanyResearch:
        self.calls += 1
        time.sleep(self._delay)
        return self._result


class _RaisingResearcher:
    def research(self, job: JobPosting) -> CompanyResearch:
        raise ResearchError("network unreachable")


class _SleepingFactChecker:
    def __init__(self, delay: float = _DELAY, report: FactCheckReport | None = None) -> None:
        self._delay = delay
        self._report = report or FactCheckReport()
        self.calls = 0

    def check(self, draft: CV, profile: MasterProfile) -> FactCheckReport:
        self.calls += 1
        time.sleep(self._delay)
        return self._report


class _RaisingFactChecker:
    def check(self, draft: CV, profile: MasterProfile) -> FactCheckReport:
        raise RuntimeError("backend exploded")


class _RecordingEditor:
    def __init__(self, cv: CV) -> None:
        self._cv = cv
        self.calls: list[tuple[object, ...]] = []

    def edit(
        self,
        draft: CV,
        research: CompanyResearch,
        fact_check: FactCheckReport,
        profile: MasterProfile,
        job: JobPosting,
        base: CV,
    ) -> CV:
        self.calls.append((draft, research, fact_check, profile, job, base))
        return self._cv


class TestCVWorkflow:
    """CVWorkflow: draft -> (research || fact-check) -> edit."""

    def test_runs_full_pipeline_and_returns_editor_output(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        draft = base_cv.model_copy(update={"summary": "Draft."})
        final = base_cv.model_copy(update={"summary": "Final."})
        drafter = _StubDrafter(draft)
        researcher = _SleepingResearcher(delay=0.0)
        fact_checker = _SleepingFactChecker(delay=0.0)
        editor = _RecordingEditor(final)
        workflow = CVWorkflow(drafter, researcher, fact_checker, editor)

        result = asyncio.run(workflow.run(profile, job, base_cv))

        assert result.summary == "Final."
        assert drafter.calls == 1
        assert researcher.calls == 1
        assert fact_checker.calls == 1
        assert len(editor.calls) == 1
        edit_draft, edit_research, edit_fact_check, *_ = editor.calls[0]
        assert edit_draft == draft
        assert edit_research.summary == "Findings."
        assert edit_fact_check.passed is True

    def test_research_and_fact_check_run_concurrently(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        drafter = _StubDrafter(base_cv)
        editor = _RecordingEditor(base_cv)
        workflow = CVWorkflow(drafter, _SleepingResearcher(), _SleepingFactChecker(), editor)

        start = time.monotonic()
        asyncio.run(workflow.run(profile, job, base_cv))
        elapsed = time.monotonic() - start

        # Sequential execution would take >= 2 * _DELAY; concurrent execution
        # should take roughly 1 * _DELAY plus scheduling overhead.
        assert elapsed < 1.5 * _DELAY

    def test_research_failure_degrades_to_empty_findings(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        drafter = _StubDrafter(base_cv)
        editor = _RecordingEditor(base_cv)
        workflow = CVWorkflow(
            drafter, _RaisingResearcher(), _SleepingFactChecker(delay=0.0), editor
        )

        asyncio.run(workflow.run(profile, job, base_cv))

        assert len(editor.calls) == 1
        _, research, *_ = editor.calls[0]
        assert research.products == []
        assert "network unreachable" in research.summary

    def test_fact_check_failure_propagates_and_skips_editor(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        drafter = _StubDrafter(base_cv)
        editor = _RecordingEditor(base_cv)
        workflow = CVWorkflow(
            drafter, _SleepingResearcher(delay=0.0), _RaisingFactChecker(), editor
        )

        with pytest.raises(RuntimeError, match="backend exploded"):
            asyncio.run(workflow.run(profile, job, base_cv))

        assert editor.calls == []

    def test_drafter_failure_skips_research_and_fact_check(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        class _RaisingDrafter:
            def adapt(self, profile: MasterProfile, job: JobPosting, base: CV) -> CV:
                raise RuntimeError("draft failed")

        researcher = _SleepingResearcher(delay=0.0)
        fact_checker = _SleepingFactChecker(delay=0.0)
        editor = _RecordingEditor(base_cv)
        workflow = CVWorkflow(_RaisingDrafter(), researcher, fact_checker, editor)

        with pytest.raises(RuntimeError, match="draft failed"):
            asyncio.run(workflow.run(profile, job, base_cv))

        assert researcher.calls == 0
        assert fact_checker.calls == 0
        assert editor.calls == []
