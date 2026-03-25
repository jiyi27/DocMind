from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.integrations.confluence.converter import (
    convert_confluence_html_to_markdown,
)


def test_convert_confluence_html_to_markdown_preserves_images_and_links() -> None:
    html = """
    <h2>Import Notes</h2>
    <p>See <a href="/pages/viewpage.action?pageId=42">reference</a>.</p>
    <p><img alt="chunk preview" data-image-src="/download/attachments/42/chunk.png?api=v2" /></p>
    """

    markdown = convert_confluence_html_to_markdown(
        html,
        "https://docs.surfin-cn.com/pages/viewpage.action?pageId=76810043",
    )

    assert "## Import Notes" in markdown
    assert (
        "[reference](https://docs.surfin-cn.com/pages/viewpage.action?pageId=42)"
        in markdown
    )
    assert (
        "![chunk preview](https://docs.surfin-cn.com/download/attachments/42/chunk.png?api=v2)"
        in markdown
    )
