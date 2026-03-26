from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.ingestion.nodes import _protect_fenced_blocks


def test_protect_fenced_blocks_replaces_each_fenced_block_with_placeholders() -> None:
    text = (
        "# Title\n\n"
        "Before code block.\n\n"
        "```python\n"
        "print('hello')\n"
        "```\n\n"
        "Between blocks.\n\n"
        "```sql\n"
        "SELECT 1;\n"
        "```\n\n"
        "After code block.\n"
    )

    protected_text, fenced_blocks = _protect_fenced_blocks(text)

    assert "__CODE_BLOCK_0__" in protected_text
    assert "__CODE_BLOCK_1__" in protected_text
    assert "```python" not in protected_text
    assert "```sql" not in protected_text
    assert fenced_blocks == [
        "```python\nprint('hello')\n```",
        "```sql\nSELECT 1;\n```",
    ]
