#!/usr/bin/env python
"""Check local database status and migration."""
import asyncio
import sys
from sqlalchemy import text
from app.core.database import engine

async def check_database():
    try:
        async with engine.begin() as conn:
            # Check if alembic_version table exists
            result = await conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version');"
            ))
            has_alembic = result.scalar()
            
            if not has_alembic:
                print("❌ alembic_version table does not exist")
                print("   Database has not been initialized yet")
                return False
            
            # Get current revision (check the alembic_version table structure)
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='alembic_version' ORDER BY ordinal_position;"
            ))
            columns = [col[0] for col in result.fetchall()]
            
            if not columns:
                print("❌ alembic_version table has no columns")
                return False
            
            # Use the first column (should be version_num)
            col_name = columns[0]
            result = await conn.execute(text(f"SELECT {col_name} FROM alembic_version;"))
            current_rev = result.scalar()
            print(f"✅ Database connection successful!")
            print(f"✅ Current migration revision: {current_rev}")
            
            # List all tables
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
            ))
            tables = result.fetchall()
            print(f"\n📊 Database tables ({len(tables)}):")
            for table in tables:
                print(f"   ✓ {table[0]}")
            
            return True
            
    except Exception as e:
        print(f"❌ Database Error: {type(e).__name__}")
        print(f"   {str(e)}")
        print(f"\n💡 Make sure:")
        print(f"   1. PostgreSQL is running")
        print(f"   2. Database 'clinic_saas' exists")
        print(f"   3. .env file has correct DATABASE_URL")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_database())
    sys.exit(0 if success else 1)
