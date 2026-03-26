"""
DDL statements for all database tables.
"""

CREATE_KNOWLEDGE_BASES_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id                          TEXT PRIMARY KEY,
    name                        TEXT UNIQUE NOT NULL,
    display_name                TEXT NOT NULL,
    description                 TEXT DEFAULT '',
    created_at                  TEXT NOT NULL,
    embedding_provider          TEXT NOT NULL DEFAULT 'openai_compatible',
    embedding_model             TEXT NOT NULL DEFAULT '',
    embedding_base_url          TEXT NOT NULL DEFAULT '',
    embedding_api_key           TEXT NOT NULL DEFAULT '',
    vector_dimension            INTEGER NOT NULL DEFAULT 0,
    confluence_root_page_id     TEXT DEFAULT '',
    confluence_root_page_title  TEXT DEFAULT '',
    confluence_sync_enabled     INTEGER NOT NULL DEFAULT 0,
    confluence_sync_interval_minutes INTEGER NOT NULL DEFAULT 5,
    confluence_retrieval_mode   TEXT NOT NULL DEFAULT 'chunk',
    confluence_last_sync_at     TEXT DEFAULT '',
    confluence_last_sync_status TEXT DEFAULT '',
    confluence_last_sync_error  TEXT DEFAULT ''
);
"""

MIGRATE_KNOWLEDGE_BASES_EMBEDDING_COLUMNS = [
    "ALTER TABLE knowledge_bases ADD COLUMN embedding_provider TEXT NOT NULL DEFAULT 'openai_compatible'",
    "ALTER TABLE knowledge_bases ADD COLUMN embedding_model TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE knowledge_bases ADD COLUMN embedding_base_url TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE knowledge_bases ADD COLUMN embedding_api_key TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE knowledge_bases ADD COLUMN vector_dimension INTEGER NOT NULL DEFAULT 0",
]

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    kb_id           TEXT NOT NULL REFERENCES knowledge_bases(id),
    role            TEXT NOT NULL DEFAULT 'user',
    created_at      TEXT NOT NULL
);
"""

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    user_id         TEXT REFERENCES users(id),
    kb_id           TEXT NOT NULL REFERENCES knowledge_bases(id),
    file_name       TEXT NOT NULL,
    title           TEXT DEFAULT '',
    doc_type        TEXT DEFAULT '',
    chunk_count     INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'pending',
    error_message   TEXT DEFAULT '',
    file_path       TEXT DEFAULT '',
    strict_mode     INTEGER DEFAULT 1,
    retrieval_mode  TEXT DEFAULT 'chunk',
    source_type     TEXT NOT NULL DEFAULT 'manual',
    external_doc_id TEXT DEFAULT '',
    source_url      TEXT DEFAULT '',
    source_version  INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);
"""

CREATE_INGESTION_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id           TEXT PRIMARY KEY,
    document_id  TEXT NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT DEFAULT '',
    claimed_at   TEXT DEFAULT '',
    started_at   TEXT DEFAULT '',
    finished_at  TEXT DEFAULT '',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
"""

CREATE_CHAT_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    kb_id           TEXT REFERENCES knowledge_bases(id),
    title           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    message_count   INTEGER NOT NULL DEFAULT 0,
    last_message_at TEXT,
    last_message_preview TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

CREATE_CHAT_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    sources_json TEXT DEFAULT '[]',
    model_name  TEXT DEFAULT '',
    token_count INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL
);
"""

CREATE_KB_SYNC_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS kb_sync_jobs (
    id              TEXT PRIMARY KEY,
    kb_id           TEXT NOT NULL REFERENCES knowledge_bases(id),
    status          TEXT NOT NULL DEFAULT 'pending',
    trigger_type    TEXT NOT NULL DEFAULT 'scheduled',
    error_message   TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    started_at      TEXT DEFAULT '',
    finished_at     TEXT DEFAULT '',
    updated_at      TEXT NOT NULL
);
"""

