"""Fetching job postings from job board URLs."""

from __future__ import annotations

from typing import Protocol

import httpx
from bs4 import BeautifulSoup, Tag

from autocv.jobs.errors import JobFetchError
from autocv.jobs.models import JobPosting

_USER_AGENT = "Mozilla/5.0 (compatible; autocv/0.1; +https://google.com)"
_DESCRIPTION_SELECTOR = ".description__text, .show-more-less-html__markup"


class JobPostingFetcher(Protocol):
    """A source that fetches a job posting from a URL."""

    def fetch(self, url: str) -> JobPosting:
        """Fetch and parse a job posting.

        Args:
            url: The job posting URL.

        Returns:
            The parsed job posting.

        Raises:
            JobFetchError: If the posting cannot be fetched or parsed.
        """
        ...


def default_http_client() -> httpx.Client:
    """Build the default HTTP client for fetching job postings.

    Returns:
        A configured, unopened ``httpx.Client``. Callers own its lifecycle.
    """
    return httpx.Client(headers={"User-Agent": _USER_AGENT}, follow_redirects=True, timeout=15.0)


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    """Read a ``<meta property="...">`` tag's content, if present and non-empty.

    Args:
        soup: The parsed document.
        property_name: The ``property`` attribute to match, e.g. ``og:title``.

    Returns:
        The trimmed content, or ``None``.
    """
    tag = soup.find("meta", attrs={"property": property_name})
    if not isinstance(tag, Tag):
        return None
    content = tag.get("content")
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    return stripped or None


def _node_text(node: Tag | None) -> str | None:
    """Read a tag's visible text, if present and non-empty.

    Args:
        node: The tag to read, or ``None``.

    Returns:
        The trimmed text, or ``None``.
    """
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


class LinkedInJobFetcher:
    """Best-effort fetcher for public LinkedIn job posting pages.

    LinkedIn serves partial markup to unauthenticated requests, so this
    extracts whatever title/description metadata is present rather than
    requiring a login. Callers that hit a login wall should fall back to
    supplying job posting text directly.
    """

    def __init__(self, client: httpx.Client) -> None:
        """Initialize the fetcher.

        Args:
            client: The HTTP client to fetch with. The caller owns its
                lifecycle (see ``default_http_client``).
        """
        self._client = client

    def fetch(self, url: str) -> JobPosting:
        """Fetch and parse a job posting from a LinkedIn job URL.

        Args:
            url: The job posting URL.

        Returns:
            The parsed job posting.

        Raises:
            JobFetchError: If the page cannot be fetched, or no title and
                description could be extracted from it.
        """
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise JobFetchError(f"failed to fetch {url}: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        title = _meta_content(soup, "og:title") or _node_text(soup.title)
        company = _meta_content(soup, "og:site_name")
        description = _meta_content(soup, "og:description") or _node_text(
            soup.select_one(_DESCRIPTION_SELECTOR)
        )

        if not title or not description:
            raise JobFetchError(
                f"could not extract a job posting from {url}; the page may require "
                "authentication — pass the posting text directly instead"
            )

        return JobPosting(title=title, company=company, location=None, description=description)
