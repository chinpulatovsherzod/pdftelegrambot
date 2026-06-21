import os
import asyncio
import tempfile
import zipfile
import subprocess
import shutil

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from db.database import async_session, User, can_generate, increment_docs_used
from bot.keyboards.keyboards import back_keyboard, main_menu, subscribe_keyboard, multi_image_keyboard
from bot.utils.channel_check import require_subscription
from locales.texts import t

router = Router()

MAX_IMAGES = 10

# Простая блокировка на пользователя, чтобы избежать гонки состояний
user_locks = {}


def get_lock(user_id: int) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]


class ConverterState(StatesGroup):
    waiting_pdf = State()
    waiting_jpg = State()
    waiting_ppt = State()
    waiting_excel = State()
    waiting_any_file = State()
    waiting_word = State()
    waiting_jpg2pdf = State()


async def get_user_lang(telegram_id: int) -> str:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user else "ru"


async def check_access(callback: CallbackQuery, lang: str) -> bool:
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


def convert_with_libreoffice(input_path: str, output_dir: str, target_format: str) -> str:
    soffice_paths = [
        "soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    soffice_exe = None
    for path in soffice_paths:
        if shutil.which(path) or os.path.exists(path):
            soffice_exe = path
            break

    if not soffice_exe:
        raise FileNotFoundError("LibreOffice не найден.")

    subprocess.run([
        soffice_exe,
        "--headless",
        "--convert-to", target_format,
        "--outdir", output_dir,
        input_path
    ], check=True, timeout=60)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    result_path = os.path.join(output_dir, f"{base_name}.{target_format}")
    return result_path


# ─── PDF → WORD ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "pdf2word")
async def start_pdf2word(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_access(callback, lang):
        return
    await state.set_state(ConverterState.waiting_pdf)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "pdf2word_ask"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ConverterState.waiting_pdf, F.document)
async def convert_pdf(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if not message.document.file_name.lower().endswith(".pdf"):
        await message.answer(t(lang, "wrong_format"))
        return

    status_msg = await message.answer(t(lang, "pdf2word_converting"))

    try:
        from pdf2docx import Converter

        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            docx_path = os.path.join(tmpdir, "output.docx")

            with open(pdf_path, "wb") as f:
                f.write(file_bytes.read())

            cv = Converter(pdf_path)
            cv.convert(docx_path)
            cv.close()

            with open(docx_path, "rb") as f:
                docx_bytes = f.read()

        await increment_docs_used(message.from_user.id)
        original_name = message.document.file_name.rsplit(".", 1)[0] + ".docx"
        await status_msg.delete()
        await message.answer_document(
            BufferedInputFile(docx_bytes, filename=original_name),
            caption=t(lang, "pdf2word_ready")
        )
    except Exception:
        await status_msg.delete()
        await message.answer(t(lang, "error"))

    await state.clear()


# ─── JPG → WORD (несколько картинок, OCR) ────────────────────────────────────

@router.callback_query(F.data == "jpg2word")
async def start_jpg2word(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_access(callback, lang):
        return
    await state.set_state(ConverterState.waiting_jpg)
    await state.update_data(lang=lang, images=[], last_status_id=None)
    await callback.message.edit_text(t(lang, "multi_image_ask"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ConverterState.waiting_jpg, F.photo | F.document)
async def collect_jpg_for_word(message: Message, state: FSMContext):
    lock = get_lock(message.from_user.id)
    async with lock:
        data = await state.get_data()
        lang = data.get("lang", "ru")
        images = data.get("images", [])
        last_status_id = data.get("last_status_id")

        if len(images) >= MAX_IMAGES:
            return

        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        images.append(file_id)

        if last_status_id:
            try:
                await message.bot.delete_message(message.chat.id, last_status_id)
            except Exception:
                pass

        status_msg = await message.answer(
            t(lang, "multi_image_added").format(count=len(images)),
            reply_markup=multi_image_keyboard(lang)
        )

        await state.update_data(images=images, last_status_id=status_msg.message_id)


@router.callback_query(ConverterState.waiting_jpg, F.data == "images_done")
async def finish_jpg2word(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    images = data.get("images", [])

    if not images:
        await callback.answer(t(lang, "no_images"), show_alert=True)
        return

    await callback.answer()
    status_msg = await callback.message.answer(t(lang, "jpg2word_converting"))

    try:
        import pytesseract
        from PIL import Image
        from docx import Document

        doc = Document()

        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, file_id in enumerate(images):
                file = await callback.bot.get_file(file_id)
                file_bytes = await callback.bot.download_file(file.file_path)

                img_path = os.path.join(tmpdir, f"img_{idx}.jpg")
                with open(img_path, "wb") as f:
                    f.write(file_bytes.read())

                image = Image.open(img_path)
                text = pytesseract.image_to_string(image, lang="rus+uzb+eng")

                if idx > 0:
                    doc.add_page_break()
                doc.add_paragraph(text)

            docx_path = os.path.join(tmpdir, "output.docx")
            doc.save(docx_path)

            with open(docx_path, "rb") as f:
                docx_bytes = f.read()

        await increment_docs_used(callback.from_user.id)
        await status_msg.delete()
        await callback.message.answer_document(
            BufferedInputFile(docx_bytes, filename="recognized_text.docx"),
            caption=t(lang, "jpg2word_ready")
        )
        await callback.message.answer(t(lang, "welcome"), reply_markup=main_menu(lang))
    except ImportError:
        await status_msg.delete()
        await callback.message.answer(
            "❌ Распознавание текста временно недоступно." if lang == "ru"
            else "❌ Matn tanish vaqtincha mavjud emas."
        )
    except Exception:
        await status_msg.delete()
        await callback.message.answer(t(lang, "error"))

    await state.clear()


# ─── POWERPOINT → PDF ───────────────────────────────────────────────────────

@router.callback_query(F.data == "ppt2pdf")
async def start_ppt2pdf(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_access(callback, lang):
        return
    await state.set_state(ConverterState.waiting_ppt)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "ppt2pdf_ask"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ConverterState.waiting_ppt, F.document)
async def convert_ppt(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if not message.document.file_name.lower().endswith((".ppt", ".pptx")):
        await message.answer(t(lang, "wrong_format"))
        return

    status_msg = await message.answer(t(lang, "ppt2pdf_converting"))

    try:
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, message.document.file_name)
            with open(input_path, "wb") as f:
                f.write(file_bytes.read())

            output_path = convert_with_libreoffice(input_path, tmpdir, "pdf")

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

        await increment_docs_used(message.from_user.id)
        original_name = message.document.file_name.rsplit(".", 1)[0] + ".pdf"
        await status_msg.delete()
        await message.answer_document(
            BufferedInputFile(pdf_bytes, filename=original_name),
            caption=t(lang, "ppt2pdf_ready")
        )
    except FileNotFoundError:
        await status_msg.delete()
        await message.answer(
            "❌ LibreOffice не установлен на сервере." if lang == "ru"
            else "❌ Serverda LibreOffice o'rnatilmagan."
        )
    except Exception:
        await status_msg.delete()
        await message.answer(t(lang, "error"))

    await state.clear()


# ─── EXCEL → PDF ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "excel2pdf")
async def start_excel2pdf(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_access(callback, lang):
        return
    await state.set_state(ConverterState.waiting_excel)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "excel2pdf_ask"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ConverterState.waiting_excel, F.document)
async def convert_excel(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if not message.document.file_name.lower().endswith((".xls", ".xlsx")):
        await message.answer(t(lang, "wrong_format"))
        return

    status_msg = await message.answer(t(lang, "excel2pdf_converting"))

    try:
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, message.document.file_name)
            with open(input_path, "wb") as f:
                f.write(file_bytes.read())

            output_path = convert_with_libreoffice(input_path, tmpdir, "pdf")

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

        await increment_docs_used(message.from_user.id)
        original_name = message.document.file_name.rsplit(".", 1)[0] + ".pdf"
        await status_msg.delete()
        await message.answer_document(
            BufferedInputFile(pdf_bytes, filename=original_name),
            caption=t(lang, "excel2pdf_ready")
        )
    except FileNotFoundError:
        await status_msg.delete()
        await message.answer(
            "❌ LibreOffice не установлен на сервере." if lang == "ru"
            else "❌ Serverda LibreOffice o'rnatilmagan."
        )
    except Exception:
        await status_msg.delete()
        await message.answer(t(lang, "error"))

    await state.clear()


# ─── FILE → ZIP ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "file2zip")
async def start_file2zip(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_access(callback, lang):
        return
    await state.set_state(ConverterState.waiting_any_file)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "file2zip_ask"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ConverterState.waiting_any_file, F.document)
async def convert_to_zip(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    status_msg = await message.answer(t(lang, "file2zip_converting"))

    try:
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        filename = message.document.file_name

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, filename)
            with open(input_path, "wb") as f:
                f.write(file_bytes.read())

            zip_path = os.path.join(tmpdir, "archive.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(input_path, arcname=filename)

            with open(zip_path, "rb") as f:
                zip_bytes = f.read()

        await increment_docs_used(message.from_user.id)
        zip_name = filename.rsplit(".", 1)[0] + ".zip"
        await status_msg.delete()
        await message.answer_document(
            BufferedInputFile(zip_bytes, filename=zip_name),
            caption=t(lang, "file2zip_ready")
        )
    except Exception:
        await status_msg.delete()
        await message.answer(t(lang, "error"))

    await state.clear()


# ─── WORD → PDF ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "word2pdf")
async def start_word2pdf(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_access(callback, lang):
        return
    await state.set_state(ConverterState.waiting_word)
    await state.update_data(lang=lang)
    await callback.message.edit_text(t(lang, "word2pdf_ask"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ConverterState.waiting_word, F.document)
async def convert_word(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if not message.document.file_name.lower().endswith((".doc", ".docx")):
        await message.answer(t(lang, "wrong_format"))
        return

    status_msg = await message.answer(t(lang, "word2pdf_converting"))

    try:
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, message.document.file_name)
            with open(input_path, "wb") as f:
                f.write(file_bytes.read())

            output_path = convert_with_libreoffice(input_path, tmpdir, "pdf")

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

        await increment_docs_used(message.from_user.id)
        original_name = message.document.file_name.rsplit(".", 1)[0] + ".pdf"
        await status_msg.delete()
        await message.answer_document(
            BufferedInputFile(pdf_bytes, filename=original_name),
            caption=t(lang, "word2pdf_ready")
        )
    except FileNotFoundError:
        await status_msg.delete()
        await message.answer(
            "❌ LibreOffice не установлен на сервере." if lang == "ru"
            else "❌ Serverda LibreOffice o'rnatilmagan."
        )
    except Exception:
        await status_msg.delete()
        await message.answer(t(lang, "error"))

    await state.clear()


# ─── JPG → PDF (несколько картинок) ──────────────────────────────────────────

@router.callback_query(F.data == "jpg2pdf")
async def start_jpg2pdf(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    if not await check_access(callback, lang):
        return
    await state.set_state(ConverterState.waiting_jpg2pdf)
    await state.update_data(lang=lang, images=[], last_status_id=None)
    await callback.message.edit_text(t(lang, "multi_image_ask"), reply_markup=back_keyboard(lang))
    await callback.answer()


@router.message(ConverterState.waiting_jpg2pdf, F.photo | F.document)
async def collect_jpg_for_pdf(message: Message, state: FSMContext):
    lock = get_lock(message.from_user.id)
    async with lock:
        data = await state.get_data()
        lang = data.get("lang", "ru")
        images = data.get("images", [])
        last_status_id = data.get("last_status_id")

        if len(images) >= MAX_IMAGES:
            return

        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
            file_id = message.document.file_id
        else:
            await message.answer(t(lang, "wrong_format"))
            return

        images.append(file_id)

        if last_status_id:
            try:
                await message.bot.delete_message(message.chat.id, last_status_id)
            except Exception:
                pass

        status_msg = await message.answer(
            t(lang, "multi_image_added").format(count=len(images)),
            reply_markup=multi_image_keyboard(lang)
        )

        await state.update_data(images=images, last_status_id=status_msg.message_id)


@router.callback_query(ConverterState.waiting_jpg2pdf, F.data == "images_done")
async def finish_jpg2pdf(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    images = data.get("images", [])

    if not images:
        await callback.answer(t(lang, "no_images"), show_alert=True)
        return

    await callback.answer()
    status_msg = await callback.message.answer(t(lang, "jpg2pdf_converting"))

    try:
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            pil_images = []
            for idx, file_id in enumerate(images):
                file = await callback.bot.get_file(file_id)
                file_bytes = await callback.bot.download_file(file.file_path)

                img_path = os.path.join(tmpdir, f"img_{idx}.jpg")
                with open(img_path, "wb") as f:
                    f.write(file_bytes.read())

                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                pil_images.append(img)

            pdf_path = os.path.join(tmpdir, "output.pdf")
            pil_images[0].save(
                pdf_path, "PDF",
                save_all=True,
                append_images=pil_images[1:]
            )

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

        await increment_docs_used(callback.from_user.id)
        await status_msg.delete()
        await callback.message.answer_document(
            BufferedInputFile(pdf_bytes, filename="images.pdf"),
            caption=t(lang, "jpg2pdf_ready")
        )
        await callback.message.answer(t(lang, "welcome"), reply_markup=main_menu(lang))
    except Exception:
        await status_msg.delete()
        await callback.message.answer(t(lang, "error"))

    await state.clear()