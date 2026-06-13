# scratch/cleanup_db.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Use port 6543 for Supabase connection pooler
DATABASE_URL = "postgresql+asyncpg://postgres.byopqfesnwdjpwxtpvma:WJBO6UsKYL3SRrta@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

async def main():
    print("Connecting to database:", DATABASE_URL)
    engine = create_async_engine(DATABASE_URL, connect_args={"statement_cache_size": 0})
    async with engine.connect() as conn:
        print("Fetching and dropping all application tables dynamically...")
        tables_res = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        ))
        tables = [row[0] for row in tables_res.fetchall()]
        print(f"Found {len(tables)} tables to drop.")
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS \"{table}\" CASCADE;"))
            
        print("Dropping old enum types...")
        enums = [
            "friendrequeststatus", "postvisibility", "mfamethod", 
            "devicetype", "sessionstatus", "loginstatus"
        ]
        for enum in enums:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum} CASCADE;"))
            
        await conn.commit()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
