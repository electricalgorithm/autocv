"""Loading master profile documents into validated MasterProfile objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from autocv.profile.errors import ProfileSourceError, ProfileValidationError
from autocv.profile.models import MasterProfile

_SECTION_TITLE_FIELD = {
    "experience": "title",
    "education": "degree",
    "publications": "title",
    "projects": "title",
}
_SECTION_LIST_FIELDS = {
    "experience": {"keywords"},
    "education": set(),
    "publications": set(),
    "projects": {"categories", "stack"},
}
_FLAT_LIST_SECTIONS = {"skills", "certifications"}
_KNOWN_SECTIONS = {"experience", "education", "publications", "projects", *_FLAT_LIST_SECTIONS}


class ProfileSource(Protocol):
    """A source that produces a validated master profile.

    Implementations may load from a file or any other origin; callers only
    depend on this protocol so the origin can change without touching the
    adapter.
    """

    def load(self) -> MasterProfile:
        """Load and validate a master profile.

        Returns:
            The validated master profile.

        Raises:
            ProfileSourceError: If the underlying data cannot be read or
                parsed.
            ProfileValidationError: If the data does not satisfy the
                master profile schema.
        """
        ...


def _normalize_key(raw: str) -> str:
    """Turn a metadata label into a model field name.

    Args:
        raw: The label as written, e.g. ``"Organization URL"``.

    Returns:
        The normalized field name, e.g. ``"organization_url"``.
    """
    return raw.strip().lower().replace(" ", "_")


def _split_list(value: str) -> list[str]:
    """Split a comma-separated metadata value into a list.

    Args:
        value: A comma-separated string.

    Returns:
        The trimmed, non-empty items.
    """
    return [item.strip() for item in value.split(",") if item.strip()]


class _Entry:
    """An in-progress ``### `` entry being accumulated during parsing."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.meta: dict[str, str] = {}
        self.achievements: list[str] = []
        self.collecting_achievements = False

    def to_data(self, section: str) -> dict[str, Any]:
        """Build the model-constructor kwargs for this entry.

        Args:
            section: The section this entry belongs to.

        Returns:
            A dict suitable for ``MasterProfile.model_validate``.
        """
        data: dict[str, Any] = {_SECTION_TITLE_FIELD[section]: self.title, **self.meta}
        for key in _SECTION_LIST_FIELDS[section]:
            if key in data:
                data[key] = _split_list(data[key])
        if self.achievements:
            data["achievements"] = self.achievements
        return data


class _ProfileParser:
    """Line-by-line state machine implementing the master profile grammar."""

    def __init__(self) -> None:
        self.section: str | None = None
        self.entries: dict[str, list[_Entry]] = {name: [] for name in _SECTION_TITLE_FIELD}
        self.flat_lists: dict[str, list[str]] = {name: [] for name in _FLAT_LIST_SECTIONS}
        self.current: _Entry | None = None

    def parse(self, text: str) -> MasterProfile:
        """Parse a document and validate the result.

        Args:
            text: The document text.

        Returns:
            The validated master profile.

        Raises:
            ProfileSourceError: If the document does not follow the grammar.
            ProfileValidationError: If the parsed data does not satisfy the
                master profile schema.
        """
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line:
                self._handle_line(line)
        self._finalize_entry()
        return self._build_model()

    def _handle_line(self, line: str) -> None:
        if line.startswith("### "):
            self._handle_entry_heading(line)
        elif line.startswith("## "):
            self._handle_section_heading(line)
        elif line.lower().rstrip(":") == "achievements":
            self._handle_achievements_marker()
        elif line.startswith("- "):
            self._handle_bullet(line)
        elif line.startswith("#"):
            self._finalize_entry()
        else:
            raise ProfileSourceError(f"unrecognized line: {line!r}")

    def _handle_entry_heading(self, line: str) -> None:
        if self.section is None or self.section not in _SECTION_TITLE_FIELD:
            raise ProfileSourceError(f"'### ' heading outside a supported section: {line!r}")
        self._finalize_entry()
        self.current = _Entry(line.removeprefix("### ").strip())

    def _handle_section_heading(self, line: str) -> None:
        self._finalize_entry()
        label = line.removeprefix("## ").strip()
        name = _normalize_key(label)
        if name not in _KNOWN_SECTIONS:
            raise ProfileSourceError(f"unknown section: {label!r}")
        self.section = name

    def _handle_achievements_marker(self) -> None:
        if self.current is None:
            raise ProfileSourceError("'Achievements:' outside an entry")
        self.current.collecting_achievements = True

    def _handle_bullet(self, line: str) -> None:
        item = line.removeprefix("- ").strip()
        if self.section in _FLAT_LIST_SECTIONS:
            self.flat_lists[self.section].append(item)
            return
        if self.current is None:
            raise ProfileSourceError(f"'- ' item outside an entry: {line!r}")
        if self.current.collecting_achievements:
            self.current.achievements.append(item)
            return
        if ":" not in item:
            raise ProfileSourceError(f"malformed metadata line: {line!r}")
        key, _, value = item.partition(":")
        self.current.meta[_normalize_key(key)] = value.strip()

    def _finalize_entry(self) -> None:
        if self.current is not None and self.section is not None:
            self.entries[self.section].append(self.current)
        self.current = None

    def _build_model(self) -> MasterProfile:
        raw_data: dict[str, Any] = {
            section_name: [entry.to_data(section_name) for entry in section_entries]
            for section_name, section_entries in self.entries.items()
        }
        raw_data.update(self.flat_lists)
        try:
            return MasterProfile.model_validate(raw_data)
        except ValidationError as exc:
            raise ProfileValidationError(
                f"master profile does not satisfy the schema: {exc}"
            ) from exc


def parse_master_profile(text: str) -> MasterProfile:
    """Parse a master profile document, per docs/MASTER_PROFILE_SPEC.md.

    Args:
        text: The document text.

    Returns:
        The validated master profile.

    Raises:
        ProfileSourceError: If the document does not follow the grammar.
        ProfileValidationError: If the parsed data does not satisfy the
            master profile schema.
    """
    return _ProfileParser().parse(text)


class MarkdownProfileSource:
    """Loads a master profile document from a Markdown file on disk."""

    def __init__(self, path: Path) -> None:
        """Initialize the source.

        Args:
            path: Path to a ``.profile.md`` file.
        """
        self._path = path

    def load(self) -> MasterProfile:
        """Read, parse, and validate the master profile file.

        Returns:
            The validated master profile.

        Raises:
            ProfileSourceError: If the file is missing, unreadable, or does
                not follow the master profile grammar.
            ProfileValidationError: If the parsed data does not satisfy the
                master profile schema.
        """
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProfileSourceError(f"cannot read {self._path}: {exc}") from exc
        return parse_master_profile(text)


def load_profile(path: Path) -> MasterProfile:
    """Load a master profile file.

    Args:
        path: Path to a ``.profile.md`` file.

    Returns:
        The validated master profile.

    Raises:
        ProfileSourceError: If the file cannot be read or parsed.
        ProfileValidationError: If the data does not satisfy the schema.
    """
    return MarkdownProfileSource(path).load()
