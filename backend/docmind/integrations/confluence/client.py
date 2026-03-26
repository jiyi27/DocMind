"""Confluence REST API client.

Uses Personal Access Token (PAT) authentication and recursive
``child/page`` traversal (the ``descendant/page`` endpoint returns 501
on tested instances).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote_plus, urlparse

import httpx

from docmind.core import logger


@dataclass(frozen=True)
class PageSummary:
    """Lightweight representation of a Confluence page for sync planning."""

    page_id: str
    title: str
    version: int
    source_url: str


class ConfluenceClient:
    """Thin wrapper around the Confluence REST API v1."""

    def __init__(self, base_url: str, pat: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{self._base_url}/rest/api",
            headers={
                "Authorization": f"Bearer {pat}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Low-level API calls
    # ------------------------------------------------------------------

    async def get_page(
        self, page_id: str, expand: str = "title,version,body.view,space"
    ) -> dict[str, Any]:
        """Fetch a single page with optional expansions."""
        resp = await self._client.get(f"/content/{page_id}", params={"expand": expand})
        resp.raise_for_status()
        return resp.json()

    async def list_child_pages(
        self,
        page_id: str,
        start: int = 0,
        limit: int = 50,
        expand: str = "version,space",
    ) -> list[dict[str, Any]]:
        """Return all child pages under *page_id* (handles pagination)."""
        results: list[dict[str, Any]] = []
        while True:
            resp = await self._client.get(
                f"/content/{page_id}/child/page",
                params={"start": start, "limit": limit, "expand": expand},
            )
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results", []))
            # Check if there are more pages
            size = data.get("size", 0)
            if size < limit:
                break
            start += limit
        return results

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    def _build_source_url(self, page: dict[str, Any]) -> str:
        links = page.get("_links", {})
        base = links.get("base", self._base_url)
        webui = links.get("webui", "")
        return f"{base}{webui}" if webui else ""

    def _to_page_summary(self, page: dict[str, Any]) -> PageSummary:
        version_info = page.get("version", {})
        return PageSummary(
            page_id=str(page["id"]),
            title=page.get("title", ""),
            version=int(version_info.get("number", 0)),
            source_url=self._build_source_url(page),
        )

    async def walk_page_tree(self, root_page_id: str) -> list[PageSummary]:
        """Recursively discover all pages under *root_page_id*.

        Returns a flat list of ``PageSummary`` objects. The root page
        itself is **not** included in the results.
        """
        all_pages: list[PageSummary] = []
        queue = [root_page_id]

        while queue:
            parent_id = queue.pop(0)
            try:
                children = await self.list_child_pages(parent_id)
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "confluence_list_children_failed",
                    {"parent_id": parent_id, "status": exc.response.status_code},
                    exc=exc,
                )
                continue

            for child in children:
                summary = self._to_page_summary(child)
                all_pages.append(summary)
                queue.append(summary.page_id)

        logger.info(
            "confluence_tree_walk_complete",
            {"root_page_id": root_page_id, "total_pages": len(all_pages)},
        )
        return all_pages

    async def get_page_body_html(self, page_id: str) -> tuple[str, str, int, str]:
        """Fetch a page's HTML body for conversion.

        Returns ``(title, html_body, version, source_url)``.
        """
        page = await self.get_page(page_id, expand="title,version,body.view")
        title = page.get("title", "")
        html_body = page.get("body", {}).get("view", {}).get("value", "")
        version = int(page.get("version", {}).get("number", 0))
        source_url = self._build_source_url(page)
        return title, html_body, version, source_url

    @staticmethod
    def _parse_confluence_url(url: str) -> tuple[str, dict[str, str]]:
        """Identify URL type and extract lookup params.

        Returns ``('page_id', {'id': '...'})`` for ``?pageId=`` URLs, or
        ``('friendly', {'space': '...', 'title': '...'})`` for ``/display/`` URLs.
        Raises ``ValueError`` for unrecognised formats.
        """
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "pageId" in qs:
            return "page_id", {"id": qs["pageId"][0]}
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 3 and parts[0] == "display":
            return "friendly", {"space": parts[1], "title": unquote_plus(parts[2])}
        raise ValueError(f"Unrecognised Confluence URL format: {url}")

    async def resolve_page_url(self, url: str) -> tuple[str, str, str]:
        """Resolve any Confluence page URL to ``(page_id, title, source_url)``.

        Accepts both ``/display/SPACE/Title`` and ``?pageId=XXX`` formats.
        Raises ``ValueError`` for bad URLs or pages not found.
        """
        url_type, params = self._parse_confluence_url(url)
        if url_type == "page_id":
            page = await self.get_page(params["id"], expand="title,version")
        else:
            resp = await self._client.get(
                "/content",
                params={
                    "spaceKey": params["space"],
                    "title": params["title"],
                    "expand": "version",
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                raise ValueError(
                    f"Page not found: space={params['space']!r}, title={params['title']!r}"
                )
            page = results[0]
        page_id = str(page["id"])
        title = page.get("title", "")
        source_url = self._build_source_url(page)
        return page_id, title, source_url

    async def close(self) -> None:
        await self._client.aclose()
