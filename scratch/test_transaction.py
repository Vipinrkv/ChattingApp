# scratch/test_transaction.py
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.database.connection import engine
from app.core.transaction import run_transaction
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def main():
    print("Testing transaction behavior...")
    async with AsyncSession(engine) as session:
        # 1. Trigger autobegin
        print("Executing a select to trigger autobegin...")
        await session.execute(select(User))
        print("In transaction:", session.in_transaction())

        # 2. Try to run_transaction
        async def work():
            print("Inside work function")
            return 42

        try:
            print("Calling run_transaction...")
            res = await run_transaction(session, work)
            print("Result:", res)
        except Exception as e:
            import traceback
            print("Error:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
