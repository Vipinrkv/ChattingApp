# scratch/check_db.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres.byopqfesnwdjpwxtpvma:WJBO6UsKYL3SRrta@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

async def main():
    print("Connecting to database:", DATABASE_URL)
    engine = create_async_engine(DATABASE_URL, connect_args={"statement_cache_size": 0})
    async with engine.connect() as conn:
        print("\n--- Listing Tables ---")
        tables_res = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ))
        tables = [row[0] for row in tables_res.fetchall()]
        print("Tables:", tables)

        print("\n--- Checking User Count ---")
        try:
            users_res = await conn.execute(text("SELECT count(*) FROM users"))
            print("Users count:", users_res.scalar())
        except Exception as e:
            print("Error checking users:", e)

        print("\n--- Checking Friends Count ---")
        try:
            friends_res = await conn.execute(text("SELECT count(*) FROM friends"))
            print("Friends count:", friends_res.scalar())
        except Exception as e:
            print("Error checking friends:", e)

        print("\n--- Checking Alembic Version ---")
        try:
            alembic_res = await conn.execute(text("SELECT * FROM alembic_version"))
            print("Alembic version:", alembic_res.fetchall())
        except Exception as e:
            print("Error checking alembic:", e)

        print("\n--- Listing Users ---")
        try:
            users_list = await conn.execute(text("SELECT id, firebase_uid, username, role FROM users LIMIT 10"))
            print("Users:")
            for row in users_list.fetchall():
                print(row)
        except Exception as e:
            print("Error listing users:", e)

    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
