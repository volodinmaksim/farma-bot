import argparse
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import exists, select

from config import settings
from db.crud import add_event
from db.db_helper import db_helper
from db.models import FarmaEvent, FarmaUser
from loader import bot, redis

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
DEFAULT_RUN_AT = datetime(2026, 5, 16, 12, 24, tzinfo=MOSCOW_TZ)
BROADCAST_SENT_EVENT = "second_channel_subscription_broadcast_sent_2026_05_16"
CHECK_CALLBACK_DATA = "check_second_channel_broadcast_sub"

BROADCAST_TEXT = """
Привет.
Мы подготовили чек-лист <b>"5 шагов к оценке риска суицида"</b>

Разговор о суицидальных мыслях может быть трудным: для клиента он нередко связан со стыдом или страхом. Иногда человек говорит не прямо, а завуалированно, например: «плохие мысли», «всякое лезет в голову».

<b>Зачем нужен протокол?</b>
🔹 Заменяет интуитивные решения на профессиональный алгоритм;
🔹 Помогает не пропустить скрытые признаки риска;
🔹 Даёт опору, чтобы действовать спокойно и уверенно.

Этот чек-лист поможет психологу поддержать клиента и мягко пройти через основные этапы оценки риска.

🎁 <b>Получите файл за подписку на Telegram канал Максима Резникова.</b>
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def build_keyboard():
    if not settings.SECOND_CHAT_URL:
        raise RuntimeError("SECOND_CHAT_URL is not configured")

    builder = InlineKeyboardBuilder()
    builder.button(text="Подписаться", url=settings.SECOND_CHAT_URL)
    builder.button(text="Проверить", callback_data=CHECK_CALLBACK_DATA)
    builder.adjust(1)
    return builder.as_markup()


async def load_recipients(*, include_already_sent: bool) -> list[int]:
    async with db_helper.session_factory() as session:
        sent_exists = (
            exists()
            .where(
                FarmaEvent.user_id == FarmaUser.id,
                FarmaEvent.event_name == BROADCAST_SENT_EVENT,
            )
            .correlate(FarmaUser)
        )
        stmt = select(FarmaUser.tg_id).distinct().order_by(FarmaUser.tg_id)
        if not include_already_sent:
            stmt = stmt.where(~sent_exists)

        result = await session.execute(stmt)
        return list(result.scalars())


async def wait_until(run_at: datetime) -> None:
    now = datetime.now(MOSCOW_TZ)
    if run_at <= now:
        logger.info("Run time is in the past, sending immediately.")
        return

    delay_seconds = (run_at - now).total_seconds()
    logger.info("Waiting until %s Moscow time.", run_at.isoformat())
    await asyncio.sleep(delay_seconds)


async def send_broadcast_message_to_chat(chat_id: int) -> None:
    await bot.send_message(
        chat_id=chat_id,
        text=BROADCAST_TEXT,
        reply_markup=build_keyboard(),
        parse_mode="HTML",
    )


async def send_test_message() -> None:
    if settings.ADMIN_ID is None:
        raise RuntimeError("ADMIN_ID is not configured")

    await send_broadcast_message_to_chat(settings.ADMIN_ID)
    logger.info("Test message sent to ADMIN_ID=%s.", settings.ADMIN_ID)


async def send_broadcast(*, dry_run: bool, include_already_sent: bool) -> None:
    recipients = await load_recipients(include_already_sent=include_already_sent)
    logger.info("Recipients found: %s", len(recipients))

    if dry_run:
        logger.info("Dry run recipients: %s", recipients)
        return

    sent = 0
    failed = 0

    for tg_id in recipients:
        try:
            await send_broadcast_message_to_chat(tg_id)
            await add_event(tg_id=tg_id, event_name=BROADCAST_SENT_EVENT)
            sent += 1
            logger.info("Sent to %s", tg_id)
            await asyncio.sleep(0.05)
        except TelegramForbiddenError:
            failed += 1
            logger.warning("User %s blocked the bot.", tg_id)
        except TelegramAPIError:
            failed += 1
            logger.exception("Telegram error while sending to %s", tg_id)

    logger.info("Done. Sent: %s. Failed: %s.", sent, failed)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send scheduled second-channel subscription broadcast to all bot users."
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Send immediately instead of waiting until 2026-05-16 12:24 MSK.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print recipient count and ids, do not send messages.",
    )
    parser.add_argument(
        "--include-already-sent",
        action="store_true",
        help="Send even to users who already have broadcast sent event.",
    )
    parser.add_argument(
        "--test-admin",
        action="store_true",
        help="Send the broadcast message only to ADMIN_ID immediately.",
    )
    args = parser.parse_args()

    try:
        if args.test_admin:
            await send_test_message()
            return

        if not args.now and not args.dry_run:
            await wait_until(DEFAULT_RUN_AT)

        await send_broadcast(
            dry_run=args.dry_run,
            include_already_sent=args.include_already_sent,
        )
    finally:
        await bot.session.close()
        await db_helper.engine.dispose()
        if redis is not None:
            await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
