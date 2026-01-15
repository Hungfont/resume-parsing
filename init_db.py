"""Initialize database schema for the matching MVP.

Creates all tables needed for the job-candidate matching system.
Run this before starting the API server.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from be.db import engine
from be.models import Base
from be.config import settings
from sqlalchemy import text


async def init_database():
    """Create all database tables."""
    print(f"Initializing database: {settings.db.url}")
    print("Creating tables...")
    
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("✓ Enabled pgvector extension")
        
        # Drop all tables (for clean start)
        await conn.run_sync(Base.metadata.drop_all)
        print("✓ Dropped existing tables")
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Created all tables")
    
    print("\n✅ Database initialization complete!")
    print(f"Tables created: {', '.join(Base.metadata.tables.keys())}")


async def main():
    """Main entry point."""
    try:
        await init_database()
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
