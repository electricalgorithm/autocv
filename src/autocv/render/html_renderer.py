"""HTML/CSS to PDF renderer, using Jinja2 templates and headless Chromium."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from autocv.markup.models import CV
from autocv.render.errors import RenderError
from autocv.render.formatting import format_date, format_month

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_DEFAULT_TEMPLATE = "default"

_FOOTER_TEMPLATE = """
<div style="width:100%; font-family:Arial, Helvetica, sans-serif; font-size:8.5pt;
            color:#333333; padding:0 20mm; display:flex; justify-content:space-between;">
  <span>{email}</span>
  <span><span class="pageNumber"></span> / <span class="totalPages"></span></span>
</div>
"""


def list_templates() -> list[str]:
    """List the names of every available CV template.

    A template is a subdirectory of ``templates/`` containing both
    ``cv.html.jinja`` and ``cv.css``.

    Returns:
        Template names, sorted alphabetically.
    """
    return sorted(
        entry.name
        for entry in _TEMPLATES_DIR.iterdir()
        if entry.is_dir() and (entry / "cv.html.jinja").is_file() and (entry / "cv.css").is_file()
    )


def _template_dir(template: str) -> Path:
    """Resolve a template name to its directory, validating it exists.

    Args:
        template: The template name.

    Returns:
        The template's directory.

    Raises:
        RenderError: If no such template exists.
    """
    template_dir = _TEMPLATES_DIR / template
    if not (template_dir / "cv.html.jinja").is_file():
        available = ", ".join(list_templates())
        raise RenderError(f"unknown template {template!r} (available: {available})")
    return template_dir


def _environment(template_dir: Path) -> Environment:
    """Build the Jinja2 environment used to render a CV template.

    Args:
        template_dir: Directory containing ``cv.html.jinja``.

    Returns:
        A configured Jinja2 environment.
    """
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    env.filters["format_month"] = format_month
    env.filters["format_date"] = format_date
    return env


def build_html(cv: CV, assets_dir: Path, template: str = _DEFAULT_TEMPLATE) -> str:
    """Render a CV to a standalone HTML document.

    This step has no browser dependency, so it can be unit tested on its own.

    Args:
        cv: The CV to render.
        assets_dir: Directory that relative asset paths (e.g.
            ``cv.person.photo``) are resolved against.
        template: Name of the template to render with (a subdirectory of
            ``templates/``); see ``list_templates``.

    Returns:
        The rendered HTML document.

    Raises:
        RenderError: If the template is unknown or a referenced asset (e.g.
            the photo) does not exist.
    """
    template_dir = _template_dir(template)

    photo_uri = None
    if cv.person.photo:
        photo_path = (assets_dir / cv.person.photo).resolve()
        if not photo_path.is_file():
            raise RenderError(f"photo not found: {photo_path}")
        mime_type, _ = mimetypes.guess_type(photo_path.name)
        encoded = base64.b64encode(photo_path.read_bytes()).decode("ascii")
        photo_uri = f"data:{mime_type or 'image/jpeg'};base64,{encoded}"

    css = (template_dir / "cv.css").read_text(encoding="utf-8")
    jinja_template = _environment(template_dir).get_template("cv.html.jinja")
    return jinja_template.render(cv=cv, css=css, photo_uri=photo_uri)


def _find_bundled_chromium() -> str | None:
    """Locate a pre-installed Chromium executable, if one is bundled.

    Playwright's default browser lookup expects an exact revision match.
    Some environments bundle a Chromium build under ``PLAYWRIGHT_BROWSERS_PATH``
    at a different revision, which this resolves directly.

    Returns:
        Path to a Chromium executable, or ``None`` to let Playwright decide.
    """
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not browsers_path:
        return None
    base = Path(browsers_path)
    if not base.is_dir():
        return None
    candidates = sorted(base.glob("chromium-*/chrome-linux/chrome"))
    return str(candidates[-1]) if candidates else None


class PlaywrightHTMLRenderer:
    """Renders a CV to PDF by printing an HTML/CSS template with Chromium."""

    def __init__(
        self, chromium_executable: str | None = None, template: str = _DEFAULT_TEMPLATE
    ) -> None:
        """Initialize the renderer.

        Args:
            chromium_executable: Path to a Chromium executable. Defaults to
                the bundled Chromium found via ``PLAYWRIGHT_BROWSERS_PATH``,
                falling back to Playwright's own resolution.
            template: Name of the template to render with; see
                ``list_templates``.
        """
        self._chromium_executable = chromium_executable or _find_bundled_chromium()
        self._template = template

    def render(self, cv: CV, output_path: Path, assets_dir: Path) -> Path:
        """Render a CV to a PDF file.

        Args:
            cv: The CV to render.
            output_path: Destination PDF path.
            assets_dir: Directory that relative asset paths are resolved
                against.

        Returns:
            ``output_path``.

        Raises:
            RenderError: If the template is unknown, a referenced asset is
                missing, or Chromium fails to render the document.
        """
        html = build_html(cv, assets_dir, self._template)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=self._chromium_executable)
                try:
                    page = browser.new_page()
                    page.set_content(html, wait_until="load")
                    page.pdf(
                        path=str(output_path),
                        format="A4",
                        print_background=True,
                        margin={
                            "top": "20mm",
                            "bottom": "16mm",
                            "left": "20mm",
                            "right": "20mm",
                        },
                        display_header_footer=True,
                        header_template="<span></span>",
                        footer_template=_FOOTER_TEMPLATE.format(email=cv.contact.email),
                    )
                finally:
                    browser.close()
        except PlaywrightError as exc:
            raise RenderError(f"failed to render CV to {output_path}: {exc}") from exc

        return output_path
