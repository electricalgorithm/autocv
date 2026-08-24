"""Renderer protocol: turning a validated CV into a document."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from autocv.markup.models import CV


class CVRenderer(Protocol):
    """Renders a CV to a document on disk."""

    def render(self, cv: CV, output_path: Path, assets_dir: Path) -> Path:
        """Render a CV.

        Args:
            cv: The CV to render.
            output_path: Destination file path.
            assets_dir: Directory that relative asset paths (e.g.
                ``cv.person.photo``) are resolved against — typically the
                directory containing the source CVML file.

        Returns:
            ``output_path``, for chaining.

        Raises:
            RenderError: If rendering fails.
        """
        ...
