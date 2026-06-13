# scratch/test_user_service.py
import asyncio
import uuid
import sys
from pathlib import Path

# Add backend to sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.database.connection import engine, get_db_session
from app.services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    print("Testing UserService.get_user_by_id...")
    user_id = "266d3e4c-8f66-47cb-b553-c58243a22af1"
    async with AsyncSession(engine) as session:
        try:
            print("Calling get_user_by_id...")
            user = await UserService.get_user_by_id(session, user_id)
            print("Success! User:", user)
            if user:
                print("Username:", user.username)
        except Exception as e:
            import traceback
            print("Error occurred:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
