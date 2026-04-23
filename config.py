"""Basic configuration for the cargo bot."""
import os
import re


def _parse_ids(raw: str):
    # Parse numeric IDs from a raw string
    return [int(x) for x in re.findall(r"\d+", raw or "")]


def _valid_ids(ids):
    # Drop non-positive IDs to avoid Telegram errors (e.g., "0")
    return [i for i in ids if i > 0]


# Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8571910365:AAGLD41TJ0B-xnFceTA84QrI3W9YvN7Tz88")

# Path to SQLite database file
DB_PATH = os.getenv("DB_PATH", "cargo_bot.db")

# Admins (can be comma/space separated)
ADMIN_IDS = _valid_ids(
    _parse_ids(os.getenv("ADMIN_ID", "802978542 7847798100"))
)
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else None

# Chat IDs where complaints will be forwarded (accepts multiple)
ADMIN_CHAT_IDS = _valid_ids(_parse_ids(os.getenv("ADMIN_CHAT_ID", os.getenv("ADMIN_ID", "0"))))
ADMIN_CHAT_ID = ADMIN_CHAT_IDS[0] if ADMIN_CHAT_IDS else None

# Default admin username for user-facing hints
DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@Realexpress_admin")

# Supported languages
LANGUAGES = ["uz", "ru"]

# Optional stickers (valid sticker file_id). Leave empty to disable.
# Defaults use a common sticker; replace if you prefer your own.
START_STICKER = os.getenv("START_STICKER", "CAACAgIAAxkBAAEBbBRmXgLZZQzQ_EimeISFRCGDpa2grAACpQADwDZPE5Z_G1HsRvN7LgQ")
ADMIN_STICKER = os.getenv("ADMIN_STICKER", START_STICKER)
