from aiogram import Router

from sheepbot.bot.handlers import common, template, upload, users

# Order matters: common first (/start, /menu, /cancel win in any state), fallback last.
ROUTERS: list[Router] = [
    common.router,
    users.router,
    template.router,
    upload.router,
    common.fallback_router,
]
