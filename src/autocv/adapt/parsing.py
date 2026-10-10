"""Shared text-parsing helpers for LLM backend output.

Every agent in the adaptation workflow (draft, research, fact-check,
editorial) asks its backend for a YAML document and validates it against a
Pydantic model; this module is that one shared step.
"""

from __future__ import annotations

import yaml
from pydantic import BaseModel, ValidationError

from autocv.adapt.errors import StructuredOutputError


def strip_code_fence(text: str) -> str:
    """Strip a leading/trailing Markdown code fence, if present.

    Backends are instructed not to add one, but models sometimes do anyway.

    Args:
        text: Raw backend output.

    Returns:
        The text with a surrounding ```-fence removed, if there was one.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    has_closing_fence = len(lines) > 1 and lines[-1].strip() == "```"
    lines = lines[1:-1] if has_closing_fence else lines[1:]
    return "\n".join(lines)


def parse_yaml_model[ModelT: BaseModel](text: str, model_type: type[ModelT]) -> ModelT:
    """Parse backend text as YAML and validate it against ``model_type``.

    Args:
        text: Raw backend output, expected to be a YAML document.
        model_type: The Pydantic model to validate against.

    Returns:
        The validated model instance.

    Raises:
        StructuredOutputError: If the text is not valid YAML, not a mapping,
            or does not satisfy ``model_type``.
    """
    cleaned = strip_code_fence(text)
    try:
        data = yaml.safe_load(cleaned)
    except yaml.YAMLError as exc:
        raise StructuredOutputError(f"backend output is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise StructuredOutputError("backend output is not a YAML mapping")
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise StructuredOutputError(
            f"backend output does not satisfy {model_type.__name__}: {exc}"
        ) from exc
