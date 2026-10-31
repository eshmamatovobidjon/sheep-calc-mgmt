"""/template and the "Шаблон" button: send the blank trip template."""

from functools import cache

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from sheepbot.bot import texts
from sheepbot.bot.filters import HasPermission, Perm
from sheepbot.excel.template_builder import build_template
from sheepbot.excel.template_spec import TEMPLATE_FILE_NAME

router = Router(name="template")
router.message.filter(HasPermission(Perm.UPLOAD))


@cache
def _blank_template() -> bytes:
    return build_template()


@router.message(Command("template"))
@router.message(F.text == texts.BTN_TEMPLATE)
async def cmd_template(message: Message, state: FSMContext) -> None:
    await state.clear()
    document = BufferedInputFile(_blank_template(), filename=TEMPLATE_FILE_NAME)
    await message.answer_document(document, caption=texts.TEMPLATE_CAPTION)
