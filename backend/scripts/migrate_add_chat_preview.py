"""One-time migration to add last_message_preview to chat_sessions.

Usage:
  python /Users/david/codes/agent/DocMind/backend/scripts/migrate_add_chat_preview.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to sys.path so we can import docmind modules.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def column_exists(cursor: object, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cursor.fetchall())


def main() -> None:
    from docmind.db.database import create_sync_connection

    conn = create_sync_connection()
    try:
        cur = conn.cursor()
        if not column_exists(cur, "chat_sessions", "last_message_preview"):
            cur.execute(
                "ALTER TABLE chat_sessions ADD COLUMN last_message_preview TEXT DEFAULT ''"
            )
            conn.commit()
            print("Migration applied: chat_sessions.last_message_preview added")
        else:
            print("No action: chat_sessions.last_message_preview already exists")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
