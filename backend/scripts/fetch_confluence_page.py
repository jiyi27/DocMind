"""Fetch a Confluence page by URL, convert to Markdown, and save locally.

Uses the same HTML→Markdown conversion logic as the production sync pipeline.
Credentials (base_url, PAT) are read from the app database — no extra config needed.

Usage (run from the backend/ directory):
    uv run python scripts/fetch_confluence_page.py <confluence_url>

Example:
    uv run python scripts/fetch_confluence_page.py "https://docs.surfin-cn.com/pages/viewpage.action?pageId=13870694"

Output:
    Markdown file saved to backend/data/confluence_preview/<page_id>_<title>.md
"""

import asyncio
import sqlite3
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

# This file is `backend/scripts/fetch_confluence_page.py`.
# The `docmind` package we want to import is in `backend/docmind/`.
# When Python runs a file inside `scripts/`, it may only look inside `scripts/`
# first, so `from docmind...` can fail even if you started the command in
# `backend/`.
# We fix that by adding `backend/` itself to Python's import search path.
# Without this, Python cannot find `backend/docmind` when running this script.
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from docmind.integrations.confluence.converter import (
    convert_confluence_html_to_markdown,
)

DB_PATH = "data/docmind.db"
OUTPUT_DIR = Path("data/confluence_preview")


def get_confluence_credentials() -> tuple[str, str]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT key, value FROM system_settings WHERE key IN ('confluence_base_url', 'confluence_pat')"
    ).fetchall()
    conn.close()
    creds = {row["key"]: row["value"] for row in rows}
    base_url = creds.get("confluence_base_url", "").strip().rstrip("/")
    pat = creds.get("confluence_pat", "").strip()
    if not base_url or not pat:
        raise RuntimeError("Confluence credentials not found in DB")
    return base_url, pat


def extract_page_id(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "pageId" in qs:
        return qs["pageId"][0]
    raise ValueError(f"Cannot extract pageId from URL: {url}")


async def fetch_and_save(url: str) -> None:
    base_url, pat = get_confluence_credentials()
    page_id = extract_page_id(url)

    async with httpx.AsyncClient(
        base_url=f"{base_url}/rest/api",
        headers={"Authorization": f"Bearer {pat}", "Accept": "application/json"},
        timeout=30.0,
    ) as client:
        resp = await client.get(
            f"/content/{page_id}",
            params={"expand": "title,version,body.view"},
        )
        resp.raise_for_status()
        data = resp.json()

    title = data.get("title", page_id)
    html_body = data.get("body", {}).get("view", {}).get("value", "")
    version = data.get("version", {}).get("number", 0)
    links = data.get("_links", {})
    source_url = f"{links.get('base', base_url)}{links.get('webui', '')}"

    md_content = convert_confluence_html_to_markdown(html_body, source_url)

    OUTPUT_DIR.mkdir(exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
    out_path = OUTPUT_DIR / f"{page_id}_{safe_title}.md"
    out_path.write_text(md_content, encoding="utf-8")

    print(f"Title   : {title}")
    print(f"Version : {version}")
    print(f"URL     : {source_url}")
    print(f"HTML    : {len(html_body):,} chars")
    print(f"Markdown: {len(md_content):,} chars")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/fetch_confluence_page.py <confluence_url>")
        sys.exit(1)
    try:
        asyncio.run(fetch_and_save(sys.argv[1]))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            print(
                "Confluence returned 403 Forbidden. Check the configured PAT in "
                "system_settings and confirm that account can access this page."
            )
        else:
            print(
                f"Confluence request failed with HTTP {exc.response.status_code}: "
                f"{exc.request.url}"
            )
        sys.exit(1)
    except httpx.RequestError as exc:
        print(f"Failed to reach Confluence: {exc}")
        sys.exit(1)
