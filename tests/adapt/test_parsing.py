"""Unit tests for autocv.adapt.parsing."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from autocv.adapt.errors import StructuredOutputError
from autocv.adapt.parsing import parse_yaml_model, strip_code_fence


class _Widget(BaseModel):
    name: str
    count: int = 0


class TestStripCodeFence:
    """strip_code_fence: removing an optional Markdown code fence."""

    def test_leaves_plain_text_unchanged(self) -> None:
        assert strip_code_fence("a: 1\nb: 2") == "a: 1\nb: 2"

    def test_strips_fence_with_language_tag(self) -> None:
        assert strip_code_fence("```yaml\na: 1\n```") == "a: 1"

    def test_strips_fence_without_language_tag(self) -> None:
        assert strip_code_fence("```\na: 1\n```") == "a: 1"

    def test_strips_unclosed_fence_opening_line_only(self) -> None:
        assert strip_code_fence("```yaml\na: 1") == "a: 1"

    def test_trims_surrounding_whitespace(self) -> None:
        assert strip_code_fence("  a: 1  \n") == "a: 1"


class TestParseYamlModel:
    """parse_yaml_model: backend text to a validated Pydantic model."""

    def test_parses_valid_yaml(self) -> None:
        widget = parse_yaml_model("name: gadget\ncount: 3", _Widget)
        assert widget == _Widget(name="gadget", count=3)

    def test_parses_yaml_wrapped_in_code_fence(self) -> None:
        widget = parse_yaml_model("```yaml\nname: gadget\n```", _Widget)
        assert widget.name == "gadget"

    def test_rejects_malformed_yaml(self) -> None:
        with pytest.raises(StructuredOutputError, match="not valid YAML"):
            parse_yaml_model("name: [unclosed", _Widget)

    def test_rejects_non_mapping_yaml(self) -> None:
        with pytest.raises(StructuredOutputError, match="not a YAML mapping"):
            parse_yaml_model("- one\n- two", _Widget)

    def test_rejects_schema_violation(self) -> None:
        with pytest.raises(StructuredOutputError, match="_Widget"):
            parse_yaml_model("count: 3", _Widget)
