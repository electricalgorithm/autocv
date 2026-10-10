"""Unit tests for autocv.adapt.research."""

from __future__ import annotations

import subprocess

import pytest
from pydantic_ai.exceptions import AgentRunError
from pytest_mock import MockerFixture

from autocv.adapt.errors import ResearchError
from autocv.adapt.models import CompanyResearch
from autocv.adapt.research import (
    ClaudeCodeCLICompanyResearcher,
    PydanticAICompanyResearcher,
    build_gemini_researcher,
    build_ollama_researcher,
)
from autocv.jobs.models import JobPosting

_VALID_RESEARCH_YAML = """
summary: Builds developer infrastructure tools.
products:
  - Widget API
culture_notes:
  - Remote-first
sources:
  - https://example.com
"""


class TestClaudeCodeCLICompanyResearcher:
    """ClaudeCodeCLICompanyResearcher: subprocess with web tools allowed."""

    def test_allows_web_search_and_fetch(self, mocker: MockerFixture, job: JobPosting) -> None:
        run = mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=_VALID_RESEARCH_YAML, stderr=""
            ),
        )

        ClaudeCodeCLICompanyResearcher().research(job)

        command = run.call_args.args[0]
        assert command[command.index("--allowedTools") + 1] == "WebSearch WebFetch"

    def test_returns_parsed_research(self, mocker: MockerFixture, job: JobPosting) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=_VALID_RESEARCH_YAML, stderr=""
            ),
        )

        research = ClaudeCodeCLICompanyResearcher().research(job)

        assert research.summary == "Builds developer infrastructure tools."
        assert research.products == ["Widget API"]

    def test_backend_failure_raises_research_error(
        self, mocker: MockerFixture, job: JobPosting
    ) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            side_effect=FileNotFoundError("no such file"),
        )
        with pytest.raises(ResearchError):
            ClaudeCodeCLICompanyResearcher().research(job)

    def test_invalid_output_raises_research_error(
        self, mocker: MockerFixture, job: JobPosting
    ) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="not: [valid", stderr=""
            ),
        )
        with pytest.raises(ResearchError):
            ClaudeCodeCLICompanyResearcher().research(job)


class _StubResult:
    def __init__(self, output: CompanyResearch) -> None:
        self.output = output


class TestPydanticAICompanyResearcher:
    """PydanticAICompanyResearcher: pydantic-ai Agent with web capabilities."""

    def test_returns_agent_output(self, mocker: MockerFixture, job: JobPosting) -> None:
        agent_cls = mocker.patch("autocv.adapt.research.Agent")
        expected = CompanyResearch(summary="Builds developer tools.")
        agent_cls.return_value.run_sync.return_value = _StubResult(expected)

        researcher = PydanticAICompanyResearcher(mocker.Mock())
        result = researcher.research(job)

        assert result == expected
        agent_cls.return_value.run_sync.assert_called_once()

    def test_wraps_agent_run_error(self, mocker: MockerFixture, job: JobPosting) -> None:
        agent_cls = mocker.patch("autocv.adapt.research.Agent")
        agent_cls.return_value.run_sync.side_effect = AgentRunError("boom")

        researcher = PydanticAICompanyResearcher(mocker.Mock())
        with pytest.raises(ResearchError):
            researcher.research(job)

    def test_configures_web_search_and_fetch_capabilities(self, mocker: MockerFixture) -> None:
        agent_cls = mocker.patch("autocv.adapt.research.Agent")

        PydanticAICompanyResearcher(mocker.Mock())

        capabilities = agent_cls.call_args.kwargs["capabilities"]
        assert len(capabilities) == 2


class TestResearcherFactories:
    """build_gemini_researcher / build_ollama_researcher."""

    def test_build_gemini_researcher_returns_pydantic_ai_researcher(self) -> None:
        researcher = build_gemini_researcher(api_key="key")
        assert isinstance(researcher, PydanticAICompanyResearcher)

    def test_build_ollama_researcher_returns_pydantic_ai_researcher(self) -> None:
        researcher = build_ollama_researcher()
        assert isinstance(researcher, PydanticAICompanyResearcher)
