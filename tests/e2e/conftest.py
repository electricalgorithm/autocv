"""Shared fixtures for system-level (end-to-end) tests."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

import pytest
from pytest_mock import MockerFixture

# Unique opening lines from each agent's system prompt (autocv.adapt.prompts),
# used to route a mocked `claude` subprocess call to the right scripted
# response without depending on prompt internals beyond this one line.
DRAFT_MARKER = "You are tailoring a CV to a specific job posting."
RESEARCH_MARKER = "You are researching the company behind a job posting"
FACT_CHECK_MARKER = "You are fact-checking a draft CV"
EDITORIAL_MARKER = "You are the final editor for a tailored CV."

RouteResponse = str | Callable[[str, str], str]


def route_by_role(
    routes: dict[str, RouteResponse],
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Build a `subprocess.run` side effect that routes by agent role.

    Args:
        routes: Maps a role marker (e.g. ``DRAFT_MARKER``) to either a fixed
            YAML response, or a ``(system_prompt, user_prompt) -> str``
            callable for a response that depends on the call.

    Returns:
        A function usable as ``subprocess.run``'s ``side_effect``.
    """

    def handler(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        system_prompt = command[command.index("--system-prompt") + 1]
        user_prompt = str(kwargs.get("input", ""))
        for marker, response in routes.items():
            if marker in system_prompt:
                stdout = response(system_prompt, user_prompt) if callable(response) else response
                return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
        raise AssertionError(f"no route matched this system prompt: {system_prompt[:200]!r}")

    return handler


@pytest.fixture
def mock_claude(mocker: MockerFixture) -> Callable[[dict[str, RouteResponse]], None]:
    """Mock every `claude` subprocess call for the duration of a test.

    Returns:
        A function that installs the mock given a role-to-response mapping;
        call it with the routes for the scenario under test.
    """

    def install(routes: dict[str, RouteResponse]) -> None:
        mocker.patch("autocv.adapt.backends.subprocess.run", side_effect=route_by_role(routes))

    return install
