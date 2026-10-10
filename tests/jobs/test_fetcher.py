"""Unit tests for autocv.jobs.fetcher."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from autocv.jobs.errors import JobFetchError
from autocv.jobs.fetcher import LinkedInJobFetcher


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _html_response(body: str, status_code: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=body)

    return handler


class TestLinkedInJobFetcher:
    """LinkedInJobFetcher: best-effort extraction from a job posting page."""

    def test_extracts_from_open_graph_meta_tags(self) -> None:
        html = """
        <html><head>
        <meta property="og:title" content="Senior Software Engineer">
        <meta property="og:site_name" content="Example Corp">
        <meta property="og:description" content="Build great things.">
        </head><body></body></html>
        """
        fetcher = LinkedInJobFetcher(_client(_html_response(html)))

        posting = fetcher.fetch("https://www.linkedin.com/jobs/view/1")

        assert posting.title == "Senior Software Engineer"
        assert posting.company == "Example Corp"
        assert posting.description == "Build great things."

    def test_falls_back_to_title_tag_and_description_selector(self) -> None:
        html = """
        <html><head><title>Senior Software Engineer | LinkedIn</title></head>
        <body><div class="description__text">Build great things.</div></body></html>
        """
        fetcher = LinkedInJobFetcher(_client(_html_response(html)))

        posting = fetcher.fetch("https://www.linkedin.com/jobs/view/1")

        assert posting.title == "Senior Software Engineer | LinkedIn"
        assert posting.description == "Build great things."
        assert posting.company is None

    def test_http_error_status_raises_job_fetch_error(self) -> None:
        fetcher = LinkedInJobFetcher(_client(_html_response("not found", status_code=404)))
        with pytest.raises(JobFetchError):
            fetcher.fetch("https://www.linkedin.com/jobs/view/1")

    def test_network_error_raises_job_fetch_error(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        fetcher = LinkedInJobFetcher(_client(handler))
        with pytest.raises(JobFetchError):
            fetcher.fetch("https://www.linkedin.com/jobs/view/1")

    def test_page_without_extractable_content_raises_job_fetch_error(self) -> None:
        html = "<html><head><title>LinkedIn Login</title></head><body></body></html>"
        fetcher = LinkedInJobFetcher(_client(_html_response(html)))
        with pytest.raises(JobFetchError, match="authentication"):
            fetcher.fetch("https://www.linkedin.com/jobs/view/1")
