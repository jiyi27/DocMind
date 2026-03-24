# Chunking Testing Guide

## Purpose

This document explains the current test strategy for the RAG chunking flow in `backend/docmind/ingestion/nodes.py`.

The goal is to protect key behavior while still allowing internal refactors. We do not try to pin every helper function or every intermediate implementation detail. Most tests are written against the workflow entrypoints so chunking logic can evolve without causing noisy test breakage.

---

## Covered Flows

The main test file is:

- `test/test_chunking.py`

It currently covers these behaviors:

### 1. Markdown splitting flow

Test entrypoint:

- `split_text_node(state)`

Verifies:

- Markdown headers trigger chunk boundaries
- Chunk text includes breadcrumb context such as `title / h1 / h2`
- `chunk_overlap` can be overridden from `state`

### 2. Atomic Markdown block handling

Test entrypoint:

- `split_text_node(state)`

Verifies:

- fenced code blocks stay atomic and are not cut in half
- blockquotes stay atomic and the `>` prefix is removed in final chunk text
- Markdown tables are converted to prose and stay atomic

### 3. Oversized block handling

Test entrypoint:

- `split_text_node(state)`

Verifies:

- oversized blocks are recursively split instead of failing the whole ingestion step

### 4. PDF paragraph splitting

Test entrypoint:

- `split_text_node(state)`

Verifies:

- plain text paragraph splitting for PDF-like content
- overlap across adjacent PDF chunks

### 5. Metadata inheritance in the ingestion workflow

Test entrypoints:

- `load_document_node(state)`
- `split_text_node(state)`

Verifies:

- metadata stamped during load is preserved after splitting
- identity fields such as `doc_id`, `user_id`, `kb_name`, and `retrieval_mode` appear on output chunks

### 6. Pure helper functions

Direct tests are intentionally limited to helpers that are stable, pure, and useful in isolation:

- `_halve_text`
- `_table_to_prose`

Verifies:

- `_halve_text` keeps every piece within the configured max size and prefers newline-aware splitting
- `_table_to_prose` converts standard pipe tables to readable prose and leaves non-standard input unchanged

---

## Fixtures

Fixtures live under:

- `test/fixtures/`

Current fixture files:

- `test/fixtures/basic_headers.md`
  Used for header boundaries, breadcrumb checks, and overlap behavior in Markdown.
- `test/fixtures/atomic_blocks.md`
  Used for fenced code block, blockquote, and table behavior.
- `test/fixtures/oversized_block.md`
  Used for automatic splitting of oversized semantic blocks.

Guideline:

- Prefer fixture files over large inline strings when testing realistic Markdown structure.
- Keep fixture content small but intentional.
- Each fixture should exist for one clear behavioral purpose.

---

## How To Run

All commands must be run from the `backend/` directory.

Run the chunking test file:

```bash
cd backend
uv run pytest test/test_chunking.py
```

Run all backend tests if needed:

```bash
cd backend
uv run pytest test/
```

---

## What We Intentionally Do Not Test

We do not try to test every private helper or every branch in isolation.

We also do not currently cover:

- `summarize_code_node`
  Reason: it depends on LLM behavior and should be tested separately with mocking or a higher-level integration strategy.
- visual preview scripts for manual inspection
  Reason: these are easy to let drift away from the real implementation and should not live inside automated test coverage.

---

## Maintenance Principles

When chunking logic changes, update tests based on behavior, not helper names.

Prefer this order when adding coverage:

1. Add or adjust a workflow-level assertion in `test/test_chunking.py`
2. Add or adjust a fixture in `test/fixtures/`
3. Only add a direct unit test for a helper if that helper is pure, stable, and valuable on its own

Avoid these anti-patterns:

- tests that only `print()` output without assertions
- tests that call deleted or non-public APIs as if they were stable contracts
- exploratory scripts mixed into `test/` or named as if they were real automated tests

---

## Current Files

Relevant files today:

- `docmind/ingestion/nodes.py`
- `docmind/ingestion/state.py`
- `test/test_chunking.py`
- `test/fixtures/basic_headers.md`
- `test/fixtures/atomic_blocks.md`
- `test/fixtures/oversized_block.md`

This document should be updated whenever the chunking test scope changes in a meaningful way.
