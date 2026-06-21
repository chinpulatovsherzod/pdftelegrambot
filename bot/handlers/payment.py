from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime
from sqlalchemy import select

from db.database import async_session, User

router = Router()


@router.message(F.text == "/status")
async def check_status(message: Message):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user:
        await message.answer("Вы ещё не зарегистрированы. Напишите /start")
        return

    lang = user.language or "ru"
    if user.is_subscribed and user.subscribed_until and user.subscribed_until > datetime.now():
        until = user.subscribed_until.strftime("%d.%m.%Y")
        text = (
            f"✅ Подписка активна до {until}\nДокументов создано: {user.docs_used}"
        ) if lang == "ru" else (
            f"✅ Obuna {until} gacha faol\nYaratilgan hujjatlar: {user.docs_used}"
        )
    else:
        remaining = max(0, 3 - user.docs_used)
        text = (
            f"📊 Бесплатных документов осталось: {remaining}/3\nВсего создано: {user.docs_used}"
        ) if lang == "ru" else (
            f"📊 Qolgan bepul hujjatlar: {remaining}/3\nJami yaratilgan: {user.docs_used}"
        )

    await message.answer(text)