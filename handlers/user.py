"""User-facing handlers."""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import LANGUAGES
from database import db
from keyboards import language_keyboard, main_menu, tracking_menu
from subscription import get_required_channel, is_subscribed, send_subscription_required


router = Router()


# --- State machines ---
class TrackCheckState(StatesGroup):
    waiting_for_code = State()


class ComplaintState(StatesGroup):
    waiting_for_text = State()


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user or db.is_admin(user.id):
            return await handler(event, data)

        channel_link, channel_chat_id = get_required_channel()
        if not channel_link:
            return await handler(event, data)

        if isinstance(event, types.Message):
            text = (event.text or "").strip()
            if text.startswith("/start") or is_language_text(text):
                return await handler(event, data)

            if not await is_subscribed(event.bot, user.id, channel_chat_id):
                lang = db.get_user_language(user.id)
                await send_subscription_required(event, lang)
                return None

        if isinstance(event, types.CallbackQuery):
            if event.data == "check_subscription":
                return await handler(event, data)

            if not await is_subscribed(event.bot, user.id, channel_chat_id):
                lang = db.get_user_language(user.id)
                if event.message:
                    await send_subscription_required(event.message, lang)
                await event.answer()
                return None

        return await handler(event, data)


router.message.middleware(SubscriptionMiddleware())
router.callback_query.middleware(SubscriptionMiddleware())


# --- Text helpers ---
def get_text(key: str, lang: str) -> str:
    texts = {
        "welcome": {
            "uz": "Hush kelibsiz, tilni tanlang",
            "ru": "Добро пожаловать, выберите язык",
        },
        "menu_prompt": {
            "uz": "Asosiy menyu:",
            "ru": "Главное меню:",
        },
        "ask_track": {
            "uz": "Trek kodni kiriting. Yana tekshirish uchun navbatdagi kodni yuboring yoki \"Orqaga\" tugmasini bosing.",
            "ru": "Введите трек-код. Для следующей проверки отправьте новый код или нажмите кнопку «Назад».",
        },
        "track_not_found": {
            "uz": "Trek kodda xatolik bor yoki yuk manzilga hali kelmagan.",
            "ru": "Трек-код введен с ошибкой или груз еще не прибыл на склад/пункт выдачи.",
        },
        "track_next_hint": {
            "uz": "Keyingi trek kodni yuboring yoki \"Orqaga\" tugmasini bosing.",
            "ru": "Отправьте следующий трек-код или нажмите кнопку «Назад».",
        },
        "ask_complaint": {
            "uz": "Shikoyatingizni yozib yuboring.",
            "ru": "Отправьте, пожалуйста, ваше обращение/жалобу.",
        },
        "complaint_received": {
            "uz": "Shikoyatingiz qabul qilindi. Tez orada javob beramiz.",
            "ru": "Ваше обращение получено. Мы скоро ответим.",
        },
        "prices_title": {
            "uz": "Narxlar:",
            "ru": "Цены:",
        },
        "address_title": {
            "uz": "Manzil ma'lumoti:",
            "ru": "Информация об адресе:",
        },
        "id_info": {
            "uz": "Hurmatli foydalanuvchi, ID olish yoki qo'shimcha ma'lumotlar uchun adminimiz bilan bog'laning: {admin}",
            "ru": "Для получения ID и дополнительной информации свяжитесь с администратором: {admin}",
        },
        "yuan_info": {
            "uz": "Yuan (Xitoy pul birligi) bo'yicha kurs va to'lov ma'lumotlari uchun admin bilan bog'laning: {admin}",
            "ru": "По вопросам юаня (китайская валюта), курса и оплаты свяжитесь с администратором: {admin}",
        },
    }
    return texts[key][lang]


def parse_language(text: str) -> str:
    if "O'zbek" in text or "🇺🇿" in text or "рџ‡єрџ‡ї" in text:
        return "uz"
    if "Рус" in text or "🇷🇺" in text or "Р СѓСЃ" in text or "рџ‡·рџ‡є" in text:
        return "ru"
    return "uz"


def is_language_text(text: str) -> bool:
    return bool(text and ("O'zbek" in text or "Рус" in text or "Р СѓСЃ" in text))