CREATE_KB_SYNC_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS kb_sync_records (
    id              TEXT PRIMARY KEY,
    job_id          TEXT NOT NULL REFERENCES kb_sync_jobs(id) ON DELETE CASCADE,
    kb_id           TEXT NOT NULL REFERENCES knowledge_bases(id),
    external_doc_id TEXT NOT NULL,
    document_title  TEXT DEFAULT '',
    source_url      TEXT DEFAULT '',
    operation       TEXT NOT NULL,
    status          TEXT NOT NULL,
    error_message   TEXT DEFAULT '',
    created_at      TEXT NOT NULL
);
"""

MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS = [
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_root_page_id TEXT DEFAULT ''",
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_sync_enabled INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_sync_interval_minutes INTEGER NOT NULL DEFAULT 5",
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_retrieval_mode TEXT NOT NULL DEFAULT 'chunk'",
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_last_sync_at TEXT DEFAULT ''",
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_last_sync_status TEXT DEFAULT ''",
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_last_sync_error TEXT DEFAULT ''",
]

MIGRATE_KNOWLEDGE_BASES_ROOT_PAGE_TITLE_COLUMN = [
    "ALTER TABLE knowledge_bases ADD COLUMN confluence_root_page_title TEXT DEFAULT ''",
]

MIGRATE_DOCUMENTS_SOURCE_COLUMNS = [
    "ALTER TABLE documents ADD COLUMN source_type TEXT NOT NULL DEFAULT 'manual'",
    "ALTER TABLE documents ADD COLUMN external_doc_id TEXT DEFAULT ''",
    "ALTER TABLE documents ADD COLUMN source_url TEXT DEFAULT ''",
    "ALTER TABLE documents ADD COLUMN source_version INTEGER NOT NULL DEFAULT 0",
]

MIGRATE_KB_SYNC_JOBS_SUMMARY_COLUMN = [
    "ALTER TABLE kb_sync_jobs ADD COLUMN summary TEXT DEFAULT ''",
]

CREATE_CONFLUENCE_UNIQUE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_confluence_unique
ON documents (kb_id, external_doc_id)
WHERE source_type = 'confluence';
"""

CREATE_DOCUMENTS_KB_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_documents_kb_created_at
ON documents (kb_id, created_at DESC);
"""

CREATE_DOCUMENTS_USER_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_documents_user_created_at
ON documents (user_id, created_at DESC);
"""

CREATE_DOCUMENTS_USER_KB_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_documents_user_kb_created_at
ON documents (user_id, kb_id, created_at DESC);
"""

CREATE_INGESTION_JOBS_STATUS_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status_created_at
ON ingestion_jobs (status, created_at ASC);
"""

CREATE_KB_SYNC_JOBS_KB_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_kb_sync_jobs_kb_created_at
ON kb_sync_jobs (kb_id, created_at DESC);
"""

CREATE_KB_SYNC_JOBS_KB_STATUS_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_kb_sync_jobs_kb_status_created_at
ON kb_sync_jobs (kb_id, status, created_at DESC);
"""

CREATE_KB_SYNC_RECORDS_JOB_CREATED_AT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_kb_sync_records_job_created_at
ON kb_sync_records (job_id, created_at ASC);
"""

__all__ = [
    "ALL_TABLES",
    "ALL_INDEXES",
    "MIGRATE_KNOWLEDGE_BASES_EMBEDDING_COLUMNS",
    "MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS",
    "MIGRATE_KNOWLEDGE_BASES_ROOT_PAGE_TITLE_COLUMN",
    "MIGRATE_DOCUMENTS_SOURCE_COLUMNS",
    "MIGRATE_KB_SYNC_JOBS_SUMMARY_COLUMN",
    "CREATE_CONFLUENCE_UNIQUE_INDEX",
]

ALL_TABLES = [
    CREATE_KNOWLEDGE_BASES_TABLE,
    CREATE_USERS_TABLE,
    CREATE_DOCUMENTS_TABLE,
    CREATE_INGESTION_JOBS_TABLE,
    CREATE_CHAT_SESSIONS_TABLE,
    CREATE_CHAT_MESSAGES_TABLE,
    CREATE_KB_SYNC_JOBS_TABLE,
    CREATE_KB_SYNC_RECORDS_TABLE,
]

ALL_INDEXES = [
    CREATE_CONFLUENCE_UNIQUE_INDEX,
    CREATE_DOCUMENTS_KB_CREATED_AT_INDEX,
    CREATE_DOCUMENTS_USER_CREATED_AT_INDEX,
    CREATE_DOCUMENTS_USER_KB_CREATED_AT_INDEX,
    CREATE_INGESTION_JOBS_STATUS_CREATED_AT_INDEX,
    CREATE_KB_SYNC_JOBS_KB_CREATED_AT_INDEX,
    CREATE_KB_SYNC_JOBS_KB_STATUS_CREATED_AT_INDEX,
    CREATE_KB_SYNC_RECORDS_JOB_CREATED_AT_INDEX,
]
