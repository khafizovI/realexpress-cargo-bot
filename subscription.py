"""Mandatory channel subscription helpers."""
from urllib.parse import urlparse

from aiogram import Bot, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database import db


PLACEHOLDER_CHANNELS = {"", "@yourchannel", "yourchannel", "https://t.me/yourchannel"}


def normalize_channel(value: str) -> tuple[str, str | None]:
    """Return a user-facing link and a chat id usable by get_chat_member."""
    raw = (value or "").strip()
    if not raw:
        return "", None

    if raw.startswith("@"):
        username = raw.split()[0]
        return f"https://t.me/{username[1:]}", username

    if raw.startswith("t.me/"):
        raw = f"https://{raw}"

    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")
        if host in {"t.me", "telegram.me"} and path and not path.startswith(("+", "joinchat/", "c/")):
            username = path.split("/")[0]
            return raw, f"@{username}"
        return raw, None

    username = raw.split()[0].lstrip("@")
    return f"https://t.me/{username}", f"@{username}"


def get_required_channel() -> tuple[str, str | None]:
    channel = (db.get_setting("channel_username") or "").strip()
    if channel.lower() in PLACEHOLDER_CHANNELS:
        return "", None
    return normalize_channel(channel)


def subscription_keyboard(channel_link: str, lang: str) -> types.InlineKeyboardMarkup:
    check_text = "✅ Obunani tekshirish" if lang == "uz" else "✅ Проверить подписку"
    join_text = "📢 Kanalga obuna bo'lish" if lang == "uz" else "📢 Подписаться на канал"
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=join_text, url=channel_link)],
            [types.InlineKeyboardButton(text=check_text, callback_data="check_subscription")],
        ]
    )


async def is_subscribed(bot: Bot, user_id: int, channel_chat_id: str | None) -> bool:
    if not channel_chat_id:
        return True
    try:
        member = await bot.get_chat_member(channel_chat_id, user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return member.status not in {"left", "kicked"}


async def send_subscription_required(message: types.Message, lang: str) -> None:
    channel_link, _ = get_required_channel()
    text = (
        "Botdan foydalanish uchun avval kanalimizga obuna bo'ling."
        if lang == "uz"
        else "Чтобы пользоваться ботом, сначала подпишитесь на наш канал."
    )
    await message.answer(text, reply_markup=subscription_keyboard(channel_link, lang))
