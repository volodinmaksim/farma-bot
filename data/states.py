from aiogram.fsm.state import State, StatesGroup


class StoryState(StatesGroup):
    waiting_for_advertising_consent = State()
    waiting_for_subscription = State()
