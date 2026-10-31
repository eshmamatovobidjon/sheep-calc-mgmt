from aiogram import Router

from sheepbot.bot import client_picker
from sheepbot.bot.handlers import clients, common, payments, template, upload, users

# Order matters: common first (/start, /menu, /cancel win in any state), fallback last.
ROUTERS: list[Router] = [
    common.router,
    users.router,
    template.router,
    upload.router,
    payments.router,
    clients.router,
    client_picker.router,
    common.fallback_router,
]
