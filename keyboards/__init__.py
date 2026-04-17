"""Reply keyboards for users and admins."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def language_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbek"), KeyboardButton(text="🇷🇺 Русский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    uz_buttons = [
        "🆔 ID olish",
        "ℹ️ Biz haqimizda",
        "💴 Yuan",
        "📨 Shikoyat yuborish",
        "💰 Narxlar",
        "📍 Manzil",
        "🎯 Trek kod tekshirish",
    ]
    ru_buttons = [
        "🆔 Получить ID",
        "ℹ️ О нас",
        "💴 Юань",
        "📨 Отправить жалобу",
        "💰 Цены",
        "📍 Адрес",
        "🎯 Проверить трек-код",
    ]
    labels = uz_buttons if lang == "uz" else ru_buttons
    keyboard = [
        [KeyboardButton(text=labels[i]), KeyboardButton(text=labels[i + 1])]
        for i in range(0, len(labels) - 1, 2)
    ]
    if len(labels) % 2 == 1:
        keyboard.append([KeyboardButton(text=labels[-1])])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def tracking_menu(lang: str) -> ReplyKeyboardMarkup:
    back_text = "⬅️ Orqaga" if lang == "uz" else "⬅️ Назад"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=back_text)]],
        resize_keyboard=True,
    )


def admin_menu(lang: str) -> ReplyKeyboardMarkup:
    uz_buttons = [
        "➕ Trek kod qo'shish",
        "🗑 Trek kod o'chirish",
        "📊 Statistika",
        "📄 Treklar ro'yxati",
        "📢 E'lon yuborish",
        "🔗 Kanal ulash",
        "👤 Admin qo'shish",
        "ℹ️ Biz haqimizda (edit)",
        "💰 Narxlar (edit)",
        "📍 Manzil (edit)",
        "📥 Treklarni import (Excel)",
        "🏠 Asosiy menyu",
    ]
    ru_buttons = [
        "➕ Добавить трек-код",
        "🗑 Удалить трек-код",
        "📊 Статистика",
        "📄 Список треков",
        "📢 Рассылка",
        "🔗 Подключить канал",
        "👤 Добавить админа",
        "ℹ️ О нас (ред.)",
        "💰 Цены (ред.)",
        "📍 Адрес (ред.)",
        "📥 Импорт треков (Excel)",
        "🏠 Главное меню",
    ]
    labels = uz_buttons if lang == "uz" else ru_buttons
    main_button = labels[-1]
    base_labels = labels[:-1]
    keyboard = [
        [KeyboardButton(text=base_labels[i]), KeyboardButton(text=base_labels[i + 1])]
        for i in range(0, len(base_labels) - 1, 2)
    ]
    if len(base_labels) % 2 == 1:
        keyboard.append([KeyboardButton(text=base_labels[-1])])
    keyboard.append([KeyboardButton(text=main_button)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
