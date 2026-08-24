"""Company research agent: what a hiring company builds, sells, and values.

Every implementation lets the backend actually browse the web rather than
recall prior knowledge — see docs/DESIGN.md for why each provider gets a
different mechanism for that.
"""

from __future__ import annotations

from typing import Protocol

from pydantic_ai import Agent
from pydantic_ai.capabilities import WebFetch, WebSearch
from pydantic_ai.exceptions import AgentRunError, UserError
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from autocv.adapt.backends import ClaudeCodeCLIBackend
from autocv.adapt.errors import BackendError, ResearchError, StructuredOutputError
from autocv.adapt.models import CompanyResearch
from autocv.adapt.parsing import parse_yaml_model
from autocv.adapt.prompts import build_research_system_prompt, build_research_user_prompt
from autocv.jobs.models import JobPosting

_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_DEFAULT_OLLAMA_MODEL = "llama3.1"
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
_CLAUDE_CODE_RESEARCH_TOOLS = "WebSearch WebFetch"


class CompanyResearcher(Protocol):
    """Gathers findings about the company behind a job posting."""

    def research(self, job: JobPosting) -> CompanyResearch:
        """Research the hiring company.

        Args:
            job: The job posting naming the company to research.

        Returns:
            The research findings.

        Raises:
            ResearchError: If research fails outright.
        """
        ...


class ClaudeCodeCLICompanyResearcher:
    """Researches a company via a Claude Code CLI subprocess.

    Unlike the plain-text roles (draft, fact-check, editorial), this one
    needs `WebSearch`/`WebFetch` explicitly allowed — see
    `ClaudeCodeCLIBackend.__init__`.
    """

    def __init__(
        self, executable: str = "claude", model: str | None = None, timeout: float = 300.0
    ) -> None:
        """Initialize the researcher.

        Args:
            executable: Name or path of the Claude Code CLI binary.
            model: Optional model alias/name to pass through.
            timeout: Seconds to wait for the subprocess before giving up.
        """
        self._backend = ClaudeCodeCLIBackend(
            executable=executable,
            model=model,
            timeout=timeout,
            allowed_tools=_CLAUDE_CODE_RESEARCH_TOOLS,
        )

    def research(self, job: JobPosting) -> CompanyResearch:
        """Research the hiring company via the `claude` CLI's web tools.

        Args:
            job: The job posting naming the company to research.

        Returns:
            The research findings.

        Raises:
            ResearchError: If the subprocess fails or its output is invalid.
        """
        try:
            text = self._backend.generate(
                build_research_system_prompt(), build_research_user_prompt(job)
            )
        except BackendError as exc:
            raise ResearchError(f"company research failed: {exc}") from exc
        try:
            return parse_yaml_model(text, CompanyResearch)
        except StructuredOutputError as exc:
            raise ResearchError(f"company research output was invalid: {exc}") from exc


class PydanticAICompanyResearcher:
    """Researches a company via a pydantic-ai Agent.

    Uses each provider's native web search/fetch where supported (e.g.
    Gemini's server-side search grounding), falling back to a local
    DuckDuckGo search and a plain HTTP fetch (markdownify-cleaned) for
    models with no native support (e.g. a local Ollama model) — so every
    model gets at least the local fallback, and better where available.
    """

    def __init__(self, model: Model) -> None:
        """Initialize the researcher.

        Args:
            model: The pydantic-ai model to research with.
        """
        self._agent = Agent(
            model,
            output_type=CompanyResearch,
            system_prompt=build_research_system_prompt(),
            capabilities=[WebSearch(local="duckduckgo"), WebFetch(local=True)],
        )

    def research(self, job: JobPosting) -> CompanyResearch:
        """Research the hiring company.

        Args:
            job: The job posting naming the company to research.

        Returns:
            The research findings.

        Raises:
            ResearchError: If the request fails or the backend is
                misconfigured.
        """
        try:
            result = self._agent.run_sync(build_research_user_prompt(job))
        except (AgentRunError, UserError) as exc:
            raise ResearchError(f"company research failed: {exc}") from exc
        return result.output


def build_gemini_researcher(
    api_key: str, model: str = _DEFAULT_GEMINI_MODEL
) -> PydanticAICompanyResearcher:
    """Build a company researcher backed by the Gemini API.

    Args:
        api_key: Gemini API key.
        model: Gemini model name.

    Returns:
        The researcher.
    """
    return PydanticAICompanyResearcher(GoogleModel(model, provider=GoogleProvider(api_key=api_key)))


def build_ollama_researcher(
    model: str = _DEFAULT_OLLAMA_MODEL, base_url: str = _DEFAULT_OLLAMA_BASE_URL
) -> PydanticAICompanyResearcher:
    """Build a company researcher backed by a local Ollama server.

    Args:
        model: Ollama model name (must already be pulled).
        base_url: Ollama's OpenAI-compatible endpoint.

    Returns:
        The researcher.
    """
    provider = OpenAIProvider(base_url=base_url, api_key="ollama")
    return PydanticAICompanyResearcher(OpenAIChatModel(model, provider=provider))
