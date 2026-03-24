# DocMind Chunking Preview Demo

This document is intentionally mixed and slightly long so chunking behavior is easy to inspect by eye. It includes normal paragraphs, nested headers, a long semantic block, a fenced code sample, a blockquote, and a Markdown table. You can run the preview script on this file directly, or convert it to PDF and compare the output from the PDF loader path.

## Product Overview

DocMind ingests internal documents and transforms them into retrieval-ready chunks. The chunking layer tries to preserve meaning rather than cutting at arbitrary character offsets. In practice that means headers should create boundaries, breadcrumbs should be attached to the final chunk text, and special Markdown structures should remain readable after splitting. When you tweak target size, max size, or overlap, this file gives you one place to visually inspect what changed.

The retrieval team usually cares about two competing goals at the same time. First, each chunk should be compact enough for embedding and ranking. Second, each chunk should still contain enough local context that a user question can match the right part of the original document without losing section meaning. That tradeoff is the reason this preview file includes both short blocks and intentionally longer prose that may need to be automatically split.

### Ingestion States

The ingestion workflow usually starts with load, then split, then optional summarize, and finally embed and store. If metadata is attached during load, downstream chunks should preserve it. When you look at the preview output, pay attention not only to the text body but also to the metadata block printed for each chunk.

## Example Code

```python
from pathlib import Path


def build_chunk_preview(file_path: str, chunk_size: int) -> dict[str, int | str]:
    path = Path(file_path)
    preview_name = path.stem.replace("-", "_")
    summary = {
        "name": preview_name,
        "chunk_size": chunk_size,
        "exists": int(path.exists()),
    }
    if path.exists():
        print(f"previewing {path.name} with chunk size {chunk_size}")
    return summary
```

The code block above should remain atomic in Markdown mode. If it starts getting broken apart, the preview output should make that problem obvious immediately.

## Operational Notes

> A good chunking preview is not a unit test replacement.
> It is a developer tool for fast visual inspection.
> The automated tests should still own regression protection.

The quote above is useful for checking whether blockquote syntax is stripped while the semantic content still stays grouped together in one output block.

## Configuration Matrix

| Setting        | Example | Why It Matters                                                 |
| -------------- | ------- | -------------------------------------------------------------- |
| chunk_size     | 260     | Controls how aggressively content is packed into each chunk    |
| chunk_overlap  | 100     | Keeps some trailing context between adjacent chunks            |

The table above should be converted into prose in Markdown splitting mode. If you compare the Markdown and PDF paths, you should notice that only the Markdown-specific path receives special handling for tables, code fences, and blockquotes.

## Long Paragraph For Non-Strict Preview

This paragraph is intentionally oversized so you can see what the system does when the target chunk size is much smaller than the prose itself. If you run the preview script with a small `--chunk-size`, the paragraph should be recursively split into smaller pieces instead of crashing the whole preview run. The point of this section is not realistic writing quality but a predictable large semantic block that makes automatic splitting easy to inspect.

## Closing Section

When you inspect the final preview output, check three things:

1. The chunk boundaries feel semantic rather than arbitrary.
2. The metadata printed for each chunk still matches the input configuration.
3. The transformed content remains readable for retrieval and debugging.
