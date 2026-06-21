from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import date
import os

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
FONT_BOLD_PATH = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans-Bold.ttf")

try:
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD_PATH))
    FONT = "DejaVu"
    FONT_BOLD = "DejaVu-Bold"
except:
    FONT = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"

PRIMARY_COLOR = colors.HexColor("#1A56DB")
SECONDARY_COLOR = colors.HexColor("#F3F4F6")
TEXT_COLOR = colors.HexColor("#111827")
MUTED_COLOR = colors.HexColor("#6B7280")
TODAY = date.today().strftime("%d.%m.%Y")


def _base_styles():
    return {
        "title": ParagraphStyle(
            "title", fontName=FONT_BOLD, fontSize=18,
            textColor=PRIMARY_COLOR, spaceAfter=6, leading=22
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=FONT, fontSize=11,
            textColor=MUTED_COLOR, spaceAfter=12
        ),
        "label": ParagraphStyle(
            "label", fontName=FONT_BOLD, fontSize=10,
            textColor=MUTED_COLOR, spaceBefore=8, spaceAfter=2
        ),
        "value": ParagraphStyle(
            "value", fontName=FONT, fontSize=11,
            textColor=TEXT_COLOR, spaceAfter=4, leading=15
        ),
        "body": ParagraphStyle(
            "body", fontName=FONT, fontSize=10,
            textColor=TEXT_COLOR, leading=14, spaceAfter=6
        ),
        "footer": ParagraphStyle(
            "footer", fontName=FONT, fontSize=9,
            textColor=MUTED_COLOR, alignment=1
        ),
    }


def _build_pdf(elements) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    doc.build(elements)
    return buf.getvalue()


def generate_kp(data: dict, lang: str) -> bytes:
    styles = _base_styles()
    elements = []

    title = "КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ" if lang == "ru" else "TIJORAT TAKLIFI"
    elements.append(Paragraph(title, styles["title"]))
    elements.append(Paragraph(f"№ КП-{TODAY.replace('.', '')} от {TODAY}", styles["subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR, spaceAfter=16))

    if lang == "ru":
        fields = [
            ("От кого:", data.get("company", "")),
            ("Кому:", data.get("client", "")),
            ("Предмет предложения:", data.get("product", "")),
            ("Стоимость:", f"{data.get('price', '')} сум"),
            ("Срок:", data.get("deadline", "")),
            ("Контакт:", data.get("phone", "")),
        ]
        body_text = (
            f"Компания <b>{data.get('company', '')}</b> рада предложить Вам {data.get('product', '')}. "
            f"Стоимость составляет {data.get('price', '')} сум. "
            f"Срок выполнения: {data.get('deadline', '')}. "
            f"По всем вопросам обращайтесь: {data.get('phone', '')}."
        )
        footer_text = "Данное предложение действительно в течение 30 дней с момента получения."
    else:
        fields = [
            ("Kimdan:", data.get("company", "")),
            ("Kimga:", data.get("client", "")),
            ("Taklif predmeti:", data.get("product", "")),
            ("Narx:", f"{data.get('price', '')} so'm"),
            ("Muddat:", data.get("deadline", "")),
            ("Aloqa:", data.get("phone", "")),
        ]
        body_text = (
            f"<b>{data.get('company', '')}</b> kompaniyasi Sizga {data.get('product', '')} taklif etishdan mamnun. "
            f"Narxi {data.get('price', '')} so'm. "
            f"Bajarish muddati: {data.get('deadline', '')}. "
            f"Aloqa uchun: {data.get('phone', '')}."
        )
        footer_text = "Ushbu taklif qabul qilingan kundan boshlab 30 kun davomida amal qiladi."

    for label, value in fields:
        elements.append(Paragraph(label, styles["label"]))
        elements.append(Paragraph(value, styles["value"]))

    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MUTED_COLOR, spaceAfter=12))
    elements.append(Paragraph(body_text, styles["body"]))
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(footer_text, styles["footer"]))

    return _build_pdf(elements)


