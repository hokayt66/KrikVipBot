import os
import json
import time
import asyncio
import tempfile

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StorageKey

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

ORDER_TIMEOUT = 15 * 60        # 15 минут
REMINDER_BEFORE = 5 * 60       # напоминание за 5 минут

ORDERS_FILE = "orders.json"
FSM_FILE = "fsm_storage.json"

STICKER_ID = "CAACAgIAAxkBAAIXo2mJlDUnJgJtip4xMw6mOz75nLKCAAKtcQACB4pYS9zy4G9qyrjcOgQ"

CARD_NUMBER = "5168240100724821"

# ================== FSM STORAGE (JSON) ==================

class JsonFSMStorage(BaseStorage):
    def __init__(self, path: str):
        self.path = path
        self.data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    async def set_state(self, key: StorageKey, state):
        uid = str(key.user_id)
        self.data.setdefault(uid, {})["state"] = state.state if state else None
        self._save()

    async def get_state(self, key: StorageKey):
        return self.data.get(str(key.user_id), {}).get("state")

    async def set_data(self, key: StorageKey, data: dict):
        uid = str(key.user_id)
        self.data.setdefault(uid, {})["data"] = data
        self._save()

    async def get_data(self, key: StorageKey):
        return self.data.get(str(key.user_id), {}).get("data", {})

    async def clear(self, key: StorageKey):
        self.data.pop(str(key.user_id), None)
        self._save()

    async def close(self):
        pass

# ================== FSM STATES ==================

class OrderState(StatesGroup):
    choosing = State()
    confirming = State()
    waiting_payment = State()

# ================== ДАННЫЕ ==================

PRODUCTS = {
    "0.25": 1,
    "0.5": 3,
    "1": 5,
    "2": 7,
}

REGIONS = [
    "🏠 Харьковская 🏠",
    "🏠 СКД 🏠",
    "🏠 Прокофьева 🏠",
    "🏠 9ка 🏠",
    "🏠 12й 🏠",
    "🏠 Химик 🏠",
]

# ================== ЗАКАЗЫ ==================

def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return {}
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(data):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

orders = load_orders()
timers = {}

# ================== BOT ==================

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=JsonFSMStorage(FSM_FILE))

# ================== ТАЙМЕРЫ ==================

async def reminder_timer(uid: int):
    await asyncio.sleep(ORDER_TIMEOUT - REMINDER_BEFORE)
    if str(uid) in orders:
        await bot.send_message(uid, "⏰ Напоминание: до отмены заказа осталось 5 минут")

async def cancel_timer(uid: int):
    await asyncio.sleep(ORDER_TIMEOUT)
    if str(uid) in orders:
        orders.pop(str(uid), None)
        save_orders(orders)
        ctx = dp.fsm.get_context(bot, uid, uid)
        await ctx.clear()
        await bot.send_message(uid, "❌ Заказ отменён по тайм-ауту")

# ================== START ==================

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer_sticker(STICKER_ID)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧊 TEST 🧊", callback_data="product_test")],
        [InlineKeyboardButton(text="🙋‍♀️ Оператор 🙋‍♀️", url="https://t.me/KrikVip")],
        [InlineKeyboardButton(text="📢 Чат 📢", url="https://t.me/KrikVip")],
        [InlineKeyboardButton(text="🚴‍♀️ Ищу курьера 🚴‍♀️", url="https://t.me/KrikVip")],
    ])

    await message.answer(
        "Главное меню (Сумы)📞:",
        reply_markup=kb
    )

# ================== ВЫБОР ВЕСА ==================

@dp.callback_query(F.data == "product_test")
async def choose_weight(call: CallbackQuery, state: FSMContext):
    uid = str(call.from_user.id)
    if uid in orders:
        await call.answer("❗ У вас уже есть активный заказ", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🧊 TEST {w}g 🧊", callback_data=f"w_{w}")]
            for w in PRODUCTS
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]]
    )

    await state.set_state(OrderState.choosing)
    await call.message.edit_text("Выберите вес:", reply_markup=kb)

@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await start(call.message, state)

# ================== ВЫБОР РАЙОНА ==================

@dp.callback_query(F.data.startswith("w_"))
async def choose_region(call: CallbackQuery, state: FSMContext):
    weight = call.data.replace("w_", "")
    price = PRODUCTS[weight]

    await state.update_data(weight=weight, price=price)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=r, callback_data=f"r_{i}")]
            for i, r in enumerate(REGIONS)
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="product_test")]]
    )

    await call.message.edit_text(
        f"Вес: {weight}g\nЦена: {price} грн\n\nВыберите район:",
        reply_markup=kb
    )

# ================== ПОДТВЕРЖДЕНИЕ ==================

@dp.callback_query(F.data.startswith("r_"))
async def confirm_order(call: CallbackQuery, state: FSMContext):
    region = REGIONS[int(call.data.replace("r_", ""))]
    data = await state.get_data()

    await state.update_data(region=region)
    await state.set_state(OrderState.confirming)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить ✅", callback_data="confirm_pay")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="product_test")],
    ])

    await call.message.edit_text(
        f"📦 Заказ:\n"
        f"Товар: TEST {data['weight']}g\n"
        f"Район: {region}\n"
        f"Цена: {data['price']} грн\n\n"
        f"Подтвердить заказ?",
        reply_markup=kb
    )

# ================== ОПЛАТА ==================

@dp.callback_query(F.data == "confirm_pay")
async def payment(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    data = await state.get_data()

    orders[str(uid)] = {
        "price": data["price"],
        "created_at": int(time.time())
    }
    save_orders(orders)

    timers[uid] = (
        asyncio.create_task(reminder_timer(uid)),
        asyncio.create_task(cancel_timer(uid)),
    )

    await state.set_state(OrderState.waiting_payment)

    await call.message.edit_text(
        f"💳 {CARD_NUMBER} 💳\n"
        f"🏷️ {data['price']} грн 🏷️\n"
        f"⏳ На оплату 15 минут ⏳\n\n"
        f"❗ После оплаты отправьте электронный чек (PDF) ❗"
    )

# ================== ПРОВЕРКА PDF ==================

def check_pdf_stub(pdf_path: str, created_at: int, price: int) -> dict:
    """
    Заглушка.
    Пока просто имитирует проверку.
    """
    return {"status": "reject", "reason": "Автопроверка ещё не настроена"}

@dp.message(OrderState.waiting_payment, F.document)
async def pdf_handler(message: Message, state: FSMContext):
    if message.document.mime_type != "application/pdf":
        await message.answer("❌ Отправьте PDF файл")
        return

    uid = message.from_user.id
    order = orders.get(str(uid))

    if not order:
        await message.answer("❌ Активный заказ не найден")
        return

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        pdf_path = tmp.name

    # ✅ ЕДИНСТВЕННЫЙ КОРРЕКТНЫЙ СПОСОБ ДЛЯ AIORAM 3
    file = await bot.get_file(message.document.file_id)
    await bot.download_file(file.file_path, destination=pdf_path)

    result = check_pdf_stub(pdf_path, order["created_at"], order["price"])

    os.remove(pdf_path)

    if result["status"] == "ok":
        for t in timers.pop(uid, []):
            t.cancel()

        orders.pop(str(uid), None)
        save_orders(orders)
        await state.clear()

        await message.answer("✅ Платёж подтверждён автоматически")
        return

    await message.answer(
        f"❌ Чек отклонён\nПричина: {result.get('reason', 'неизвестно')}"
    )

# ================== RUN ==================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
