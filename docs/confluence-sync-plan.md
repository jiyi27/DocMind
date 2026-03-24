# Confluence Sync Implementation Plan

## Goal

Add a minimal Confluence integration for knowledge bases.

- A KB can optionally be linked to a Confluence root page.
- A background worker can sync that root page subtree into the KB.
- Confluence pages become KB documents automatically.
- Manual uploads continue to work.

This plan is intentionally scoped to Confluence only.

## Verified API Facts

These points were verified against the current target instance:

- `GET /rest/api/content/{page_id}?expand=title,version,ancestors,space,body.view`
  returns `id`, `title`, `version.number`, `_links.base`, `_links.webui`, and page HTML.
- `GET /rest/api/content/{page_id}/child/page`
  works and supports `start`, `limit`, and `expand=version,space`.
- `GET /rest/api/content/{page_id}/descendant/page`
  returns `501`, so subtree traversal must use recursive `child/page`.
- Document URL can be generated automatically:
  - `source_url = _links.base + _links.webui`

## V1 Scope

1. Create KB with optional Confluence root page binding.
2. Enable or disable Confluence sync per KB.
3. Add a KB-level sync job table.
4. Add a Confluence sync worker.
5. Traverse the root page subtree via recursive `child/page`.
6. Detect page create, update, and delete.
7. Auto-fill Confluence document metadata:
   - title
   - page id
   - URL
   - version
8. Add a manual `sync now` API for one KB.

## Required Data Changes

### `knowledge_bases`

Add:

- `confluence_root_page_id TEXT DEFAULT ''`
- `confluence_sync_enabled INTEGER NOT NULL DEFAULT 0`
- `confluence_retrieval_mode TEXT NOT NULL DEFAULT 'chunk'`
- `confluence_last_sync_at TEXT DEFAULT ''`
- `confluence_last_sync_status TEXT DEFAULT ''`
- `confluence_last_sync_error TEXT DEFAULT ''`

`confluence_retrieval_mode` controls how all Confluence pages in this KB are ingested.
Allowed values mirror the existing document retrieval modes: `'chunk'` or `'full_doc'`.
The KB admin sets this once based on the nature of the content — short wiki pages suit
`full_doc`; long technical documents suit `chunk`. Mixed-mode per page is not supported
in V1.

These columns are added via `MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS` using the
existing idempotent `ALTER TABLE` migration pattern in `database.py`.

### `documents`

Add:

- `source_type TEXT NOT NULL DEFAULT 'manual'`
- `external_doc_id TEXT DEFAULT ''`
- `source_url TEXT DEFAULT ''`
- `source_version INTEGER NOT NULL DEFAULT 0`

Allowed `source_type` values:

- `'manual'` — uploaded by a user through the ingest API (default for all existing documents)
- `'confluence'` — created automatically by the Confluence sync worker

These columns are added via `MIGRATE_DOCUMENTS_SOURCE_COLUMNS` using the same pattern.

Recommended uniqueness rule:

- one Confluence page per KB
- enforce uniqueness at the database layer, not only in application logic
- preferred SQLite implementation: partial unique index on `(kb_id, external_doc_id)`
  where `source_type = 'confluence'`

