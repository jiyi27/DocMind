"""
DDL statements for all database tables.
"""

CREATE_KNOWLEDGE_BASES_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id           TEXT PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description  TEXT DEFAULT '',
    created_at   TEXT NOT NULL
);
"""

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
    created_at  TEXT NOT NULL
);
"""

ALL_TABLES = [
    CREATE_KNOWLEDGE_BASES_TABLE,
    CREATE_USERS_TABLE,
    CREATE_DOCUMENTS_TABLE,
]
