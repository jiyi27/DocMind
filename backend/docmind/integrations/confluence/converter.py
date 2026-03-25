"""Confluence HTML to Markdown conversion utilities."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
import markdownify


def _pick_image_url(img: Tag, page_url: str) -> str:
    """Resolve the best usable image URL from a Confluence ``img`` node."""
    candidates = (
        img.get("src"),
        img.get("data-image-src"),
        img.get("data-src"),
        img.get("data-lazy-src"),
    )
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate).strip()
        if not value or value.startswith("data:"):
            continue
        return urljoin(page_url, value)
    return ""


def _normalize_html_urls(html: str, page_url: str) -> str:
    """Convert relative Confluence links and images into absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")

    for img in soup.find_all("img"):
        absolute_url = _pick_image_url(img, page_url)
        if absolute_url:
            img["src"] = absolute_url

    for anchor in soup.find_all("a", href=True):
        anchor["href"] = urljoin(page_url, str(anchor["href"]))

    return str(soup)


def convert_confluence_html_to_markdown(html: str, page_url: str) -> str:
    """Convert Confluence-rendered HTML into Markdown while preserving images."""
    normalized_html = _normalize_html_urls(html, page_url)
    return markdownify.markdownify(
        normalized_html,
        heading_style="ATX",
    )
