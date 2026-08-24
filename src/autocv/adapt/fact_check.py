"""Fact-checking agent: verifies a draft CV's claims against the master profile."""

from __future__ import annotations

from typing import Protocol

from autocv.adapt.backends import MarkupGenerationBackend
from autocv.adapt.errors import StructuredOutputError
from autocv.adapt.models import FactCheckReport
from autocv.adapt.parsing import parse_yaml_model
from autocv.adapt.prompts import build_fact_check_system_prompt, build_fact_check_user_prompt
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile

_MAX_ATTEMPTS = 2


class FactChecker(Protocol):
    """Verifies a draft CV's claims against the applicant's master profile."""

    def check(self, draft: CV, profile: MasterProfile) -> FactCheckReport:
        """Fact-check a draft CV.

        Args:
            draft: The draft CV to check.
            profile: The applicant's full experience pool (source of truth).

        Returns:
            The fact-check report.

        Raises:
            BackendError: If the backend itself fails to produce a response.
            StructuredOutputError: If the backend's response is never a
                valid report within the retry budget.
        """
        ...


class LLMFactChecker:
    """Fact-checks a draft CV via any `MarkupGenerationBackend`.

    Fact-checking is text reasoning over data already in hand — it needs no
    tools, so any provider works identically here.
    """

    def __init__(self, backend: MarkupGenerationBackend) -> None:
        """Initialize the fact-checker.

        Args:
            backend: The LLM backend to generate text with.
        """
        self._backend = backend

    def check(self, draft: CV, profile: MasterProfile) -> FactCheckReport:
        """Fact-check a draft CV against the master profile.

        Retries once, feeding the parse error back to the backend, if the
        first response isn't a valid report. A backend failure (network,
        missing binary, ...) is not retried and propagates as
        ``BackendError``.

        Args:
            draft: The draft CV to check.
            profile: The applicant's full experience pool (source of truth).

        Returns:
            The fact-check report.

        Raises:
            BackendError: If the backend itself fails to produce a response.
            StructuredOutputError: If the backend's response is never a
                valid report within the retry budget.
        """
        system_prompt = build_fact_check_system_prompt()
        base_user_prompt = build_fact_check_user_prompt(draft, profile)

        last_error: StructuredOutputError | None = None
        for _attempt in range(_MAX_ATTEMPTS):
            prompt = base_user_prompt
            if last_error is not None:
                prompt = (
                    f"{base_user_prompt}\n\n"
                    "## Your previous attempt was invalid\n\n"
                    f"Error: {last_error}\n"
                    "Fix it and output only the corrected YAML document."
                )
            text = self._backend.generate(system_prompt, prompt)
            try:
                return parse_yaml_model(text, FactCheckReport)
            except StructuredOutputError as exc:
                last_error = exc

        raise StructuredOutputError(
            f"fact-check produced invalid output after {_MAX_ATTEMPTS} attempts: {last_error}"
        )
