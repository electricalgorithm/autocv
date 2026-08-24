"""Editorial agent: synthesizes the final CV from the draft and both reviews."""

from __future__ import annotations

from typing import Protocol

from autocv.adapt.backends import MarkupGenerationBackend
from autocv.adapt.errors import AdaptationError
from autocv.adapt.generator import enforce_base_identity, generate_cv_with_retry
from autocv.adapt.models import CompanyResearch, FactCheckReport
from autocv.adapt.prompts import build_editorial_system_prompt, build_editorial_user_prompt
from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile


class Editor(Protocol):
    """Synthesizes the final CV from the draft, research, and fact-check."""

    def edit(  # noqa: PLR0913, PLR0917 - each is distinct input material
        self,
        draft: CV,
        research: CompanyResearch,
        fact_check: FactCheckReport,
        profile: MasterProfile,
        job: JobPosting,
        base: CV,
    ) -> CV:
        """Produce the final CV.

        Args:
            draft: The draft CV produced by the drafting agent.
            research: Company research findings.
            fact_check: The fact-check report over the draft.
            profile: The applicant's full experience pool.
            job: The job posting to tailor the CV to.
            base: The base CV; its identity fields are carried through
                unchanged.

        Returns:
            The final, validated CV.

        Raises:
            BackendError: If the backend itself fails to produce a response.
            AdaptationError: If the backend's response never satisfies the
                CV schema within the retry budget.
        """
        ...


class LLMEditor:
    """Synthesizes the final CV via any `MarkupGenerationBackend`.

    Backend-agnostic, like drafting and fact-checking: this is text
    synthesis over data already gathered, not a tool-using role.
    """

    def __init__(self, backend: MarkupGenerationBackend) -> None:
        """Initialize the editor.

        Args:
            backend: The LLM backend to generate text with.
        """
        self._backend = backend

    def edit(  # noqa: PLR0913, PLR0917 - each is distinct input material
        self,
        draft: CV,
        research: CompanyResearch,
        fact_check: FactCheckReport,
        profile: MasterProfile,
        job: JobPosting,
        base: CV,
    ) -> CV:
        """Produce the final CV.

        Args:
            draft: The draft CV produced by the drafting agent.
            research: Company research findings.
            fact_check: The fact-check report over the draft.
            profile: The applicant's full experience pool.
            job: The job posting to tailor the CV to.
            base: The base CV; its identity fields are carried through
                unchanged.

        Returns:
            The final, validated CV.

        Raises:
            BackendError: If the backend itself fails to produce a response.
            AdaptationError: If the backend's response never satisfies the
                CV schema within the retry budget.
        """
        system_prompt = build_editorial_system_prompt()
        user_prompt = build_editorial_user_prompt(draft, research, fact_check, profile, job, base)
        try:
            cv = generate_cv_with_retry(self._backend, system_prompt, user_prompt)
        except AdaptationError as exc:
            raise AdaptationError(f"editorial pass failed: {exc}") from exc
        return enforce_base_identity(cv, base)
