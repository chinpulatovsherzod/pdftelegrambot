from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy import select, update

from db.database import get_or_create_user, async_session, User
from bot.keyboards.keyboards import language_keyboard, main_menu, back_keyboard, subscribe_channel_keyboard
from bot.utils.channel_check import is_subscribed
from locales.texts import t
from config import CHANNEL_ID

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    subscribed = await is_subscribed(message.bot, message.from_user.id)
    if not subscribed:
        await message.answer(
            "👋 Привет! Для использования бота необходимо подписаться на наш канал.\n\n"
            "После подписки нажмите кнопку ✅ Я подписался",
            reply_markup=subscribe_channel_keyboard("ru", CHANNEL_ID)
        )
        return

    await message.answer(
        "🌐 Выберите язык / Tilni tanlang:",
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    subscribed = await is_subscribed(callback.bot, callback.from_user.id)

    if not subscribed:
        await callback.answer(
            "❌ Вы ещё не подписались! / Hali obuna bo'lmadingiz!",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "🌐 Выберите язык / Tilni tanlang:",
        reply_markup=language_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == callback.from_user.id)
            .values(language=lang)
        )
        await session.commit()
    await callback.message.edit_text(
        t(lang, "welcome"),
        reply_markup=main_menu(lang)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ru"
    await callback.message.edit_text(
        t(lang, "welcome"),
        reply_markup=main_menu(lang)
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ru"
    await callback.message.edit_text(
        t(lang, "help_text"),
        reply_markup=back_keyboard(lang),
        parse_mode="HTML"
    )
    await callback.answer()