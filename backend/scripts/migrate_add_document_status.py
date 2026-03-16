import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path so we can import docmind modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


async def migrate():
    """Add status, error_message, file_path, and strict_mode columns to documents table."""
    from docmind.db.database import get_db

    print("Running migration: Add document status fields...")
    async with get_db() as db:
        try:
            await db.execute(
                "ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending'"
            )
            await db.execute(
                "ALTER TABLE documents ADD COLUMN error_message TEXT DEFAULT ''"
            )
            await db.execute(
                "ALTER TABLE documents ADD COLUMN file_path TEXT DEFAULT ''"
            )
            await db.execute(
                "ALTER TABLE documents ADD COLUMN strict_mode INTEGER DEFAULT 1"
            )

            # Since existing docs are likely already done, let's mark them as completed
            await db.execute(
                "UPDATE documents SET status = 'completed' WHERE status = 'pending'"
            )
            await db.commit()
            print("Migration completed successfully.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Migration already applied. Columns exist.")
            else:
                print(f"Error during migration: {e}")
                await db.rollback()


if __name__ == "__main__":
    asyncio.run(migrate())
