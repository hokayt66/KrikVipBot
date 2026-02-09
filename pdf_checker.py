import re
import pdfplumber
from datetime import datetime, timedelta

# ------------------ CONFIG ------------------

CARD_LAST4 = "4821"
TIME_WINDOW_MINUTES = 15

BANK_SIGNATURES = {
    "monobank": [
        "monobank",
        "Платіж успішний",
        "Картка",
        "Сума"
    ],
    "privatbank": [
        "ПриватБанк",
        "Оплата",
        "UAH",
        "Картка"
    ]
}

# ------------------ HELPERS ------------------

def extract_text_from_pdf(path: str) -> str | None:
    try:
        with pdfplumber.open(path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip() if text.strip() else None
    except Exception:
        return None


def detect_bank(text: str) -> str:
    lower = text.lower()
    for bank, signs in BANK_SIGNATURES.items():
        matches = sum(1 for s in signs if s.lower() in lower)
        if matches >= 2:
            return bank
    return "unknown"


def extract_amount(text: str) -> float | None:
    # ищем 1 234.56 или 1234,56 UAH
    match = re.search(r"(\d+[.,]\d{2})\s*(uah|грн)", text.lower())
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def extract_time(text: str) -> datetime | None:
    # 09.02.2026 21:05
    match = re.search(r"(\d{2}\.\d{2}\.\d{4}).*?(\d{2}:\d{2})", text)
    if not match:
        return None
    dt_str = f"{match.group(1)} {match.group(2)}"
    try:
        return datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
    except ValueError:
        return None


def card_present(text: str) -> bool:
    return CARD_LAST4 in text.replace(" ", "")

# ------------------ MAIN CHECK ------------------

def check_pdf(
    pdf_path: str,
    created_at: int,
    expected_amount: float
) -> dict:

    text = extract_text_from_pdf(pdf_path)
    if not text:
        return {
            "status": "reject",
            "reason": "PDF не содержит текста (скан или подделка)"
        }

    bank = detect_bank(text)

    amount = extract_amount(text)
    if amount is None:
        return {
            "status": "reject",
            "reason": "Не найдена сумма"
        }

    if amount != expected_amount:
        return {
            "status": "reject",
            "reason": f"Сумма не совпадает ({amount})"
        }

    if not card_present(text):
        return {
            "status": "reject",
            "reason": "Карта не совпадает"
        }

    payment_time = extract_time(text)
    if not payment_time:
        return {
            "status": "suspicious",
            "bank": bank,
            "reason": "Не удалось определить время платежа"
        }

    created_dt = datetime.fromtimestamp(created_at)
    if not (created_dt <= payment_time <= created_dt + timedelta(minutes=TIME_WINDOW_MINUTES)):
        return {
            "status": "reject",
            "reason": "Платёж вне допустимого времени"
        }

    return {
        "status": "ok",
        "bank": bank,
        "found_amount": amount,
        "found_time": payment_time.strftime("%d.%m.%Y %H:%M")
    }
