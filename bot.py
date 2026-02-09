import os
import json
import time
import asyncio
import tempfile

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StorageKey

from pdf_checker import check_pdf

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

STICKER_ID = "CAACAgIAAxkBAAIXo2mJlDUnJgJtip4xMw6mOz75nLKCAAKtcQACB4pYS9zy4G9qyrjcOgQ"

ORDER_TIMEOUT = 15 * 60
REMINDER_TIME = 5 * 60

ORDERS_FILE = "orders.json"
FSM_FILE = "fsm_storage.json"

# ================== FSM STORAGE ==================

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

# ================== BOT ==================

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=JsonFSMStorage(FSM_FILE))

# ================== FSM ==================

class OrderState(StatesGroup):
    choosing_weight = State()
    choosing_area = State()
    confirming = State()
    waiting_payment = State()
    checking_pdf = State()

# ================== DATA ==================

PRODUCTS = {
    "t025": ("🧊 TEST 0.25g 🧊", 1),
    "t05": ("🧊 TEST 0.5g 🧊", 3),
    "t1": ("🧊 TEST 1g 🧊", 5),
    "t2": ("🧊 TEST 2g 🧊", 7),
}

AREAS = {
    "t025": ["🏠 Харьковская 🏠", "🏠 СКД 🏠"],
    "t05": ["🏠 Прокофьева 🏠", "🏠 9ка 🏠"],
    "t1": ["🏠 Химик 🏠"],
    "t2": ["🏠 Харьковская 🏠", "🏠 СКД 🏠", "🏠 9ка 🏠"],
}

# ================== ORDERS ==================

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

# ================== TIMERS ==================

async def reminder(uid):
    await asyncio.sleep(ORDER_TIMEOUT - REMINDER_TIME)
    await bot.send_message(uid, "⏰ Напоминание: до отмены заказа 5 минут.")

async def timeout(uid):
    await asyncio.sleep(ORDER_TIMEOUT)
    orders.pop(str(uid), None)
    save_orders(orders)
    ctx = dp.fsm.get_context(bot, uid, uid)
    await ctx.clear()
    await bot.send_message(uid, "❌ Заказ отменён по тайм-ауту.")

def restore_timers():
    now = int(time.time())
    for uid, data in list(orders.items()):
        left = ORDER_TIMEOUT - (now - data["created_at"])
        if left <= 0:
            orders.pop(uid, None)
            continue
        uid_i = int(uid)
        timers[uid_i] = (
            asyncio.create_task(reminder(uid_i)),
            asyncio.create_task(timeout(uid_i))
        )
    save_orders(orders)

# ================== START ==================

@dp.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer_sticker(STICKER_ID)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧊 TEST 🧊", callback_data="test")],
        [InlineKeyboardButton(text="🙋‍♀️ Оператор 🙋‍♀️", url="https://t.me/KrikVip")],
        [InlineKeyboardButton(text="📢 Чат 📢", url="https://t.me/KrikVip")],
        [InlineKeyboardButton(text="🚴‍♀️ Ищу курьера 🚴‍♀️", url="https://t.me/KrikVip")],
    ])

    await msg.answer("Главное меню (Сумы)📞:", reply_markup=kb)

# ================== PRODUCT FLOW ==================

@dp.callback_query(F.data == "test")
async def choose_weight(call: CallbackQuery, state: FSMContext):
    if str(call.from_user.id) in orders:
        await call.answer("❗ У вас уже есть активный заказ", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=v[0], callback_data=k)]
            for k, v in PRODUCTS.items()
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    )

    await state.set_state(OrderState.choosing_weight)
    await call.message.edit_text("Выберите вес:", reply_markup=kb)

@dp.callback_query(F.data.in_(PRODUCTS))
async def choose_area(call: CallbackQuery, state: FSMContext):
    name, price = PRODUCTS[call.data]
    await state.update_data(key=call.data, name=name, price=price)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=a, callback_data=f"area_{i}")]
            for i, a in enumerate(AREAS[call.data])
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="test")]]
    )

    await state.set_state(OrderState.choosing_area)
    await call.message.edit_text("Выберите район:", reply_markup=kb)

@dp.callback_query(F.data.startswith("area_"))
async def confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    area = AREAS[data["key"]][int(call.data.split("_")[1])]
    await state.update_data(area=area)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить ✅", callback_data="pay")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=data["key"])],
    ])

    await state.set_state(OrderState.confirming)
    await call.message.edit_text(
        f"{data['name']}\nРайон: {area}\nЦена: {data['price']} грн\n\nПодтвердить?",
        reply_markup=kb
    )

# ================== PAYMENT ==================

@dp.callback_query(F.data == "pay")
async def payment(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    data = await state.get_data()

    orders[str(uid)] = {**data, "created_at": int(time.time())}
    save_orders(orders)

    timers[uid] = (
        asyncio.create_task(reminder(uid)),
        asyncio.create_task(timeout(uid))
    )

    await state.set_state(OrderState.waiting_payment)
    await call.message.edit_text(
        f"💳 5168240100724821 💳\n"
        f"🏷️ {data['price']} грн 🏷️\n"
        f"⏳ 15 минут ⏳\n\n"
        f"После оплаты отправьте PDF-чек"
    )

# ================== PDF (STRICT FSM) ==================

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

    await state.set_state(OrderState.checking_pdf)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        await message.document.download(destination=tmp.name)
        pdf_path = tmp.name

    result = check_pdf(pdf_path, order["created_at"], order["price"])
    os.unlink(pdf_path)

    if result.get("status") == "ok":
        for t in timers.pop(uid, []):
            t.cancel()

        orders.pop(str(uid), None)
        save_orders(orders)
        await state.clear()
        await message.answer("✅ Платёж подтверждён автоматически")
        return

    if result.get("status") == "reject":
        await state.set_state(OrderState.waiting_payment)
        await message.answer(f"❌ Чек отклонён\nПричина: {result.get('reason')}")
        return

    # suspicious
    await state.set_state(OrderState.waiting_payment)
    await message.answer("⚠️ Чек отправлен на ручную проверку оператору")

    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"⚠️ Подозрительный чек от {uid}\n{result}"
        )

# ================== BACK ==================

@dp.callback_query(F.data == "back")
async def back(call: CallbackQuery, state: FSMContext):
    await start(call.message, state)

# ================== RUN ==================

async def main():
    restore_timers()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
