from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mini_analysis.constants import STATE_KEY_AWAITING_MINI_PHOTO


class AwaitingMiniPhoto(BaseFilter):
    """
    True only for photo messages sent by a user who is currently inside the
    free mini-analysis flow (flag set by the CB_GET_MINI_ANALYSIS callback).

    This lets `mini_analysis.handlers.router` be registered *before*
    `handlers.photo.router` without ever intercepting a normal paid-flow
    photo: when the flag isn't set, this filter returns False and aiogram
    falls through to the next router as usual.
    """

    async def __call__(self, message: Message, state: FSMContext) -> bool:
        if not message.photo:
            return False
        data = await state.get_data()
        return bool(data.get(STATE_KEY_AWAITING_MINI_PHOTO, False))
