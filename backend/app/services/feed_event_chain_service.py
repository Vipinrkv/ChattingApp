import hashlib
import json
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.feed_event_chain import FeedEventChain


class FeedEventChainService:
    @staticmethod
    async def log_event(
        session: AsyncSession,
        event_type: str,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: dict,
    ) -> FeedEventChain:
        # Get last event to link the chain
        stmt = select(FeedEventChain).order_by(FeedEventChain.timestamp.desc(), FeedEventChain.id.desc()).limit(1)
        res = await session.execute(stmt)
        last_event = res.scalar_one_or_none()

        previous_hash = last_event.hash if last_event else None
        event_uuid = uuid.uuid4()
        timestamp = datetime.utcnow()

        # Deterministic serialization for JSON payload
        payload_str = json.dumps(payload, sort_keys=True)
        hash_input = (
            f"{event_uuid}"
            f"{event_type}"
            f"{event_id}"
            f"{user_id}"
            f"{timestamp.isoformat()}"
            f"{payload_str}"
            f"{previous_hash or ''}"
        )
        current_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        event = FeedEventChain(
            id=event_uuid,
            event_type=event_type,
            event_id=event_id,
            user_id=user_id,
            timestamp=timestamp,
            payload=payload,
            previous_hash=previous_hash,
            hash=current_hash,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event

    @staticmethod
    async def verify_chain(session: AsyncSession) -> bool:
        stmt = select(FeedEventChain).order_by(FeedEventChain.timestamp.asc(), FeedEventChain.id.asc())
        res = await session.execute(stmt)
        events = res.scalars().all()

        expected_previous_hash = None
        for event in events:
            payload_str = json.dumps(event.payload, sort_keys=True)
            hash_input = (
                f"{event.id}"
                f"{event.event_type}"
                f"{event.event_id}"
                f"{event.user_id}"
                f"{event.timestamp.isoformat()}"
                f"{payload_str}"
                f"{event.previous_hash or ''}"
            )
            recalculated_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            if recalculated_hash != event.hash:
                return False
            if event.previous_hash != expected_previous_hash:
                return False
            expected_previous_hash = event.hash

        return True
