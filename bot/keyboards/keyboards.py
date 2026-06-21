from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from locales.texts import t


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
        ]
    ])


def main_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_kp"), callback_data="doc_kp")],
        [InlineKeyboardButton(text=t(lang, "btn_contract"), callback_data="doc_contract")],
        [InlineKeyboardButton(text=t(lang, "btn_invoice"), callback_data="doc_invoice")],
        [InlineKeyboardButton(text=t(lang, "btn_pdf2word"), callback_data="pdf2word")],
        [InlineKeyboardButton(text=t(lang, "btn_word2pdf"), callback_data="word2pdf")],
        [InlineKeyboardButton(text=t(lang, "btn_jpg2word"), callback_data="jpg2word")],
        [InlineKeyboardButton(text=t(lang, "btn_jpg2pdf"), callback_data="jpg2pdf")],
        [InlineKeyboardButton(text=t(lang, "btn_ppt2pdf"), callback_data="ppt2pdf")],
        [InlineKeyboardButton(text=t(lang, "btn_excel2pdf"), callback_data="excel2pdf")],
        [InlineKeyboardButton(text=t(lang, "btn_file2zip"), callback_data="file2zip")],
        [InlineKeyboardButton(text=t(lang, "btn_help"), callback_data="help")],
    ])


def confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "btn_confirm"), callback_data="confirm_doc"),
            InlineKeyboardButton(text=t(lang, "btn_regenerate"), callback_data="regenerate_doc"),
        ],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_to_menu")],
    ])


def subscribe_keyboard(lang: str, payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_subscribe"), url=payment_url)],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_to_menu")],
    ])


def back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="back_to_menu")]
    ])


def subscribe_channel_keyboard(lang: str, channel: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_subscribe_channel"), url=f"https://t.me/{channel.lstrip('@')}")],
        [InlineKeyboardButton(text=t(lang, "btn_check_subscription"), callback_data="check_subscription")],
    ])

def multi_image_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_done"), callback_data="images_done")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="back_to_menu")],
    ])