def ensure_user_language(user_id: int, language: str):
    if language not in LANGUAGES:
        language = "uz"
    db.set_user_language(user_id, language)


def is_back_text(text: str) -> bool:
    raw = (text or "").strip()
    lowered = raw.lower()
    return (
        "orqaga" in lowered
        or "назад" in lowered
        or "РќР°Р·Р°Рґ".lower() in lowered
    )


# --- Handlers ---
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    # Optional sticker on start
    sticker_id = getattr(message.bot, "start_sticker", "") or ""
    if sticker_id:
        try:
            await message.answer_sticker(sticker_id)
        except Exception:
            pass
    await message.answer(get_text("welcome", "uz"), reply_markup=language_keyboard())


@router.message(lambda m: m.text and ("O'zbek" in m.text or "Рус" in m.text or "Р СѓСЃ" in m.text))
async def choose_language(message: types.Message, state: FSMContext):
    language = parse_language(message.text)
    ensure_user_language(message.from_user.id, language)
    await state.clear()
    _, channel_chat_id = get_required_channel()
    if not await is_subscribed(message.bot, message.from_user.id, channel_chat_id):
        await send_subscription_required(message, language)
        return
    await message.answer(
        get_text("menu_prompt", language),
        reply_markup=main_menu(language),
    )


@router.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(callback: types.CallbackQuery):
    lang = db.get_user_language(callback.from_user.id)
    _, channel_chat_id = get_required_channel()
    if await is_subscribed(callback.bot, callback.from_user.id, channel_chat_id):
        await callback.answer(
            "Obuna tasdiqlandi." if lang == "uz" else "Подписка подтверждена.",
            show_alert=True,
        )
        if callback.message:
            await callback.message.answer(get_text("menu_prompt", lang), reply_markup=main_menu(lang))
        return

    await callback.answer(
        "Avval kanalga obuna bo'ling." if lang == "uz" else "Сначала подпишитесь на канал.",
        show_alert=True,
    )


@router.message(lambda m: m.text and ("ID olish" in m.text or "Получить ID" in m.text or "РџРѕР»СѓС‡РёС‚СЊ ID" in m.text))
async def handle_get_id(message: types.Message):
    lang = db.get_user_language(message.from_user.id)
    admin_username = db.get_setting("admin_username")
    await message.answer(get_text("id_info", lang).format(admin=admin_username))


@router.message(lambda m: m.text and ("Biz haqimizda" in m.text or "О нас" in m.text or "Рћ РЅР°СЃ" in m.text))
async def handle_about(message: types.Message):
    lang = db.get_user_language(message.from_user.id)
    key = "about_uz" if lang == "uz" else "about_ru"
    about_text = db.get_setting(key) or ""
    await message.answer(about_text)


@router.message(lambda m: m.text and ("Narxlar" in m.text or "Цены" in m.text or "Р¦РµРЅС‹" in m.text))
async def handle_prices(message: types.Message):
    lang = db.get_user_language(message.from_user.id)
    key = "prices_uz" if lang == "uz" else "prices_ru"
    fallback_key = "price_uz" if lang == "uz" else "price_ru"
    prices = db.get_setting(key) or db.get_setting(fallback_key) or get_text("prices_title", lang)
    await message.answer(prices)


@router.message(lambda m: m.text and ("Manzil" in m.text or "Адрес" in m.text or "РђРґСЂРµСЃ" in m.text))
async def handle_address(message: types.Message):
    lang = db.get_user_language(message.from_user.id)
    text_key = "address_uz" if lang == "uz" else "address_ru"
    address = db.get_setting(text_key) or ""
    map_link = db.get_setting("map_link") or ""
    full_text = f"{get_text('address_title', lang)}\n{address}"
    if map_link:
        full_text += f"\n{map_link}"
    await message.answer(full_text)


@router.message(lambda m: m.text and ("Yuan" in m.text or "Юань" in m.text or "Юан" in m.text or "Р®Р°РЅСЊ" in m.text or "Р®Р°РЅ" in m.text))
async def handle_yuan(message: types.Message):
    lang = db.get_user_language(message.from_user.id)
    admin_username = db.get_setting("admin_username")
    await message.answer(get_text("yuan_info", lang).format(admin=admin_username))


