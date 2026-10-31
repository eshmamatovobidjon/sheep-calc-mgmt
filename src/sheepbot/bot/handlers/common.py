from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from sheepbot.bot import texts

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(texts.START_PLACEHOLDER)
