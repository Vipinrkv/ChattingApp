# scratch/test_friend_respond.py
import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

import uuid
from sqlalchemy import select
from app.database.connection import get_db_session, AsyncSessionLocal
from app.models.friend import FriendRequest, FriendRequestStatus
from app.models.user import User
from app.services.friend_service import respond_to_friend_request
from app.schemas.friend_schema import FriendRequestResponse

async def main():
    async with AsyncSessionLocal() as session:
        # Get or create a user and friend request to test
        user_res = await session.execute(select(User).limit(2))
        users = user_res.scalars().all()
        if len(users) < 2:
            print("Need at least 2 users in db to test.")
            return
        
        user_a, user_b = users[0], users[1]
        print(f"Testing with User A: {user_a.username} ({user_a.id}) and User B: {user_b.username} ({user_b.id})")
        
        # Create a pending request from A to B
        req = FriendRequest(
            requester_id=user_a.id,
            addressee_id=user_b.id,
            status=FriendRequestStatus.PENDING
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)
        
        print(f"Created pending request {req.id}")
        
        try:
            # Try to respond to it
            updated_req = await respond_to_friend_request(session, user_b.id, req.id, "accept")
            print("respond_to_friend_request finished successfully.")
            
            # Try to serialize it
            dump = FriendRequestResponse.from_orm(updated_req)
            print("Serialization successful:", dump.model_dump())
            
        except Exception as e:
            import traceback
            traceback.print_exc()
        finally:
            # Clean up the test request
            await session.delete(req)
            await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
