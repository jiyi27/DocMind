"""One-time migration to add last_message_preview to chat_sessions.

Usage:
  python /Users/david/codes/agent/DocMind/backend/scripts/migrate_add_chat_preview.py
"""

from __future__ import annotations

import sqlite3

DB_PATH = "/Users/david/codes/agent/DocMind/backend/docmind.db"


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cursor.fetchall())


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        if not column_exists(cur, "chat_sessions", "last_message_preview"):
            cur.execute("ALTER TABLE chat_sessions ADD COLUMN last_message_preview TEXT DEFAULT ''")
            conn.commit()
            print("Migration applied: chat_sessions.last_message_preview added")
        else:
            print("No action: chat_sessions.last_message_preview already exists")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
