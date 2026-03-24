"""Confluence REST API client.

Uses Personal Access Token (PAT) authentication and recursive
``child/page`` traversal (the ``descendant/page`` endpoint returns 501
on tested instances).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
        self._client = httpx.Client(
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

    def get_page(
        self, page_id: str, expand: str = "title,version,body.view,space"
    ) -> dict[str, Any]:
        """Fetch a single page with optional expansions."""
        resp = self._client.get(f"/content/{page_id}", params={"expand": expand})
        resp.raise_for_status()
        return resp.json()

    def list_child_pages(
        self,
        page_id: str,
        start: int = 0,
        limit: int = 50,
        expand: str = "version,space",
    ) -> list[dict[str, Any]]:
        """Return all child pages under *page_id* (handles pagination)."""
        results: list[dict[str, Any]] = []
        while True:
            resp = self._client.get(
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

    def walk_page_tree(self, root_page_id: str) -> list[PageSummary]:
        """Recursively discover all pages under *root_page_id*.

        Returns a flat list of ``PageSummary`` objects. The root page
        itself is **not** included in the results.
        """
        all_pages: list[PageSummary] = []
        queue = [root_page_id]

        while queue:
            parent_id = queue.pop(0)
            try:
                children = self.list_child_pages(parent_id)
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

    def get_page_body_html(self, page_id: str) -> tuple[str, str, int, str]:
        """Fetch a page's HTML body for conversion.

        Returns ``(title, html_body, version, source_url)``.
        """
        page = self.get_page(page_id, expand="title,version,body.view")
        title = page.get("title", "")
        html_body = page.get("body", {}).get("view", {}).get("value", "")
        version = int(page.get("version", {}).get("number", 0))
        source_url = self._build_source_url(page)
        return title, html_body, version, source_url

    def close(self) -> None:
        self._client.close()
