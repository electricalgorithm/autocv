"""Unit tests for autocv.markup.parser."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from autocv.markup.errors import CVSourceError, CVValidationError
from autocv.markup.parser import YAMLCVSource, load_cv


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


class TestYAMLCVSource:
    """YAMLCVSource: loads and validates a CVML file from disk."""

    def test_loads_valid_document(self, tmp_path: Path, minimal_cv_data: dict[str, Any]) -> None:
        path = _write_yaml(tmp_path / "cv.cvml.yaml", minimal_cv_data)
        cv = YAMLCVSource(path).load()
        assert cv.person.name == "Ada Lovelace"

    def test_missing_file_raises_source_error(self, tmp_path: Path) -> None:
        with pytest.raises(CVSourceError):
            YAMLCVSource(tmp_path / "missing.cvml.yaml").load()

    def test_malformed_yaml_raises_source_error(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.cvml.yaml"
        path.write_text("person: [unclosed", encoding="utf-8")
        with pytest.raises(CVSourceError):
            YAMLCVSource(path).load()

    def test_non_mapping_document_raises_source_error(self, tmp_path: Path) -> None:
        path = tmp_path / "list.cvml.yaml"
        path.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(CVSourceError):
            YAMLCVSource(path).load()

    def test_schema_violation_raises_validation_error(
        self, tmp_path: Path, minimal_cv_data: dict[str, Any]
    ) -> None:
        del minimal_cv_data["summary"]
        path = _write_yaml(tmp_path / "cv.cvml.yaml", minimal_cv_data)
        with pytest.raises(CVValidationError):
            YAMLCVSource(path).load()


class TestLoadCv:
    """load_cv: module-level convenience wrapper."""

    def test_loads_valid_document(self, tmp_path: Path, full_cv_data: dict[str, Any]) -> None:
        path = _write_yaml(tmp_path / "cv.cvml.yaml", full_cv_data)
        cv = load_cv(path)
        assert len(cv.experience) == 1
