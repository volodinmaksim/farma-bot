from contextlib import suppress

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest

from config import settings
from data.story_content import text_subscription_is_confirmed
from db.crud import add_event
from exception.db import UserNotFound
from loader import bot, logger

CHECK_CALLBACK_DATA = "check_second_channel_broadcast_sub"
CHECK_CLICK_EVENT = "click_check_second_channel_broadcast_subscription"
FILE_RECEIVED_EVENT = 'Получить файл: "Материалы за подписку"'

router = Router(name="second_channel_broadcast_router")


async def add_event_safely(*, tg_id: int, event_name: str) -> None:
    try:
        await add_event(tg_id=tg_id, event_name=event_name)
    except UserNotFound:
        logger.error("Ошибка: пользователь с tg_id %s не найден в базе.", tg_id)


async def is_subscribed_to_second_channel(user_id: int) -> bool:
    if settings.SECOND_CHAT_ID_TO_CHECK is None:
        raise RuntimeError("SECOND_CHAT_ID_TO_CHECK is not configured")

    user_sub = await bot.get_chat_member(
        chat_id=settings.SECOND_CHAT_ID_TO_CHECK,
        user_id=user_id,
    )
    return user_sub.status in ["member", "administrator", "creator"]


@router.callback_query(F.data == CHECK_CALLBACK_DATA)
async def verify_second_channel_broadcast_subscription(
    callback: types.CallbackQuery,
) -> None:
    await add_event_safely(
        tg_id=callback.from_user.id,
        event_name=CHECK_CLICK_EVENT,
    )

    if not await is_subscribed_to_second_channel(callback.from_user.id):
        with suppress(TelegramBadRequest):
            await callback.answer(
                "Подпишитесь на канал Максима Резникова и нажмите «Проверить» еще раз.",
                show_alert=False,
            )
        return

    with suppress(TelegramBadRequest):
        await callback.answer()
    await add_event_safely(
        tg_id=callback.from_user.id,
        event_name=FILE_RECEIVED_EVENT,
    )
    await callback.message.answer(text_subscription_is_confirmed, parse_mode="HTML")
    await callback.message.answer(f"Ваша ссылка: {settings.YDISK_LINK}")
