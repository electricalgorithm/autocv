"""Unit tests for autocv.render.html_renderer."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocv.markup.models import CV
from autocv.render.errors import RenderError
from autocv.render.html_renderer import PlaywrightHTMLRenderer, build_html, list_templates

_TEMPLATES = ("default", "compact")


class TestListTemplates:
    """list_templates: discovering available CV templates."""

    def test_includes_default_and_compact(self) -> None:
        assert list_templates() == ["compact", "default"]


class TestBuildHtml:
    """build_html: pure HTML rendering, no browser dependency."""

    def test_includes_person_and_summary(self, cv: CV, assets_dir: Path) -> None:
        html = build_html(cv, assets_dir)
        assert "Ada Lovelace" in html
        assert "A pioneering software engineer." in html

    @pytest.mark.parametrize("template", _TEMPLATES)
    def test_includes_scholar_link(self, cv: CV, assets_dir: Path, template: str) -> None:
        html = build_html(cv, assets_dir, template=template)
        assert "https://scholar.google.com/citations?user=adalovelace" in html

    @pytest.mark.parametrize("template", _TEMPLATES)
    def test_links_linkedin_github_and_website(
        self, cv: CV, assets_dir: Path, template: str
    ) -> None:
        html = build_html(cv, assets_dir, template=template)
        assert 'href="https://www.linkedin.com/in/adalovelace"' in html
        assert 'href="https://github.com/adalovelace"' in html
        assert 'href="https://ada.example.com"' in html

    @pytest.mark.parametrize("template", _TEMPLATES)
    def test_renders_experience_highlights_as_list(
        self, cv_data: dict[str, object], assets_dir: Path, template: str
    ) -> None:
        experience = cv_data["experience"]
        assert isinstance(experience, list)
        experience[0]["highlights"] = ["Shipped the thing.", "Cut latency by 40%."]
        html = build_html(CV.model_validate(cv_data), assets_dir, template=template)
        assert "<li>Shipped the thing.</li>" in html
        assert "<li>Cut latency by 40%.</li>" in html

    @pytest.mark.parametrize("template", _TEMPLATES)
    def test_includes_every_populated_section_heading(
        self, cv: CV, assets_dir: Path, template: str
    ) -> None:
        html = build_html(cv, assets_dir, template=template)
        for heading in (
            "Professional Experience",
            "Education",
            "Skills",
            "Certifications",
            "Publications",
            "Open Source Projects",
            "References",
            "Languages",
        ):
            assert heading in html

    def test_unknown_template_raises_render_error(self, cv: CV, assets_dir: Path) -> None:
        with pytest.raises(RenderError, match="unknown template"):
            build_html(cv, assets_dir, template="does-not-exist")

    def test_omits_heading_for_empty_section(self, minimal_cv_data: dict[str, object]) -> None:
        cv = CV.model_validate(minimal_cv_data)
        html = build_html(cv, Path())
        assert "Publications" not in html
        assert "Open Source Projects" not in html

    def test_missing_photo_raises_render_error(
        self, cv_data: dict[str, object], tmp_path: Path
    ) -> None:
        cv_data["person"]["photo"] = "missing.jpg"  # type: ignore[index]
        cv = CV.model_validate(cv_data)
        with pytest.raises(RenderError, match="photo not found"):
            build_html(cv, tmp_path)

    def test_existing_photo_is_embedded_as_data_uri(
        self, cv_data: dict[str, object], tmp_path: Path
    ) -> None:
        photo = tmp_path / "photo.jpg"
        photo.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
        cv_data["person"]["photo"] = "photo.jpg"  # type: ignore[index]
        cv = CV.model_validate(cv_data)
        html = build_html(cv, tmp_path)
        assert "data:image/jpeg;base64," in html

    def test_escapes_html_in_free_text_fields(
        self, cv_data: dict[str, object], tmp_path: Path
    ) -> None:
        cv_data["summary"] = "<script>alert('x')</script>"
        cv = CV.model_validate(cv_data)
        html = build_html(cv, tmp_path)
        assert "<script>" not in html


class TestPlaywrightHTMLRenderer:
    """PlaywrightHTMLRenderer: printing the HTML template to PDF."""

    def test_renders_valid_pdf(self, cv: CV, assets_dir: Path, tmp_path: Path) -> None:
        output_path = tmp_path / "cv.pdf"
        renderer = PlaywrightHTMLRenderer()

        result = renderer.render(cv, output_path, assets_dir)

        assert result == output_path
        assert output_path.read_bytes().startswith(b"%PDF")
        assert output_path.stat().st_size > 1000

    def test_missing_photo_raises_render_error_before_launching_browser(
        self, cv_data: dict[str, object], tmp_path: Path
    ) -> None:
        cv_data["person"]["photo"] = "missing.jpg"  # type: ignore[index]
        cv = CV.model_validate(cv_data)
        renderer = PlaywrightHTMLRenderer()

        with pytest.raises(RenderError, match="photo not found"):
            renderer.render(cv, tmp_path / "cv.pdf", tmp_path)

    def test_renders_valid_pdf_with_compact_template(
        self, cv: CV, assets_dir: Path, tmp_path: Path
    ) -> None:
        output_path = tmp_path / "cv.pdf"
        renderer = PlaywrightHTMLRenderer(template="compact")

        renderer.render(cv, output_path, assets_dir)

        assert output_path.read_bytes().startswith(b"%PDF")

    def test_unknown_template_raises_render_error_before_launching_browser(
        self, cv: CV, assets_dir: Path, tmp_path: Path
    ) -> None:
        renderer = PlaywrightHTMLRenderer(template="does-not-exist")

        with pytest.raises(RenderError, match="unknown template"):
            renderer.render(cv, tmp_path / "cv.pdf", assets_dir)
