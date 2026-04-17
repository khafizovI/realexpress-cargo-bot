"""Entry point for the cargo Telegram bot."""
import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message

import config
from database import init_db, db
from handlers import user, admin
from keyboards import main_menu


logging.basicConfig(level=logging.INFO)


async def on_startup(bot: Bot):
    """Initialize database and attach runtime data."""
    init_db()
    # Attach admin chat ids for complaints
    bot.admin_chat_ids = config.ADMIN_CHAT_IDS or config.ADMIN_IDS or []
    bot.complaint_map = {}
    bot.start_sticker = config.START_STICKER
    bot.admin_sticker = config.ADMIN_STICKER
    logging.info("Bot started, admin_chat_ids=%s", bot.admin_chat_ids)


async def handle_admin_reply(message: Message):
    """Route admin replies back to users for complaints."""
    bot = message.bot
    admin_chats = getattr(bot, "admin_chat_ids", []) or []
    if message.chat.id not in admin_chats:
        return
    if not getattr(bot, "complaint_map", None):
        return
    if not message.reply_to_message:
        return
    key = (message.chat.id, message.reply_to_message.message_id)
    target_user_id = bot.complaint_map.get(key)
    if not target_user_id:
        return
    try:
        await bot.send_message(chat_id=target_user_id, text=message.text)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to forward admin reply: %s", exc)


def register_routers(dp: Dispatcher):
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.message.register(
        handle_admin_reply,
        lambda m: m.chat.id in (getattr(m.bot, "admin_chat_ids", []) or []) and m.reply_to_message,
    )


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_routers(dp)
    await on_startup(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
