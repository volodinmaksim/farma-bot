from aiogram import Bot, F, Router, types
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from data.story_content import text_after_link, text_hello, text_subscription_is_confirmed
from db.crud import add_event, add_user
from exception.db import UserNotFound
from loader import logger

router = Router(name="start_router")


@router.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    utm = (command.args or "").strip()
    user_name = (
        message.from_user.username
        or f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    )
    await add_user(tg_id=message.from_user.id, username=user_name, utm_mark=utm)

    builder = InlineKeyboardBuilder()
    builder.button(text="1. Подписаться", url=settings.CHAT_URL)
    builder.button(text="2. Я подписался!", callback_data="check_sub")
    builder.adjust(1)

    await message.answer(text_hello, reply_markup=builder.as_markup())


@router.callback_query(F.data == "check_sub")
async def verify_subscription(callback: types.CallbackQuery, bot: Bot):
    user_sub = await bot.get_chat_member(
        chat_id=settings.CHAT_ID_TO_CHECK,
        user_id=callback.from_user.id,
    )

    if user_sub.status in ["member", "administrator", "creator"]:
        try:
            await add_event(
                tg_id=callback.from_user.id,
                event_name='Получить файл: "Гайд по серотониновому синдрому"',
            )
        except UserNotFound:
            logger.error("Ошибка: пользователь с tg_id %s не найден в базе.", callback.from_user.id)

        await callback.message.answer(text_subscription_is_confirmed, parse_mode="HTML")
        await callback.message.answer(f"Ваша ссылка: {settings.YDISK_LINK}")
        await callback.message.answer(text_after_link, parse_mode="HTML")
        await callback.answer()
        return

    await callback.answer("Вы еще не подписались на канал!", show_alert=True)
