import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_feed_control import UserFeedControl
from app.schemas.user_feed_control_schema import UserFeedControlUpdate


class UserFeedControlService:
    @staticmethod
    async def get_controls(session: AsyncSession, user_id: uuid.UUID) -> UserFeedControl:
        stmt = select(UserFeedControl).where(UserFeedControl.user_id == user_id)
        res = await session.execute(stmt)
        control = res.scalar_one_or_none()

        if not control:
            control = UserFeedControl(
                user_id=user_id,
                muted_words=[],
                ranking_mode="engagement",
                sensitive_content_hidden=True,
                data_saver_enabled=False,
            )
            session.add(control)
            await session.commit()
            await session.refresh(control)
        return control

    @staticmethod
    async def update_controls(
        session: AsyncSession,
        user_id: uuid.UUID,
        update_data: UserFeedControlUpdate,
    ) -> UserFeedControl:
        control = await UserFeedControlService.get_controls(session, user_id)

        if update_data.muted_words is not None:
            control.muted_words = update_data.muted_words
        if update_data.ranking_mode is not None:
            control.ranking_mode = update_data.ranking_mode
        if update_data.sensitive_content_hidden is not None:
            control.sensitive_content_hidden = update_data.sensitive_content_hidden
        if update_data.data_saver_enabled is not None:
            control.data_saver_enabled = update_data.data_saver_enabled

        await session.commit()
        await session.refresh(control)
        return control
