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
        print("Dropping application tables...")
        tables = [
            "alembic_version", "post_reposts", "post_likes", "post_comments", 
            "group_messages", "group_posts", "group_members", "chat_settings", 
            "posts", "messages", "blocks", "followers", "friends", "groups", "users",
            "mfa_setups", "user_sessions", "user_devices", "login_history", 
            "suspicious_activities", "csrf_tokens", "ip_reputations", 
            "rate_limit_entries", "security_audit_logs"
        ]
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
            
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
