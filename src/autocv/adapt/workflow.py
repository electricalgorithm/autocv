"""Agentic CV-tailoring workflow, expressed as a graph.

    GenerateDraft ──┬──▶ ResearchCompany ──┐
                    └──▶ FactCheckDraft ───┴──▶ EditorialSynthesis ──▶ tailored CV

`ResearchCompany` and `FactCheckDraft` run concurrently once the draft
exists; `EditorialSynthesis` starts only after both finish. See
docs/DESIGN.md for why this is plain `asyncio`, and why a failed
`ResearchCompany` degrades to empty findings while a failed
`FactCheckDraft` aborts the run.
"""

from __future__ import annotations

import asyncio

from autocv.adapt.editorial import Editor
from autocv.adapt.errors import ResearchError
from autocv.adapt.fact_check import FactChecker
from autocv.adapt.generator import Drafter
from autocv.adapt.models import CompanyResearch
from autocv.adapt.research import CompanyResearcher
from autocv.jobs.models import JobPosting
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile


class CVWorkflow:
    """Runs the draft -> (research || fact-check) -> edit pipeline."""

    def __init__(
        self,
        drafter: Drafter,
        researcher: CompanyResearcher,
        fact_checker: FactChecker,
        editor: Editor,
    ) -> None:
        """Initialize the workflow.

        Args:
            drafter: Produces the initial draft CV.
            researcher: Gathers company research. A failure here degrades to
                empty findings rather than aborting the run.
            fact_checker: Verifies the draft's claims. A failure here aborts
                the run.
            editor: Synthesizes the final CV from the above.
        """
        self._drafter = drafter
        self._researcher = researcher
        self._fact_checker = fact_checker
        self._editor = editor

    async def run(self, profile: MasterProfile, job: JobPosting, base: CV) -> CV:
        """Run the full adaptation workflow.

        Args:
            profile: The applicant's full experience pool.
            job: The job posting to tailor the CV to.
            base: The base CV; its identity fields are carried through
                unchanged.

        Returns:
            The final, tailored CV.

        Raises:
            BackendError: If drafting, fact-checking, or editing fails at
                the backend level.
            AdaptationError: If drafting or editing never produces valid
                CVML within their retry budgets.
            StructuredOutputError: If fact-checking never produces a valid
                report within its retry budget.
        """
        draft = await asyncio.to_thread(self._drafter.adapt, profile, job, base)

        research, fact_check = await asyncio.gather(
            asyncio.to_thread(self._safe_research, job),
            asyncio.to_thread(self._fact_checker.check, draft, profile),
        )

        return await asyncio.to_thread(
            self._editor.edit, draft, research, fact_check, profile, job, base
        )

    def _safe_research(self, job: JobPosting) -> CompanyResearch:
        """Research the company, degrading to empty findings on failure.

        Args:
            job: The job posting naming the company to research.

        Returns:
            The research findings, or an empty placeholder if research failed.
        """
        try:
            return self._researcher.research(job)
        except ResearchError as exc:
            return CompanyResearch(summary=f"No company research available: {exc}")
