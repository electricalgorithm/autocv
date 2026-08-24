"""Shared CVML generation: prompt -> backend -> validate -> retry once."""

from __future__ import annotations

from typing import Protocol

from autocv.adapt.backends import MarkupGenerationBackend
from autocv.adapt.errors import AdaptationError, StructuredOutputError
from autocv.adapt.parsing import parse_yaml_model
from autocv.adapt.prompts import build_system_prompt, build_user_prompt
from autocv.jobs.models import JobPosting
from autocv.markup.errors import CVValidationError
from autocv.markup.models import CV
from autocv.profile.models import MasterProfile

_MAX_ATTEMPTS = 2


class Drafter(Protocol):
    """Produces an initial draft CV tailored to a job posting."""

    def adapt(self, profile: MasterProfile, job: JobPosting, base: CV) -> CV:
        """Generate a draft CV.

        Args:
            profile: The applicant's full experience pool.
            job: The job posting to tailor the CV to.
            base: The base CV; its identity fields are carried through
                unchanged.

        Returns:
            A validated, tailored CV.

        Raises:
            BackendError: If the backend itself fails to produce a response.
            AdaptationError: If the backend's response never satisfies the
                CV schema within the retry budget.
        """
        ...


def _parse_cv_text(text: str) -> CV:
    """Parse and validate a backend's CVML text output.

    Args:
        text: Raw backend output, expected to be a CVML YAML document.

    Returns:
        The validated CV.

    Raises:
        CVValidationError: If the text is not valid YAML, not a mapping, or
            does not satisfy the CV schema.
    """
    try:
        return parse_yaml_model(text, CV)
    except StructuredOutputError as exc:
        raise CVValidationError(str(exc)) from exc


def enforce_base_identity(cv: CV, base: CV) -> CV:
    """Replace identity fields with the base CV's, regardless of backend output.

    ``person``/``contact`` must never drift from the applicant's real
    identity, and the master profile carries no ``references``/``languages``
    for a backend to draw on — so all four are always taken from the base CV
    rather than trusted from a backend response.

    Args:
        cv: A backend-produced CV.
        base: The base CV to take identity fields from.

    Returns:
        ``cv`` with ``person``/``contact``/``references``/``languages``
        replaced by ``base``'s.
    """
    return cv.model_copy(
        update={
            "person": base.person,
            "contact": base.contact,
            "references": base.references,
            "languages": base.languages,
        }
    )


def generate_cv_with_retry(
    backend: MarkupGenerationBackend, system_prompt: str, user_prompt: str
) -> CV:
    """Generate CVML text and validate it, retrying once on schema failure.

    Args:
        backend: The LLM backend to generate text with.
        system_prompt: The agent's system prompt for this call.
        user_prompt: The agent's user prompt for this call.

    Returns:
        The validated CV, as returned by the backend (identity fields not
        yet enforced — see ``enforce_base_identity``).

    Raises:
        BackendError: If the backend itself fails to produce a response.
        AdaptationError: If the backend's response never satisfies the CV
            schema within the retry budget.
    """
    last_error: CVValidationError | None = None
    for _attempt in range(_MAX_ATTEMPTS):
        prompt = user_prompt
        if last_error is not None:
            prompt = (
                f"{user_prompt}\n\n"
                "## Your previous attempt was invalid\n\n"
                f"Error: {last_error}\n"
                "Fix it and output only the corrected YAML document."
            )
        text = backend.generate(system_prompt, prompt)
        try:
            return _parse_cv_text(text)
        except CVValidationError as exc:
            last_error = exc

    raise AdaptationError(
        f"backend produced invalid CVML after {_MAX_ATTEMPTS} attempts: {last_error}"
    )


class CVAdapter:
    """Generates a draft CVML document from a job posting and a profile."""

    def __init__(self, backend: MarkupGenerationBackend) -> None:
        """Initialize the adapter.

        Args:
            backend: The LLM backend to generate text with.
        """
        self._backend = backend

    def adapt(self, profile: MasterProfile, job: JobPosting, base: CV) -> CV:
        """Generate a CV tailored to a job posting.

        Retries once, feeding the validation error back to the backend, if
        the first response does not satisfy the CV schema. A backend failure
        (network, missing binary, ...) is not retried and propagates as
        ``BackendError``.

        Args:
            profile: The applicant's full experience pool.
            job: The job posting to tailor the CV to.
            base: The base CV; its identity fields are carried through
                unchanged.

        Returns:
            A validated, tailored CV.

        Raises:
            BackendError: If the backend itself fails to produce a response.
            AdaptationError: If the backend's response never satisfies the
                CV schema within the retry budget.
        """
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(profile, job, base)
        cv = generate_cv_with_retry(self._backend, system_prompt, user_prompt)
        return enforce_base_identity(cv, base)
