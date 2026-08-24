"""Loading CVML documents into validated CV objects."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import yaml
from pydantic import ValidationError

from autocv.markup.errors import CVSourceError, CVValidationError
from autocv.markup.models import CV


class CVSource(Protocol):
    """A source that produces a validated CV.

    Implementations may load from a file, a database, or any other origin;
    callers only depend on this protocol so the origin can change without
    touching the renderer or the adapter.
    """

    def load(self) -> CV:
        """Load and validate a CV.

        Returns:
            The validated CV.

        Raises:
            CVSourceError: If the underlying data cannot be read or parsed.
            CVValidationError: If the data does not satisfy the CV schema.
        """
        ...


class YAMLCVSource:
    """Loads a CVML document from a YAML file on disk."""

    def __init__(self, path: Path) -> None:
        """Initialize the source.

        Args:
            path: Path to a ``.cvml.yaml`` file.
        """
        self._path = path

    def load(self) -> CV:
        """Read, parse, and validate the CVML file.

        Returns:
            The validated CV.

        Raises:
            CVSourceError: If the file is missing, unreadable, not valid YAML,
                or does not decode to a mapping.
            CVValidationError: If the parsed data does not satisfy the CV
                schema.
        """
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CVSourceError(f"cannot read {self._path}: {exc}") from exc

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise CVSourceError(f"invalid YAML in {self._path}: {exc}") from exc

        if not isinstance(data, dict):
            raise CVSourceError(f"{self._path} must contain a YAML mapping at the top level")

        try:
            return CV.model_validate(data)
        except ValidationError as exc:
            raise CVValidationError(f"{self._path} does not satisfy the CV schema: {exc}") from exc


def load_cv(path: Path) -> CV:
    """Load a CVML file.

    Args:
        path: Path to a ``.cvml.yaml`` file.

    Returns:
        The validated CV.

    Raises:
        CVSourceError: If the file cannot be read or parsed.
        CVValidationError: If the data does not satisfy the CV schema.
    """
    return YAMLCVSource(path).load()