@router.message(
    lambda m: m.text and ("Trek kod tekshirish" in m.text or "Проверить трек-код" in m.text or "РџСЂРѕРІРµСЂРёС‚СЊ С‚СЂРµРє-РєРѕРґ" in m.text)
)
async def handle_track_request(message: types.Message, state: FSMContext):
    lang = db.get_user_language(message.from_user.id)
    await state.set_state(TrackCheckState.waiting_for_code)
    await message.answer(
        get_text("ask_track", lang),
        reply_markup=tracking_menu(lang),
    )


@router.message(
    TrackCheckState.waiting_for_code,
    lambda m: m.text and is_back_text(m.text),
)
async def handle_track_back(message: types.Message, state: FSMContext):
    lang = db.get_user_language(message.from_user.id)
    await state.clear()
    await message.answer(
        get_text("menu_prompt", lang),
        reply_markup=main_menu(lang),
    )


@router.message(TrackCheckState.waiting_for_code)
async def handle_track_code(message: types.Message, state: FSMContext):
    lang = db.get_user_language(message.from_user.id)
    text = (message.text or "").strip()
    if is_back_text(text):
        await state.clear()
        await message.answer(
            get_text("menu_prompt", lang),
            reply_markup=main_menu(lang),
        )
        return

    track_code = text
    track = db.get_track_by_code(track_code)

    if not track:
        await message.answer(
            f"{get_text('track_not_found', lang)}\n\n{get_text('track_next_hint', lang)}",
            reply_markup=tracking_menu(lang),
        )
        return

    status = track["status"] or ("Yo'lda" if lang == "uz" else "В пути")
    response = (
        f"Trek: {track['track_code']}\n"
        f"Reys: {track['flight_number']}\n"
        f"Holat/Статус: {status}\n"
        f"Kiritilgan: {track['created_at']}\n\n"
        f"{get_text('track_next_hint', lang)}"
    )
    await message.answer(response, reply_markup=tracking_menu(lang))


@router.message(
    lambda m: m.text and ("Shikoyat yuborish" in m.text or "Отправить жалобу" in m.text or "РћС‚РїСЂР°РІРёС‚СЊ Р¶Р°Р»РѕР±Сѓ" in m.text)
)
async def handle_complaint_start(message: types.Message, state: FSMContext):
    lang = db.get_user_language(message.from_user.id)
    await state.set_state(ComplaintState.waiting_for_text)
    await message.answer(get_text("ask_complaint", lang))


@router.message(ComplaintState.waiting_for_text)
async def handle_complaint_text(message: types.Message, state: FSMContext):
    lang = db.get_user_language(message.from_user.id)
    await state.clear()
    admin_chat_ids = getattr(message.bot, "admin_chat_ids", []) or []
    if not admin_chat_ids:
        await message.answer("Admin chat ID sozlanmagan.")
        return
    text = (
        f"Yangi shikoyat / Новое обращение:\n"
        f"User ID: {message.from_user.id}\n"
        f"Username: @{message.from_user.username or '-'}\n"
        f"Ism: {message.from_user.full_name}\n\n"
        f"Matn:\n{message.text}"
    )
    complaint_map = getattr(message.bot, "complaint_map", {})
    delivered = False
    for admin_chat_id in admin_chat_ids:
        try:
            sent = await message.bot.send_message(chat_id=admin_chat_id, text=text)
            complaint_map[(admin_chat_id, sent.message_id)] = message.from_user.id
            delivered = True
            try:
                reminder = await message.bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"Reply to this message to answer user {message.from_user.id}",
                    reply_to_message_id=sent.message_id,
                )
                complaint_map[(admin_chat_id, reminder.message_id)] = message.from_user.id
            except Exception as exc:  # noqa: BLE001
                logging.error("Failed to send reminder to admin chat %s: %s", admin_chat_id, exc)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to send complaint to admin chat %s: %s", admin_chat_id, exc)
            continue
    if delivered:
        message.bot.complaint_map = complaint_map
        await message.answer(get_text("complaint_received", lang))
    else:
        await message.answer("Shikoyatni yuborib bo'lmadi. Iltimos, keyinroq urinib ko'ring.")
