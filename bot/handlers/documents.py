from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.states.states import KPState, ContractState, InvoiceState
from bot.keyboards.keyboards import main_menu, confirm_keyboard, subscribe_keyboard, back_keyboard
from db.database import async_session, get_or_create_user, can_generate, increment_docs_used
from db.database import User
from locales.texts import t
from pdf.generator import generate_kp, generate_contract, generate_invoice

router = Router()


async def get_user_lang(telegram_id: int) -> str:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user else "ru"


async def check_limit(callback: CallbackQuery, lang: str) -> bool:
    from bot.utils.channel_check import require_subscription
    if not await require_subscription(callback, lang):
        return False

    allowed = await can_generate(callback.from_user.id)
    if not allowed:
        from config import CLICK_MERCHANT_ID
        payment_url = (
            f"https://my.click.uz/services/pay?service_id={CLICK_MERCHANT_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}&amount=49900"
            f"&transaction_param={callback.from_user.id}"
        )
        await callback.message.edit_text(
            t(lang, "free_limit"),
            reply_markup=subscribe_keyboard(lang, payment_url),
            parse_mode="HTML"
        )
        return False
    return True


# ─── КП ───────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "doc_kp")
async def start_kp(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_limit(callback, lang):
        return
    await state.set_state(KPState.q1_company)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "kp_q1"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(KPState.q1_company)
async def kp_q1(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(company=message.text)
    await state.set_state(KPState.q2_client)
    await message.answer(t(data["lang"], "kp_q2"))


@router.message(KPState.q2_client)
async def kp_q2(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(client=message.text)
    await state.set_state(KPState.q3_product)
    await message.answer(t(data["lang"], "kp_q3"))


@router.message(KPState.q3_product)
async def kp_q3(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(product=message.text)
    await state.set_state(KPState.q4_price)
    await message.answer(t(data["lang"], "kp_q4"))


@router.message(KPState.q4_price)
async def kp_q4(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(price=message.text)
    await state.set_state(KPState.q5_deadline)
    await message.answer(t(data["lang"], "kp_q5"))


@router.message(KPState.q5_deadline)
async def kp_q5(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(deadline=message.text)
    await state.set_state(KPState.q6_phone)
    await message.answer(t(data["lang"], "kp_q6"))


@router.message(KPState.q6_phone)
async def kp_q6(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]
    await state.update_data(phone=message.text)
    await state.set_state(KPState.confirm)

    summary = (
        f"📋 <b>Коммерческое предложение</b>\n\n"
        f"🏢 Ваша компания: {data.get('company')}\n"
        f"🤝 Клиент: {data.get('client')}\n"
        f"📦 Продукт: {data.get('product')}\n"
        f"💰 Цена: {data.get('price')}\n"
        f"📅 Срок: {data.get('deadline')}\n"
        f"📞 Телефон: {message.text}\n\n"
        f"Всё верно?"
    ) if lang == "ru" else (
        f"📋 <b>Tijorat taklifi</b>\n\n"
        f"🏢 Kompaniya: {data.get('company')}\n"
        f"🤝 Mijoz: {data.get('client')}\n"
        f"📦 Mahsulot: {data.get('product')}\n"
        f"💰 Narx: {data.get('price')}\n"
        f"📅 Muddat: {data.get('deadline')}\n"
        f"📞 Telefon: {message.text}\n\n"
        f"Hammasi to'g'rimi?"
    )
    await message.answer(summary, reply_markup=confirm_keyboard(lang), parse_mode="HTML")


@router.callback_query(F.data == "confirm_doc")
async def confirm_doc(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_text(t(lang, "generating"))

    try:
        if "phone" in data:
            pdf_bytes = generate_kp(data, lang)
            filename = "commercial_offer.pdf"
        elif "city" in data:
            pdf_bytes = generate_contract(data, lang)
            filename = "contract.pdf"
        else:
            pdf_bytes = generate_invoice(data, lang)
            filename = "invoice.pdf"

        await increment_docs_used(callback.from_user.id)

        from aiogram.types import BufferedInputFile
        await callback.message.answer_document(
            BufferedInputFile(pdf_bytes, filename=filename),
            caption=t(lang, "doc_ready")
        )
        await callback.message.edit_text(
            t(lang, "welcome"),
            reply_markup=main_menu(lang)
        )
    except Exception as e:
        await callback.message.edit_text(
            t(lang, "error"),
            reply_markup=main_menu(lang)
        )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "regenerate_doc")
async def regenerate_doc(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.clear()
    await callback.message.edit_text(
        t(lang, "welcome"),
        reply_markup=main_menu(lang)
    )
    await callback.answer()


# ─── ДОГОВОР ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "doc_contract")
async def start_contract(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_limit(callback, lang):
        return
    await state.set_state(ContractState.q1_company)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "contract_q1"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ContractState.q1_company)
async def contract_q1(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(company=message.text)
    await state.set_state(ContractState.q2_client)
    await message.answer(t(data["lang"], "contract_q2"))


@router.message(ContractState.q2_client)
async def contract_q2(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(client=message.text)
    await state.set_state(ContractState.q3_subject)
    await message.answer(t(data["lang"], "contract_q3"))


@router.message(ContractState.q3_subject)
async def contract_q3(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(subject=message.text)
    await state.set_state(ContractState.q4_amount)
    await message.answer(t(data["lang"], "contract_q4"))


@router.message(ContractState.q4_amount)
async def contract_q4(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(amount=message.text)
    await state.set_state(ContractState.q5_deadline)
    await message.answer(t(data["lang"], "contract_q5"))


@router.message(ContractState.q5_deadline)
async def contract_q5(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(deadline=message.text)
    await state.set_state(ContractState.q6_city)
    await message.answer(t(data["lang"], "contract_q6"))


@router.message(ContractState.q6_city)
async def contract_q6(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]
    await state.update_data(city=message.text)
    await state.set_state(ContractState.confirm)

    summary = (
        f"📝 <b>Договор на услуги</b>\n\n"
        f"🏢 Исполнитель: {data.get('company')}\n"
        f"🤝 Заказчик: {data.get('client')}\n"
        f"📋 Предмет: {data.get('subject')}\n"
        f"💰 Сумма: {data.get('amount')}\n"
        f"📅 Срок: {data.get('deadline')}\n"
        f"📍 Город: {message.text}\n\n"
        f"Всё верно?"
    ) if lang == "ru" else (
        f"📝 <b>Xizmat shartnomasi</b>\n\n"
        f"🏢 Ijrochi: {data.get('company')}\n"
        f"🤝 Buyurtmachi: {data.get('client')}\n"
        f"📋 Predmet: {data.get('subject')}\n"
        f"💰 Summa: {data.get('amount')}\n"
        f"📅 Muddat: {data.get('deadline')}\n"
        f"📍 Shahar: {message.text}\n\n"
        f"Hammasi to'g'rimi?"
    )
    await message.answer(summary, reply_markup=confirm_keyboard(lang), parse_mode="HTML")


# ─── СЧЁТ ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "doc_invoice")
async def start_invoice(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_limit(callback, lang):
        return
    await state.set_state(InvoiceState.q1_company)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "invoice_q1"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(InvoiceState.q1_company)
async def invoice_q1(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(company=message.text)
    await state.set_state(InvoiceState.q2_client)
    await message.answer(t(data["lang"], "invoice_q2"))


@router.message(InvoiceState.q2_client)
async def invoice_q2(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(client=message.text)
    await state.set_state(InvoiceState.q3_product)
    await message.answer(t(data["lang"], "invoice_q3"))


@router.message(InvoiceState.q3_product)
async def invoice_q3(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(product=message.text)
    await state.set_state(InvoiceState.q4_quantity)
    await message.answer(t(data["lang"], "invoice_q4"))


@router.message(InvoiceState.q4_quantity)
async def invoice_q4(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(quantity=message.text)
    await state.set_state(InvoiceState.q5_price)
    await message.answer(t(data["lang"], "invoice_q5"))


@router.message(InvoiceState.q5_price)
async def invoice_q5(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(price=message.text)
    await state.set_state(InvoiceState.q6_bank)
    await message.answer(t(data["lang"], "invoice_q6"))


@router.message(InvoiceState.q6_bank)
async def invoice_q6(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]
    await state.update_data(bank=message.text)
    await state.set_state(InvoiceState.confirm)

    try:
        total = int(data.get("quantity", 1)) * int(data.get("price", 0))
        total_str = f"{total:,}".replace(",", " ")
        price_str = f"{int(data.get('price', 0)):,}".replace(",", " ")
    except:
        total_str = "—"
        price_str = data.get("price", "0")

    summary = (
        f"🧾 <b>Счёт на оплату</b>\n\n"
        f"🏢 Продавец: {data.get('company')}\n"
        f"🤝 Покупатель: {data.get('client')}\n"
        f"📦 Товар: {data.get('product')}\n"
        f"🔢 Кол-во: {data.get('quantity')}\n"
        f"💰 Цена: {price_str} сум\n"
        f"💵 Итого: {total_str} сум\n\n"
        f"Всё верно?"
    ) if lang == "ru" else (
        f"🧾 <b>Hisob-faktura</b>\n\n"
        f"🏢 Sotuvchi: {data.get('company')}\n"
        f"🤝 Xaridor: {data.get('client')}\n"
        f"📦 Tovar: {data.get('product')}\n"
        f"🔢 Miqdori: {data.get('quantity')}\n"
        f"💰 Narx: {price_str} so'm\n"
        f"💵 Jami: {total_str} so'm\n\n"
        f"Hammasi to'g'rimi?"
    )
    await message.answer(summary, reply_markup=confirm_keyboard(lang), parse_mode="HTML")