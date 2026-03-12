"""Command-line script for batch document ingestion.

Usage:
    uv run python scripts/ingest_file.py path/to/document.pdf --title "My Doc" --url "https://..."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docmind.ingestion.graph import ingestion_graph


def main():
    parser = argparse.ArgumentParser(description="Ingest a document into DocMind knowledge base")
    parser.add_argument("file", type=str, help="Path to the file (.pdf or .md)")
    parser.add_argument("--title", type=str, default="", help="Document title")
    parser.add_argument("--url", type=str, default="", help="Source URL")
    parser.add_argument("--category", type=str, default="none", help="Document category")
    parser.add_argument("--business-line", type=str, default="none", help="Business line")
    parser.add_argument("--audience", type=str, default="all", help="Target audience")

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    metadata = {
        "title": args.title or file_path.stem,
        "url": args.url,
        "category": args.category,
        "business_line": args.business_line,
        "audience": args.audience,
    }

    print(f"Ingesting: {file_path.name}")
    print(f"Metadata:  {metadata}")

    try:
        result = ingestion_graph.invoke({
            "file_path": str(file_path),
            "metadata": metadata,
        })
    except Exception as exc:
        print(f"Error: Ingestion failed — {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Status:    {result.get('status', 'unknown')}")
    print(f"Chunks:    {result.get('chunk_count', 0)}")


if __name__ == "__main__":
    main()
