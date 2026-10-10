"""Unit tests for autocv.adapt.prompts."""

from __future__ import annotations

from autocv.adapt.models import CompanyResearch, FactCheckIssue, FactCheckReport
from autocv.adapt.prompts import (
    build_editorial_system_prompt,
    build_editorial_user_prompt,
    build_fact_check_system_prompt,
    build_fact_check_user_prompt,
    build_research_system_prompt,
    build_research_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile


class TestBuildSystemPrompt:
    """build_system_prompt: instructions plus the CVML JSON Schema."""

    def test_includes_schema_field_names(self) -> None:
        prompt = build_system_prompt()
        assert '"person"' in prompt
        assert '"experience"' in prompt

    def test_includes_no_invention_rule(self) -> None:
        prompt = build_system_prompt()
        assert "Never" in prompt
        assert "invent" in prompt

    def test_asks_for_highlights_not_summary_paragraphs(self) -> None:
        prompt = build_system_prompt()
        assert '"highlights" (a bullet list) and no "summary"' in prompt
        assert 'Do not emit "keywords"' in prompt

    def test_includes_writing_style_rules(self) -> None:
        prompt = build_system_prompt()
        assert "No em dashes" in prompt
        assert "Do not name specific LLM vendors" in prompt
        assert "—" not in prompt


class TestBuildUserPrompt:
    """build_user_prompt: job posting, base identity, and profile pool."""

    def test_includes_job_details(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        prompt = build_user_prompt(profile, job, base_cv)
        assert job.title in prompt
        assert job.description in prompt

    def test_includes_base_contact_email(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        prompt = build_user_prompt(profile, job, base_cv)
        assert base_cv.contact.email in prompt

    def test_includes_profile_achievements(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        prompt = build_user_prompt(profile, job, base_cv)
        assert profile.experience[0].achievements[0] in prompt

    def test_missing_company_and_location_fall_back_to_unknown(
        self, profile: MasterProfile, base_cv: CV
    ) -> None:
        job = JobPosting(title="Engineer", description="Build things.")
        prompt = build_user_prompt(profile, job, base_cv)
        assert "Company: unknown" in prompt
        assert "Location: unknown" in prompt


class TestBuildResearchPrompts:
    """build_research_system_prompt / build_research_user_prompt."""

    def test_system_prompt_includes_schema_fields(self) -> None:
        prompt = build_research_system_prompt()
        assert '"summary"' in prompt
        assert '"culture_notes"' in prompt

    def test_system_prompt_forbids_guessing(self) -> None:
        prompt = build_research_system_prompt()
        assert "do not guess" in prompt.lower()

    def test_user_prompt_includes_job_details(self, job: JobPosting) -> None:
        prompt = build_research_user_prompt(job)
        assert job.title in prompt
        assert job.description in prompt


class TestBuildFactCheckPrompts:
    """build_fact_check_system_prompt / build_fact_check_user_prompt."""

    def test_system_prompt_includes_schema_fields(self) -> None:
        prompt = build_fact_check_system_prompt()
        assert '"issues"' in prompt
        assert '"claim"' in prompt

    def test_user_prompt_includes_draft_and_profile(
        self, profile: MasterProfile, base_cv: CV
    ) -> None:
        draft = base_cv.model_copy(update={"summary": "Draft summary text."})
        prompt = build_fact_check_user_prompt(draft, profile)
        assert "Draft summary text." in prompt
        assert profile.experience[0].organization in prompt


class TestBuildEditorialPrompts:
    """build_editorial_system_prompt / build_editorial_user_prompt."""

    def test_system_prompt_mentions_fact_check_and_research(self) -> None:
        prompt = build_editorial_system_prompt()
        assert "fact-check" in prompt.lower()
        assert "company research" in prompt.lower()

    def test_system_prompt_includes_same_style_guide_as_draft(self) -> None:
        prompt = build_editorial_system_prompt()
        assert "No em dashes" in prompt
        assert '"highlights" (a bullet list) and no "summary"' in prompt
        assert "—" not in prompt

    def test_user_prompt_includes_everything(
        self, profile: MasterProfile, job: JobPosting, base_cv: CV
    ) -> None:
        draft = base_cv.model_copy(update={"summary": "Draft summary text."})
        research = CompanyResearch(summary="Builds developer tools.", products=["Widget API"])
        fact_check = FactCheckReport(
            issues=[FactCheckIssue(claim="Managed 50 engineers", explanation="Not in profile")]
        )

        prompt = build_editorial_user_prompt(draft, research, fact_check, profile, job, base_cv)

        assert "Draft summary text." in prompt
        assert "Widget API" in prompt
        assert "Managed 50 engineers" in prompt
        assert job.title in prompt
        assert base_cv.contact.email in prompt
