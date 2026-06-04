import uuid
import asyncio
from sqlalchemy import text
from app.database.connection import AsyncSessionLocal

async def test_insert():
    async with AsyncSessionLocal() as s:
        mid = uuid.uuid4()
        uid = uuid.uuid4()
        print('uids', mid, uid)
        await s.execute(
            text(
                "INSERT INTO users (id, firebase_uid, username, role, is_active, is_shadow_banned, is_muted, is_suspended, created_at, updated_at) "
                "VALUES (:id, :firebase_uid, :username, 'user', true, false, false, false, now(), now()) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": str(uid), "firebase_uid": str(uid), "username": f"user_{uid.hex[:8]}"},
        )
        await s.execute(
            text(
                "INSERT INTO messages (id, sender_id, receiver_id, content) "
                "VALUES (:mid, :sid, :rid, :content) ON CONFLICT (id) DO NOTHING"
            ),
            {"mid": str(mid), "sid": str(uid), "rid": str(uid), "content": ""},
        )
        await s.flush()
        result = await s.execute(text("SELECT id, sender_id, receiver_id, content FROM messages WHERE id=:mid"), {"mid": str(mid)})
        row = result.first()
        print('row', row)
        result2 = await s.execute(text("SELECT id FROM users WHERE id=:uid"), {"uid": str(uid)})
        print('user', result2.first())

asyncio.run(test_insert())