Example:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_confluence_unique
ON documents (kb_id, external_doc_id)
WHERE source_type = 'confluence';
```

Application code should still check for an existing Confluence document first, but the
unique index is the final guard against duplicate rows caused by retries, manual sync,
scheduled sync, or race conditions.

### `kb_sync_jobs`

Create a new table. One record per sync run (one KB, one trigger).

- `id TEXT PRIMARY KEY`
- `kb_id TEXT NOT NULL REFERENCES knowledge_bases(id)`
- `status TEXT NOT NULL DEFAULT 'pending'`
- `trigger_type TEXT NOT NULL DEFAULT 'scheduled'`
- `error_message TEXT DEFAULT ''`
- `created_at TEXT NOT NULL`
- `started_at TEXT DEFAULT ''`
- `finished_at TEXT DEFAULT ''`
- `updated_at TEXT NOT NULL`

`trigger_type` values: `'scheduled'` for the background worker, `'manual'` for `POST /kb/{kb_id}/sync`.

### `kb_sync_records`

Create a new table. One record per document operation within a sync run.

- `id TEXT PRIMARY KEY`
- `job_id TEXT NOT NULL REFERENCES kb_sync_jobs(id) ON DELETE CASCADE`
- `kb_id TEXT NOT NULL REFERENCES knowledge_bases(id)`
- `external_doc_id TEXT NOT NULL` — Confluence page id
- `document_title TEXT DEFAULT ''`
- `source_url TEXT DEFAULT ''`
- `operation TEXT NOT NULL` — `'create'`, `'update'`, `'delete'`
- `status TEXT NOT NULL` — `'success'`, `'failed'`, `'skipped'`
- `error_message TEXT DEFAULT ''`
- `created_at TEXT NOT NULL`

`status` values:

- `'success'` — operation completed at the sync layer. For `create` and `update` this
  means the document record was created and the ingestion job was enqueued successfully,
  not that embedding has finished. Final indexing status is tracked separately in
  `documents.status`.
- `'failed'` — the operation did not complete. Covers all failure cases: Confluence API
  unreachable, DB write failed, page exceeds `max_full_doc_chars`, or any other exception.
  The `error_message` column records the specific reason.

Both tables are added directly to `ALL_TABLES`; `CREATE TABLE IF NOT EXISTS` is idempotent.

## System Ownership for Confluence Documents

V1 should not create a fake `confluence_admin` user bound to an arbitrary KB. In the current
schema, `users.kb_id` is a real foreign key, so attaching a system user to "the first KB"
would make that KB harder or impossible to delete cleanly later.

Preferred approach:

- allow `documents.user_id` to be nullable
- for `source_type='confluence'`, store `user_id = NULL`
- treat `NULL` uploader as a system-owned document in serializers / frontend display
- keep authorization based on `documents.kb_id` plus the caller's role, not on document owner

Frontend / API display:

- `uploader_name = NULL` from SQL joins remains acceptable at the storage layer
- serializers or frontend can render this as `System` or `Confluence Sync`

Fallback if nullable `documents.user_id` is rejected:

- introduce a real system-user concept only after first relaxing the `users.kb_id` constraint
  or otherwise allowing a user record that is not tied to a business KB
- do not bind a synthetic user to an arbitrary KB just to satisfy today's schema

## Required Refactors

Before implementing sync, extract reusable document operations from the ingest router.

Create `docmind/services/document_service.py` with functions for:

- creating a pending document record
- enqueueing an ingestion job
- deleting a document and its vectors

Important fix:

- document deletion must resolve the document's real KB collection via `documents.kb_id`
- do not rely on `current_user.kb_name`

## New Modules

Add these modules:

- `docmind/integrations/confluence/__init__.py`
- `docmind/integrations/confluence/client.py`
- `docmind/integrations/confluence/sync_planner.py`
- `docmind/integrations/confluence/service.py`
- `docmind/integrations/confluence/worker.py`
- `docmind/services/document_service.py`

All Confluence-specific code lives under `docmind/integrations/confluence/`.
`document_service` lives under `docmind/services/` because it is not Confluence-specific
and may be reused by other integrations.

## Confluence Client Responsibilities

The Confluence client should provide:

- `get_page(page_id, expand=...)`
- `list_child_pages(page_id, start=0, limit=50, expand='version,space')`
- `walk_page_tree(root_page_id)`

`walk_page_tree` should recursively call `child/page` and return a flat list of page summaries.

## HTML to Markdown Conversion

Confluence page bodies are returned as HTML (`body.view`). Before ingestion, convert HTML
to Markdown using `markdownify`.

Rationale: Confluence HTML contains nested lists, code blocks, and tables. `markdownify`
handles these structures more reliably than `html2text`, producing cleaner output for the
downstream splitter.

Conversion and file handling:

1. Convert HTML to Markdown text via `markdownify`.
2. Save the result as `data/uploads/{doc_id}_{page_id}.md`.
3. Pass the `.md` file path to the existing ingestion pipeline.

The existing `load_document` dispatcher in `loaders.py` already handles `.md` files via
`load_markdown`, so no changes to the loader layer are required.

## Sync Planner Rules

For one KB:

- Load all remote pages under the root page.
- Load all local documents where `source_type = 'confluence'`.
- Compare by `external_doc_id`.

Planner output:

- `to_create`: remote page exists, local doc does not
- `to_update`: remote page exists, local doc exists, `remote.version > local.source_version`
- `to_delete`: local doc exists, remote page no longer exists in subtree
- `unchanged`: same page id and same version

## Sync Apply Rules

### Create

For each page in `to_create`:

1. Fetch page detail with `body.view`.
2. Convert HTML to Markdown using `markdownify`.
3. Save as `data/uploads/{doc_id}_{page_id}.md`.
4. If `confluence_retrieval_mode = 'full_doc'`, check the converted Markdown length
   against `settings.retrieval.max_full_doc_chars`. If exceeded, write a `kb_sync_records`
   entry with `operation='create'`, `status='failed'`, and the size reason in
   `error_message`. Do not fail the entire sync job. Move to the next page.
5. Create a document record with:
   - `source_type='confluence'`
   - `external_doc_id=page_id`
   - `source_url`
   - `source_version`
   - `title`
   - `user_id = NULL` to indicate a system-owned Confluence document
6. Insert a job into `ingestion_jobs` with the following `payload_json` structure,
   which must match `IngestionState` exactly:

```json
{
  "file_path": "data/uploads/{doc_id}_{page_id}.md",
  "metadata": {
    "title": "<page title>",
    "url": "<source_url>",
    "doc_type": "all",
    "service": "all"
  },
  "user_id": "",
  "doc_id": "<doc_id>",
  "kb_name": "<kb name slug>",
  "retrieval_mode": "<confluence_retrieval_mode>",
  "strict_mode": false,
  "chunk_size": "<settings.ingestion.chunk_size>",
  "max_chunk_size": "<settings.ingestion.max_chunk_size>",
  "chunk_overlap": "<settings.ingestion.chunk_overlap>"
}
```

`strict_mode` is always `false` for Confluence documents. Confluence pages frequently
contain long paragraphs that would trigger strict-mode validation failures.

`kb_name` is the knowledge base slug (`knowledge_bases.name`), not `kb_id`. The sync
service must look up the KB record to get this value before constructing the payload.

The existing `IngestionQueueWorker` picks up the job automatically. For `chunk` mode
the worker deletes the temp `.md` file after ingestion completes. For `full_doc` mode
the file is kept permanently for retrieval.

7. Write a `kb_sync_records` entry with `operation='create'`, `status='success'`.
   If any step above raises an exception, write the record with `status='failed'` and
   the exception message in `error_message`. Clean up any partially written files.

### Update

V1 strategy must avoid a delete-first gap. Do not delete the old local document before the
replacement content has been prepared successfully.

Safer V1 strategy:

1. Fetch the latest page detail with `body.view`.
2. Convert HTML to Markdown using `markdownify`.
3. If `confluence_retrieval_mode = 'full_doc'`, validate the converted Markdown length
   against `settings.retrieval.max_full_doc_chars`. If it exceeds the limit, write
   `operation='update'`, `status='failed'`, and keep the old document unchanged.
4. Create the replacement local document record and enqueue its ingestion job.
5. Only after the replacement document has been created and the ingestion job has been
   enqueued successfully, delete the old document and its vectors.
6. Write a `kb_sync_records` entry with `operation='update'`, `status='success'`.

Failure rule:

- if any step before replacement enqueue fails, leave the old document and vectors intact
- V1 may temporarily tolerate a short overlap window between old and new local records if
  that keeps the system safe from accidental data loss

### Delete

1. Delete vectors.
2. Delete the local document.
3. Write a `kb_sync_records` entry with `operation='delete'`, `status='success'`.
   On any failure, write `status='failed'` with the error message.

## Configuration

Use global backend config for V1:

- `CONFLUENCE_BASE_URL`
- `CONFLUENCE_PAT`
- `CONFLUENCE_SYNC_INTERVAL_SECONDS`

Do not add per-KB Confluence credentials in V1.

Add a `ConfluenceConfig` dataclass to `core/config.py`, but do not load it with the same
"always required" semantics used by core runtime dependencies like JWT or Qdrant.

Expected behavior:

- if both `CONFLUENCE_BASE_URL` and `CONFLUENCE_PAT` are empty, Confluence integration is
  treated as disabled and the sync worker does not start
- if one of them is set but the other is missing, fail fast at startup with a clear error
- `CONFLUENCE_SYNC_INTERVAL_SECONDS` can have a code-level default for V1

Add corresponding entries to `.env.example` and keep the optional-startup behavior explicit.

## API Changes

### KB Create / Update

Allow KB payload to include optional Confluence settings:

```json
{
  "confluence": {
    "root_page_id": "39383288",
    "sync_enabled": true,
    "retrieval_mode": "chunk"
  }
}
```

`retrieval_mode` maps to `confluence_retrieval_mode` on the KB. Allowed values: `'chunk'`
(default) or `'full_doc'`. Omitting the field leaves the existing value unchanged.

### Manual Sync

Add:

- `POST /kb/{kb_id}/sync`

Behavior:

- create a pending `kb_sync_jobs` record with `trigger_type='manual'`
- return accepted response

### Sync Records

Add:

- `GET /kb/{kb_id}/sync/jobs` — list sync runs for a KB, ordered by `created_at DESC`
- `GET /kb/{kb_id}/sync/jobs/{job_id}/records` — list all document-level records for a specific sync run

Response fields for each record: `external_doc_id`, `document_title`, `source_url`,
`operation`, `status`, `error_message`, `created_at`.

## Worker Model

Keep the current ingestion worker.

Add a second worker for KB sync:

- find KBs with `confluence_sync_enabled = 1`
- create or claim sync jobs
- call the Confluence sync service
- update KB sync status fields

The worker should start only when Confluence integration is configured. If Confluence config
is absent, the rest of the backend should still boot normally and manual uploads must remain
fully available.

## Implementation Phases

### Phase 1: Foundations

Implement:

- DB changes for `knowledge_bases` (`MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS`)
- DB changes for `documents` (`MIGRATE_DOCUMENTS_SOURCE_COLUMNS`)
- new `kb_sync_jobs` table in `ALL_TABLES`
- new `kb_sync_records` table in `ALL_TABLES`
- repository methods for sync jobs, sync records, and Confluence documents
- `document_service`
- deletion fix for correct KB collection lookup
- optional config entries for Confluence
- nullable / system-owned document handling for Confluence sources

Done when:

- manual upload still works
- reusable document lifecycle methods exist
- Confluence being unconfigured does not block backend startup

### Phase 2: Manual Confluence Sync

Implement:

- `ConfluenceClient`
- recursive subtree traversal via `child/page`
- `sync_planner`
- `integrations/confluence/service.py`
- KB create/update support for Confluence binding
- `POST /kb/{kb_id}/sync`

Done when:

- one KB can be manually synced from Confluence
- new pages are created
- updated pages are re-ingested
- removed pages are deleted
- each operation produces a `kb_sync_records` entry
- sync history is queryable via `GET /kb/{kb_id}/sync/jobs` and per-job records API

### Phase 3: Background Sync Worker

Implement:

- `integrations/confluence/worker.py`
- periodic sync loop
- sync job claiming/execution
- KB sync status updates

Done when:

- enabled KBs sync automatically
- sync failures are visible

## Notes for the Implementing AI

- Prefer reusing the current ingestion pipeline instead of adding a separate indexing path.
- For subtree discovery, do not use `descendant/page`; use recursive `child/page`.
- Generate Confluence document URLs from `_links.base + _links.webui`.
- Only fetch full page body for `to_create` and `to_update`.
- Use `markdownify` for HTML-to-Markdown conversion; save output as `.md` to reuse the existing loader.
- All Confluence sync modules go under `docmind/integrations/confluence/`.
- Prefer `NULL` `documents.user_id` for Confluence-owned records over a synthetic user bound to a real KB.

### Ingestion pipeline contract

The ingestion pipeline is invoked by inserting a record into `ingestion_jobs`. The existing
`IngestionQueueWorker` polls this table and calls `ingestion_graph.invoke(payload_json)`.
The sync service must never call the graph directly — always go through the job queue.

The `payload_json` must be a valid `IngestionState` dict. Required fields: `file_path`,
`metadata`, `user_id`, `doc_id`, `kb_name`, `retrieval_mode`, `strict_mode`, `chunk_size`,
`max_chunk_size`, `chunk_overlap`. Missing fields cause silent fallback to defaults or
runtime errors inside graph nodes.

`kb_name` is `knowledge_bases.name` (the Qdrant collection slug), not `kb_id`.
Always look up the KB record and read the `name` field before constructing the payload.

Always set `strict_mode=False` for Confluence documents. Confluence HTML frequently
produces long paragraphs after conversion that would fail strict-mode chunk validation.

### Sync record semantics

A `kb_sync_records` row must be written for every planned operation. Never silently drop
a page — always leave a traceable record.

`status='success'` for `create` and `update` means the ingestion job was enqueued, not
that embedding completed. Embedding failures are visible in `documents.status` and
`ingestion_jobs.error_message`, not in `kb_sync_records`. Do not conflate the two layers.

### Document lifecycle safety

Extract reusable lifecycle helpers into `docmind/services/document_service.py`.

Responsibilities:

- create a pending document record
- enqueue an ingestion job from a valid `IngestionState` payload
- delete a document and its vectors by resolving the real KB collection from `documents.kb_id`

Important rule:

- deletion must look up the document's KB first and then resolve `knowledge_bases.name`
- never use `current_user.kb_name` for cross-source lifecycle operations

- Keep V1 simple. Do not add webhook support yet.