def generate_contract(data: dict, lang: str) -> bytes:
    styles = _base_styles()
    elements = []

    title = "ДОГОВОР ОКАЗАНИЯ УСЛУГ" if lang == "ru" else "XIZMAT KO'RSATISH SHARTNOMASI"
    number = f"№ Д-{TODAY.replace('.', '')}"
    city = data.get("city", "Toshkent")

    elements.append(Paragraph(title, styles["title"]))
    elements.append(Paragraph(f"{number} | {city}, {TODAY}", styles["subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR, spaceAfter=16))

    if lang == "ru":
        elements.append(Paragraph(
            f"<b>Исполнитель:</b> {data.get('company', '')}, именуемый далее «Исполнитель»",
            styles["body"]
        ))
        elements.append(Paragraph(
            f"<b>Заказчик:</b> {data.get('client', '')}, именуемый далее «Заказчик»",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3*cm))
        clauses = [
            ("1. ПРЕДМЕТ ДОГОВОРА",
             f"Исполнитель обязуется оказать следующие услуги: {data.get('subject', '')}. "
             f"Заказчик обязуется принять и оплатить данные услуги."),
            ("2. СТОИМОСТЬ И ПОРЯДОК ОПЛАТЫ",
             f"Стоимость услуг составляет {data.get('amount', '')} сум. "
             f"Оплата производится в течение 5 банковских дней после подписания акта."),
            ("3. СРОКИ ИСПОЛНЕНИЯ",
             f"Исполнитель обязуется выполнить работы в срок: {data.get('deadline', '')}."),
            ("4. ОТВЕТСТВЕННОСТЬ СТОРОН",
             "Стороны несут ответственность за неисполнение условий настоящего договора "
             "в соответствии с действующим законодательством Республики Узбекистан."),
        ]
    else:
        elements.append(Paragraph(
            f"<b>Ijrochi:</b> {data.get('company', '')}, bundan buyon «Ijrochi» deb ataladi",
            styles["body"]
        ))
        elements.append(Paragraph(
            f"<b>Buyurtmachi:</b> {data.get('client', '')}, bundan buyon «Buyurtmachi» deb ataladi",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.3*cm))
        clauses = [
            ("1. SHARTNOMA PREDMETI",
             f"Ijrochi quyidagi xizmatlarni ko'rsatishga majburiyat oladi: {data.get('subject', '')}. "
             f"Buyurtmachi ushbu xizmatlarni qabul qilish va to'lashga majburiyat oladi."),
            ("2. NARX VA TO'LOV TARTIBI",
             f"Xizmatlar narxi {data.get('amount', '')} so'mni tashkil etadi. "
             f"To'lov dalolatnoma imzolanganidan keyin 5 ish kuni ichida amalga oshiriladi."),
            ("3. BAJARISH MUDDATLARI",
             f"Ijrochi ishlarni quyidagi muddatda bajarishga majburiyat oladi: {data.get('deadline', '')}."),
            ("4. TOMONLARNING JAVOBGARLIGI",
             "Tomonlar O'zbekiston Respublikasining amaldagi qonunchiligiga muvofiq "
             "ushbu shartnoma shartlarini bajarmaganlik uchun javobgar bo'ladilar."),
        ]

    for clause_title, clause_body in clauses:
        elements.append(Paragraph(clause_title, styles["label"]))
        elements.append(Paragraph(clause_body, styles["body"]))
        elements.append(Spacer(1, 0.2*cm))

    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MUTED_COLOR, spaceAfter=12))

    sign_label = "ПОДПИСИ СТОРОН" if lang == "ru" else "TOMONLARNING IMZOLARI"
    exec_label = "Исполнитель" if lang == "ru" else "Ijrochi"
    client_label = "Заказчик" if lang == "ru" else "Buyurtmachi"

    elements.append(Paragraph(sign_label, styles["label"]))
    sign_table = Table(
        [[f"{exec_label}: ________________", f"{client_label}: ________________"]],
        colWidths=[8*cm, 8*cm]
    )
    sign_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(sign_table)

    return _build_pdf(elements)


def generate_invoice(data: dict, lang: str) -> bytes:
    styles = _base_styles()
    elements = []

    title = "СЧЁТ НА ОПЛАТУ" if lang == "ru" else "HISOB-FAKTURA"
    elements.append(Paragraph(title, styles["title"]))
    elements.append(Paragraph(f"№ СЧ-{TODAY.replace('.', '')} от {TODAY}", styles["subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR, spaceAfter=16))

    if lang == "ru":
        elements.append(Paragraph(f"<b>Поставщик:</b> {data.get('company', '')}", styles["body"]))
        elements.append(Paragraph(f"<b>Покупатель:</b> {data.get('client', '')}", styles["body"]))
        if data.get("bank"):
            elements.append(Paragraph(f"<b>Реквизиты:</b> {data.get('bank', '')}", styles["body"]))
        elements.append(Spacer(1, 0.5*cm))
        header = ["№", "Наименование", "Кол-во", "Цена (сум)", "Сумма (сум)"]
    else:
        elements.append(Paragraph(f"<b>Yetkazib beruvchi:</b> {data.get('company', '')}", styles["body"]))
        elements.append(Paragraph(f"<b>Xaridor:</b> {data.get('client', '')}", styles["body"]))
        if data.get("bank"):
            elements.append(Paragraph(f"<b>Rekvizitlar:</b> {data.get('bank', '')}", styles["body"]))
        elements.append(Spacer(1, 0.5*cm))
        header = ["№", "Nomi", "Miqdori", "Narx (so'm)", "Summa (so'm)"]

    try:
        qty = int(data.get("quantity", 1))
        price = int(data.get("price", 0))
        total = qty * price
        total_str = f"{total:,}".replace(",", " ")
        price_str = f"{price:,}".replace(",", " ")
    except:
        qty = data.get("quantity", "1")
        price_str = data.get("price", "0")
        total_str = "—"

    rows = [
        header,
        ["1", data.get("product", ""), str(qty), price_str, total_str],
    ]

    table = Table(rows, colWidths=[1*cm, 7*cm, 2*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), SECONDARY_COLOR),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_COLOR),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECONDARY_COLOR]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))

    total_label = f"Итого к оплате: {total_str} сум" if lang == "ru" else f"Jami to'lov: {total_str} so'm"
    elements.append(Paragraph(f"<b>{total_label}</b>", styles["value"]))
    elements.append(Spacer(1, 1*cm))

    footer = "Оплата в течение 3 банковских дней." if lang == "ru" else "To'lov 3 ish kuni ichida amalga oshiriladi."
    elements.append(Paragraph(footer, styles["footer"]))

    return _build_pdf(elements)