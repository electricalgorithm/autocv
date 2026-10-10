"""Command-line entry point for autocv."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
import yaml

from autocv.adapt.backends import (
    ClaudeCodeCLIBackend,
    GeminiBackend,
    MarkupGenerationBackend,
    OllamaBackend,
)
from autocv.adapt.editorial import LLMEditor
from autocv.adapt.errors import AdaptationError, BackendError, StructuredOutputError
from autocv.adapt.fact_check import LLMFactChecker
from autocv.adapt.generator import CVAdapter
from autocv.adapt.research import (
    ClaudeCodeCLICompanyResearcher,
    CompanyResearcher,
    build_gemini_researcher,
    build_ollama_researcher,
)
from autocv.adapt.workflow import CVWorkflow
from autocv.jobs.errors import JobFetchError
from autocv.jobs.fetcher import LinkedInJobFetcher, default_http_client
from autocv.jobs.models import JobPosting
from autocv.markup.errors import CVSourceError, CVValidationError
from autocv.markup.parser import load_cv
from autocv.profile.errors import ProfileSourceError, ProfileValidationError
from autocv.profile.parser import load_profile
from autocv.render.errors import RenderError
from autocv.render.html_renderer import PlaywrightHTMLRenderer

app = typer.Typer(help="Render and adapt CVML documents.")

_BACKEND_NAMES = ("claude-code", "gemini", "ollama")
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
_DEFAULT_TEMPLATE = "default"


@app.callback()
def main() -> None:
    """Render and adapt CVML documents."""


@app.command()
def render(
    source: Path = typer.Argument(..., help="Path to a .cvml.yaml file."),
    output: Path = typer.Option(..., "--output", "-o", help="Destination PDF path."),
    template: str = typer.Option(
        _DEFAULT_TEMPLATE, "--template", help="Template name (a subdirectory of render/templates)."
    ),
) -> None:
    """Render a CVML document to a PDF."""
    try:
        cv = load_cv(source)
    except (CVSourceError, CVValidationError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        PlaywrightHTMLRenderer(template=template).render(cv, output, source.parent)
    except RenderError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"rendered {output}")


def _build_agents(
    name: str, model: str | None, gemini_api_key: str | None, ollama_base_url: str
) -> tuple[MarkupGenerationBackend, CompanyResearcher]:
    """Construct the LLM backend and company researcher named on the command line.

    Both are built from the same provider choice and credentials: the
    backend drafts/fact-checks/edits (plain text, no tools), the researcher
    additionally browses the web (see docs/DESIGN.md).

    Args:
        name: One of ``claude-code``, ``gemini``, ``ollama``.
        model: Optional model name/alias, passed through to both.
        gemini_api_key: API key, required when ``name`` is ``gemini``.
        ollama_base_url: Ollama's OpenAI-compatible endpoint.

    Returns:
        The constructed backend and researcher.

    Raises:
        ValueError: If ``name`` is unknown, or a required option is missing.
    """
    if name == "claude-code":
        if model:
            return ClaudeCodeCLIBackend(model=model), ClaudeCodeCLICompanyResearcher(model=model)
        return ClaudeCodeCLIBackend(), ClaudeCodeCLICompanyResearcher()
    if name == "gemini":
        if not gemini_api_key:
            raise ValueError(
                "--gemini-api-key (or GEMINI_API_KEY) is required for --backend gemini"
            )
        if model:
            return (
                GeminiBackend(api_key=gemini_api_key, model=model),
                build_gemini_researcher(api_key=gemini_api_key, model=model),
            )
        return (
            GeminiBackend(api_key=gemini_api_key),
            build_gemini_researcher(api_key=gemini_api_key),
        )
    if name == "ollama":
        if model:
            return (
                OllamaBackend(base_url=ollama_base_url, model=model),
                build_ollama_researcher(base_url=ollama_base_url, model=model),
            )
        return (
            OllamaBackend(base_url=ollama_base_url),
            build_ollama_researcher(base_url=ollama_base_url),
        )
    raise ValueError(f"unknown backend {name!r} (expected one of {', '.join(_BACKEND_NAMES)})")


def _resolve_job_posting(job_url: str | None, job_text_file: Path | None) -> JobPosting:
    """Fetch or read the job posting to tailor the CV to.

    Args:
        job_url: A LinkedIn job posting URL, or ``None``.
        job_text_file: Path to a text file with the job posting, or ``None``.
            Exactly one of ``job_url``/``job_text_file`` must be set.

    Returns:
        The job posting.

    Raises:
        ValueError: If neither or both of ``job_url``/``job_text_file`` are set.
        JobFetchError: If ``job_url`` could not be fetched or parsed.
        OSError: If ``job_text_file`` could not be read.
    """
    if job_url is not None:
        with default_http_client() as client:
            return LinkedInJobFetcher(client).fetch(job_url)
    if job_text_file is None:
        raise ValueError("one of job_url or job_text_file is required")
    text = job_text_file.read_text(encoding="utf-8")
    return JobPosting(title=job_text_file.stem, description=text)


@app.command()
def adapt(
    profile: Path = typer.Option(..., "--profile", help="Path to a .profile.md master profile."),
    base: Path = typer.Option(..., "--base", help="Base .cvml.yaml (used for person/contact)."),
    output: Path = typer.Option(..., "--output", "-o", help="Destination .cvml.yaml path."),
    job_url: str | None = typer.Option(None, "--job-url", help="LinkedIn job posting URL."),
    job_text_file: Path | None = typer.Option(
        None, "--job-text-file", help="Job posting text file, instead of --job-url."
    ),
    backend_name: str = typer.Option(
        "claude-code", "--backend", help="claude-code, gemini, or ollama."
    ),
    model: str | None = typer.Option(None, "--model", help="Model name/alias for the backend."),
    gemini_api_key: str | None = typer.Option(
        None, "--gemini-api-key", envvar="GEMINI_API_KEY", help="Required for --backend gemini."
    ),
    ollama_base_url: str = typer.Option(
        _DEFAULT_OLLAMA_BASE_URL, "--ollama-base-url", help="Ollama OpenAI-compatible endpoint."
    ),
) -> None:
    """Generate a CVML document tailored to a job posting.

    Runs the full agentic workflow: draft, then company research and fact-
    checking in parallel, then an editorial pass that reconciles both — see
    docs/DESIGN.md.
    """
    if (job_url is None) == (job_text_file is None):
        typer.echo("error: pass exactly one of --job-url or --job-text-file", err=True)
        raise typer.Exit(code=1)

    try:
        loaded_profile = load_profile(profile)
    except (ProfileSourceError, ProfileValidationError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        base_cv = load_cv(base)
    except (CVSourceError, CVValidationError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        job = _resolve_job_posting(job_url, job_text_file)
    except (JobFetchError, OSError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    try:
        backend, researcher = _build_agents(backend_name, model, gemini_api_key, ollama_base_url)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    workflow = CVWorkflow(
        CVAdapter(backend), researcher, LLMFactChecker(backend), LLMEditor(backend)
    )
    try:
        tailored = asyncio.run(workflow.run(loaded_profile, job, base_cv))
    except (BackendError, AdaptationError, StructuredOutputError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    dumped = yaml.safe_dump(
        tailored.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True
    )
    output.write_text(dumped, encoding="utf-8")
    typer.echo(f"wrote {output}")


if __name__ == "__main__":
    app()
