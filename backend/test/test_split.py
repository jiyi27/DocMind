from langchain_core.documents import Document
from docmind.ingestion.nodes import _custom_split_markdown, _strict_split_pdf


def test_strict_split_markdown():
    doc = Document(
        page_content="# Header 1\n\nSome text\n\n```python\nprint('hello')\n```\n\nMore text",
        metadata={"file_name": "test.md"},
    )
    chunks = _custom_split_markdown(doc, target_size=100, max_size=1500, overlap=0)
    for c in chunks:
        print(f"CHUNK: {c.page_content!r}, META: {c.metadata}")


def test_strict_split_pdf():
    doc = Document(
        page_content="Paragraph 1\n\nParagraph 2\n\nParagraph 3",
        metadata={"file_name": "test.pdf"},
    )
    chunks = _strict_split_pdf(doc, target_size=50, max_size=1500, overlap=0)
    for c in chunks:
        print(f"CHUNK: {c.page_content!r}, META: {c.metadata}")


test_strict_split_markdown()
test_strict_split_pdf()
