"""LLM backends: generating raw text from a system+user prompt pair.

Every provider — a local CLI, a hosted API, a self-hosted model — reduces to
the same shape: send a system prompt and a user prompt, get text back. The
generator (autocv.adapt.generator) is responsible for parsing and validating
that text as CVML; backends never see the CV schema.
"""

from __future__ import annotations

import subprocess
from typing import Protocol

from pydantic_ai import Agent
from pydantic_ai.exceptions import AgentRunError, UserError
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from autocv.adapt.errors import BackendError

_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_DEFAULT_OLLAMA_MODEL = "llama3.1"
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"


class MarkupGenerationBackend(Protocol):
    """Generates raw text from a system+user prompt pair."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text.

        Args:
            system_prompt: Instructions and constraints for the model.
            user_prompt: The task-specific content (job posting, profile).

        Returns:
            The model's raw text response.

        Raises:
            BackendError: If the backend fails to produce a response.
        """
        ...


class ClaudeCodeCLIBackend:
    """Generates text via a local Claude Code CLI subprocess.

    For users with a Claude Code subscription rather than a standalone API
    key: shells out to the ``claude`` binary already authenticated on this
    machine, instead of making a direct API call.
    """

    def __init__(
        self,
        executable: str = "claude",
        model: str | None = None,
        timeout: float = 300.0,
        allowed_tools: str | None = None,
    ) -> None:
        """Initialize the backend.

        Args:
            executable: Name or path of the Claude Code CLI binary.
            model: Optional model alias/name to pass through (e.g. "sonnet").
            timeout: Seconds to wait for the subprocess before giving up.
            allowed_tools: Space/comma-separated tool names to pre-approve
                (e.g. ``"WebSearch WebFetch"``). Non-interactive `-p` mode
                auto-denies any tool not pre-approved, so every plain-text
                generation call is tool-free by default; pass this only for
                a role that genuinely needs a tool, such as company research.
        """
        self._executable = executable
        self._model = model
        self._timeout = timeout
        self._allowed_tools = allowed_tools

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text by piping the user prompt into ``claude -p``.

        Args:
            system_prompt: Passed via ``--system-prompt``.
            user_prompt: Piped to the subprocess's stdin.

        Returns:
            The CLI's stdout, stripped.

        Raises:
            BackendError: If the binary is missing, times out, exits
                non-zero, or produces no output.
        """
        command = [
            self._executable,
            "-p",
            "--output-format",
            "text",
            "--system-prompt",
            system_prompt,
        ]
        if self._model:
            command += ["--model", self._model]
        if self._allowed_tools:
            command += ["--allowedTools", self._allowed_tools]

        try:
            result = subprocess.run(  # noqa: S603 - fixed argv, no shell
                command,
                input=user_prompt,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except OSError as exc:
            raise BackendError(f"failed to run '{self._executable}': {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise BackendError(f"'{self._executable}' timed out after {self._timeout}s") from exc

        if result.returncode != 0:
            raise BackendError(
                f"'{self._executable}' exited with code {result.returncode}: "
                f"{result.stderr.strip()}"
            )

        output = result.stdout.strip()
        if not output:
            raise BackendError(f"'{self._executable}' produced no output")
        return output


class GeminiBackend:
    """Generates text via the Gemini API."""

    def __init__(self, api_key: str, model: str = _DEFAULT_GEMINI_MODEL) -> None:
        """Initialize the backend.

        Args:
            api_key: Gemini API key.
            model: Gemini model name.
        """
        self._model_name = model
        self._provider = GoogleProvider(api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text via the Gemini API.

        Args:
            system_prompt: The agent's system prompt for this call.
            user_prompt: The user message.

        Returns:
            The model's text response.

        Raises:
            BackendError: If the request fails or the backend is misconfigured.
        """
        agent = Agent(
            GoogleModel(self._model_name, provider=self._provider), system_prompt=system_prompt
        )
        try:
            result = agent.run_sync(user_prompt)
        except (AgentRunError, UserError) as exc:
            raise BackendError(f"Gemini request failed: {exc}") from exc
        return result.output


class OllamaBackend:
    """Generates text via a local Ollama server's OpenAI-compatible API."""

    def __init__(
        self,
        model: str = _DEFAULT_OLLAMA_MODEL,
        base_url: str = _DEFAULT_OLLAMA_BASE_URL,
    ) -> None:
        """Initialize the backend.

        Args:
            model: Ollama model name (must already be pulled).
            base_url: Ollama's OpenAI-compatible endpoint.
        """
        self._model_name = model
        self._provider = OpenAIProvider(base_url=base_url, api_key="ollama")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text via Ollama.

        Args:
            system_prompt: The agent's system prompt for this call.
            user_prompt: The user message.

        Returns:
            The model's text response.

        Raises:
            BackendError: If the request fails or the backend is misconfigured.
        """
        agent = Agent(
            OpenAIChatModel(self._model_name, provider=self._provider),
            system_prompt=system_prompt,
        )
        try:
            result = agent.run_sync(user_prompt)
        except (AgentRunError, UserError) as exc:
            raise BackendError(f"Ollama request failed: {exc}") from exc
        return result.output
