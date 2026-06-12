import asyncio
import sys
import os
import uuid
from pathlib import Path

# Add the parent and backend directories to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database.connection import init_db, get_db_session, engine
from app.services.feed_service import FeedService
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    await init_db()
    # Create an async session
    async_session = AsyncSession(engine)
    user_id = "52e67653-c133-428b-8ee5-61dc38cf17a8"
    print(f"Testing FeedService.get_feed for user: {user_id}")
    try:
        feed = await FeedService.get_feed(async_session, user_id, limit=12)
        print("Success! Loaded feed items:", len(feed))
    except Exception as exc:
        import traceback
        print("Error during get_feed:")
        traceback.print_exc()

    print("\nTesting FeedService.search_feed:")
    try:
        results = await FeedService.search_feed(async_session, user_id, search_term="#", limit=12)
        print("Success! Loaded search items:", len(results))
    except Exception as exc:
        import traceback
        print("Error during search_feed:")
        traceback.print_exc()

    await async_session.close()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
