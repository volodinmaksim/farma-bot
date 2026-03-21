from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.db_helper import db_helper
from db.models import FarmaEvent, FarmaUser
from exception.db import UserNotFound


async def add_user(tg_id: int, username: str, utm_mark: str) -> None:
    async with db_helper.session() as session:
        user = await get_user(tg_id, session=session)
        if user is None:
            session.add(FarmaUser(tg_id=tg_id, username=username, utm_mark=utm_mark))
            await session.commit()


async def get_user(tg_id: int, session: AsyncSession | None = None):
    if session is None:
        async with db_helper.session() as session:
            query = select(FarmaUser).where(FarmaUser.tg_id == tg_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    query = select(FarmaUser).where(FarmaUser.tg_id == tg_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def add_event(tg_id: int, event_name: str) -> None:
    async with db_helper.session() as session:
        user_query = await session.execute(select(FarmaUser.id).where(FarmaUser.tg_id == tg_id))
        internal_user_id = user_query.scalar()

        if internal_user_id is None:
            raise UserNotFound

        session.add(FarmaEvent(user_id=internal_user_id, event_name=event_name))
        await session.commit()
