from aiogram import Bot
from aiogram.types import CallbackQuery
from config import CHANNEL_ID


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False


async def require_subscription(callback: CallbackQuery, lang: str) -> bool:
    from config import ADMIN_IDS
    if callback.from_user.id in ADMIN_IDS:
        return True

    subscribed = await is_subscribed(callback.bot, callback.from_user.id)
    if not subscribed:
        from bot.keyboards.keyboards import subscribe_channel_keyboard

        await callback.answer(
            "❌ Подпишитесь на канал чтобы пользоваться ботом!" if lang == "ru"
            else "❌ Botdan foydalanish uchun kanalga obuna bo'ling!",
            show_alert=True
        )
        await callback.message.edit_text(
            "👋 Для продолжения подпишитесь на канал:" if lang == "ru"
            else "👋 Davom etish uchun kanalga obuna bo'ling:",
            reply_markup=subscribe_channel_keyboard(lang, CHANNEL_ID)
        )
        return False
    return True