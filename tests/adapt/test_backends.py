"""Unit tests for autocv.adapt.backends."""

from __future__ import annotations

import subprocess

import pytest
from pydantic_ai.exceptions import AgentRunError
from pytest_mock import MockerFixture

from autocv.adapt.backends import ClaudeCodeCLIBackend, GeminiBackend, OllamaBackend
from autocv.adapt.errors import BackendError


class TestClaudeCodeCLIBackend:
    """ClaudeCodeCLIBackend: shells out to the `claude` CLI."""

    def test_returns_stripped_stdout(self, mocker: MockerFixture) -> None:
        run = mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="  hello\n", stderr=""
            ),
        )

        output = ClaudeCodeCLIBackend().generate("system", "user")

        assert output == "hello"
        command = run.call_args.args[0]
        assert command[0] == "claude"
        assert "--system-prompt" in command
        assert command[command.index("--system-prompt") + 1] == "system"
        assert run.call_args.kwargs["input"] == "user"

    def test_passes_model_through(self, mocker: MockerFixture) -> None:
        run = mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr=""),
        )

        ClaudeCodeCLIBackend(model="sonnet").generate("system", "user")

        command = run.call_args.args[0]
        assert command[command.index("--model") + 1] == "sonnet"

    def test_omits_allowed_tools_by_default(self, mocker: MockerFixture) -> None:
        run = mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr=""),
        )

        ClaudeCodeCLIBackend().generate("system", "user")

        assert "--allowedTools" not in run.call_args.args[0]

    def test_passes_allowed_tools_through(self, mocker: MockerFixture) -> None:
        run = mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr=""),
        )

        ClaudeCodeCLIBackend(allowed_tools="WebSearch WebFetch").generate("system", "user")

        command = run.call_args.args[0]
        assert command[command.index("--allowedTools") + 1] == "WebSearch WebFetch"

    def test_missing_executable_raises_backend_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            side_effect=FileNotFoundError("no such file"),
        )
        with pytest.raises(BackendError, match="failed to run"):
            ClaudeCodeCLIBackend().generate("system", "user")

    def test_timeout_raises_backend_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=1.0),
        )
        with pytest.raises(BackendError, match="timed out"):
            ClaudeCodeCLIBackend().generate("system", "user")

    def test_nonzero_exit_raises_backend_error_with_stderr(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="auth error"
            ),
        )
        with pytest.raises(BackendError, match="auth error"):
            ClaudeCodeCLIBackend().generate("system", "user")

    def test_empty_output_raises_backend_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "autocv.adapt.backends.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="   ", stderr=""
            ),
        )
        with pytest.raises(BackendError, match="no output"):
            ClaudeCodeCLIBackend().generate("system", "user")


class _StubResult:
    def __init__(self, output: str) -> None:
        self.output = output


class TestGeminiBackend:
    """GeminiBackend: pydantic-ai Agent wired to the Gemini provider."""

    def test_returns_agent_output(self, mocker: MockerFixture) -> None:
        agent_cls = mocker.patch("autocv.adapt.backends.Agent")
        agent_cls.return_value.run_sync.return_value = _StubResult("generated cvml")

        output = GeminiBackend(api_key="key").generate("system", "user")

        assert output == "generated cvml"
        agent_cls.return_value.run_sync.assert_called_once_with("user")

    def test_wraps_agent_run_error(self, mocker: MockerFixture) -> None:
        agent_cls = mocker.patch("autocv.adapt.backends.Agent")
        agent_cls.return_value.run_sync.side_effect = AgentRunError("boom")

        with pytest.raises(BackendError, match="Gemini request failed"):
            GeminiBackend(api_key="key").generate("system", "user")


class TestOllamaBackend:
    """OllamaBackend: pydantic-ai Agent wired to a local OpenAI-compatible server."""

    def test_returns_agent_output(self, mocker: MockerFixture) -> None:
        agent_cls = mocker.patch("autocv.adapt.backends.Agent")
        agent_cls.return_value.run_sync.return_value = _StubResult("generated cvml")

        output = OllamaBackend().generate("system", "user")

        assert output == "generated cvml"

    def test_wraps_agent_run_error(self, mocker: MockerFixture) -> None:
        agent_cls = mocker.patch("autocv.adapt.backends.Agent")
        agent_cls.return_value.run_sync.side_effect = AgentRunError("boom")

        with pytest.raises(BackendError, match="Ollama request failed"):
            OllamaBackend().generate("system", "user")
