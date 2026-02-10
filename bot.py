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

from pdf_checker import check_pdf

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

ORDER_TIMEOUT = 15 * 60
REMINDER_TIME = 5 * 60

ORDERS_FILE = "orders.json"
FSM_FILE = "fsm_storage.json"

# ================= FSM STORAGE =================

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

# ================= BOT =================

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=JsonFSMStorage(FSM_FILE))

# ================= FSM =================

class OrderState(StatesGroup):
    choosing = State()
    confirming = State()
    waiting_payment = State()

# ================= PRODUCTS =================

PRODUCTS = {
    "0.25": 1,
    "0.5": 3,
    "1": 5,
    "2": 7,
}

# ================= ORDERS =================

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

# ================= TIMERS =================

async def reminder(uid: int):
    await asyncio.sleep(ORDER_TIMEOUT - REMINDER_TIME)
    await bot.send_message(uid, "⏰ Напоминание: до отмены заказа 5 минут")

async def timeout(uid: int):
    await asyncio.sleep(ORDER_TIMEOUT)
    orders.pop(str(uid), None)
    save_orders(orders)
    ctx = dp.fsm.get_context(bot, uid, uid)
    await ctx.clear()
    await bot.send_message(uid, "❌ Заказ отменён по тайм-ауту")

# ================= START =================

@dp.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧊 TEST 🧊", callback_data="test")],
    ])

    await msg.answer("Главное меню (Сумы)📞:", reply_markup=kb)

# ================= FLOW =================

@dp.callback_query(F.data == "test")
async def choose(call: CallbackQuery, state: FSMContext):
    if str(call.from_user.id) in orders:
        await call.answer("❗ У вас уже есть активный заказ", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{k}g — {v} грн", callback_data=k)]
            for k, v in PRODUCTS.items()
        ]
    )

    await state.set_state(OrderState.choosing)
    await call.message.edit_text("Выберите товар:", reply_markup=kb)

@dp.callback_query(F.data.in_(PRODUCTS))
async def confirm(call: CallbackQuery, state: FSMContext):
    price = PRODUCTS[call.data]

    await state.update_data(weight=call.data, price=price)
    await state.set_state(OrderState.confirming)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="pay")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="test")],
    ])

    await call.message.edit_text(
        f"Товар: {call.data}g\nЦена: {price} грн\n\nПодтвердить заказ?",
        reply_markup=kb
    )

@dp.callback_query(F.data == "pay")
async def pay(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    data = await state.get_data()

    orders[str(uid)] = {
        "price": data["price"],
        "created_at": int(time.time())
    }
    save_orders(orders)

    timers[uid] = (
        asyncio.create_task(reminder(uid)),
        asyncio.create_task(timeout(uid))
    )

    await state.set_state(OrderState.waiting_payment)

    await call.message.edit_text(
        f"💳 5168240100724821 💳\n"
        f"🏷️ {data['price']} грн 🏷️\n"
        f"⏳ На оплату 15 минут ⏳\n\n"
        f"❗ После оплаты отправьте PDF-чек"
    )

# ================= PDF HANDLER =================

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

    # ✅ ПРАВИЛЬНО для aiogram 3
    await bot.download(message.document, destination=pdf_path)

    result = check_pdf(
        pdf_path,
        order["created_at"],
        order["price"]
    )

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
        f"❌ Чек не принят\nПричина: {result.get('reason','неизвестно')}"
    )

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
