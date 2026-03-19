"""
DDL statements for all database tables.
"""

CREATE_KNOWLEDGE_BASES_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id                  TEXT PRIMARY KEY,
    name                TEXT UNIQUE NOT NULL,
    display_name        TEXT NOT NULL,
    description         TEXT DEFAULT '',
    created_at          TEXT NOT NULL,
    embedding_provider  TEXT NOT NULL DEFAULT 'openai_compatible',
    embedding_model     TEXT NOT NULL DEFAULT '',
    embedding_base_url  TEXT NOT NULL DEFAULT '',
    embedding_api_key   TEXT NOT NULL DEFAULT '',
    vector_dimension    INTEGER NOT NULL DEFAULT 0
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
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    kb_id       TEXT NOT NULL REFERENCES knowledge_bases(id),
    file_name   TEXT NOT NULL,
    title       TEXT DEFAULT '',
    doc_type    TEXT DEFAULT '',
    chunk_count INTEGER DEFAULT 0,
    status        TEXT DEFAULT 'pending',
    error_message TEXT DEFAULT '',
    file_path     TEXT DEFAULT '',
    strict_mode     INTEGER DEFAULT 1,
    retrieval_mode  TEXT DEFAULT 'chunk',
    created_at  TEXT NOT NULL
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
    sources_json TEXT DEFAULT '',
    model_name  TEXT DEFAULT '',
    token_count INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL
);
"""

__all__ = [
    "ALL_TABLES",
    "MIGRATE_KNOWLEDGE_BASES_EMBEDDING_COLUMNS",
]

ALL_TABLES = [
    CREATE_KNOWLEDGE_BASES_TABLE,
    CREATE_USERS_TABLE,
    CREATE_DOCUMENTS_TABLE,
    CREATE_INGESTION_JOBS_TABLE,
    CREATE_CHAT_SESSIONS_TABLE,
    CREATE_CHAT_MESSAGES_TABLE,
]
