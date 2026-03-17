import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


async def migrate():
    """Add retrieval_mode column to documents table."""
    from docmind.db.database import create_async_connection

    print("Running migration: Add retrieval_mode column to documents...")
    db = await create_async_connection()
    try:
        await db.execute(
            "ALTER TABLE documents ADD COLUMN retrieval_mode TEXT DEFAULT 'chunk'"
        )
        await db.commit()
        print("Migration completed successfully.")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("Migration already applied. Column exists.")
        else:
            print(f"Error during migration: {e}")
            await db.rollback()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(migrate())
