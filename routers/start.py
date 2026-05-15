from contextlib import suppress

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from data.states import StoryState
from data.story_content import (
    text_advertising_consent,
    text_hello,
    text_subscription_is_confirmed,
)
from db.crud import add_event, add_user
from exception.db import UserNotFound
from loader import logger

router = Router(name="start_router")


def get_subscription_channels() -> tuple[tuple[int, str], ...]:
    channels: list[tuple[int, str]] = [
        (settings.CHAT_ID_TO_CHECK, settings.CHAT_URL),
    ]

    if settings.SECOND_CHAT_ID_TO_CHECK and settings.SECOND_CHAT_URL:
        channels.append((settings.SECOND_CHAT_ID_TO_CHECK, settings.SECOND_CHAT_URL))

    return tuple(channels)


def build_consent_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Разрешаю", callback_data="allow_advertising")
    builder.adjust(1)
    return builder.as_markup()


def build_subscription_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, (_, url) in enumerate(get_subscription_channels(), start=1):
        builder.button(text=f"{index}. Подписаться", url=url)

    builder.button(
        text=f"{len(get_subscription_channels()) + 1}. Я подписался!",
        callback_data="check_sub",
    )
    builder.adjust(1)
    return builder.as_markup()


async def is_subscribed_to_all_channels(user_id: int) -> bool:
    from loader import bot

    subscriptions = [
        await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        for chat_id, _ in get_subscription_channels()
    ]
    return all(
        user_sub.status in ["member", "administrator", "creator"]
        for user_sub in subscriptions
    )


async def add_event_safely(*, tg_id: int, event_name: str) -> None:
    try:
        await add_event(tg_id=tg_id, event_name=event_name)
    except UserNotFound:
        logger.error("Ошибка: пользователь с tg_id %s не найден в базе.", tg_id)


@router.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    await state.set_state(StoryState.waiting_for_advertising_consent)

    utm = (command.args or "").strip()
    user_name = (
        message.from_user.username
        or f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    )
    await add_user(tg_id=message.from_user.id, username=user_name, utm_mark=utm)

    await message.answer(
        text_advertising_consent,
        reply_markup=build_consent_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(
    StoryState.waiting_for_advertising_consent, F.data == "allow_advertising"
)
async def accept_advertising(callback: types.CallbackQuery, state: FSMContext):
    with suppress(TelegramBadRequest):
        await callback.answer()

    await add_event_safely(
        tg_id=callback.from_user.id,
        event_name="advertising_consent",
    )
    await state.set_state(StoryState.waiting_for_subscription)
    await callback.message.answer(
        text_hello,
        reply_markup=build_subscription_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(StoryState.waiting_for_subscription, F.data == "check_sub")
async def verify_subscription(callback: types.CallbackQuery, state: FSMContext):
    with suppress(TelegramBadRequest):
        await callback.answer()

    if await is_subscribed_to_all_channels(callback.from_user.id):
        await add_event_safely(
            tg_id=callback.from_user.id,
            event_name='Получить файл: "Материалы за подписку"',
        )
        await state.clear()
        await callback.message.answer(text_subscription_is_confirmed, parse_mode="HTML")
        await callback.message.answer(f"Ваша ссылка: {settings.YDISK_LINK}")
        return

    await callback.message.answer("Вы еще не подписались на все каналы!")
