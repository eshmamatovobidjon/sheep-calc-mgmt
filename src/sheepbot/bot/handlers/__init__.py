from aiogram import Router

from sheepbot.bot.handlers import common

# Order matters: the common router (with the fallback from Phase 02) stays last.
ROUTERS: list[Router] = [common.router]
