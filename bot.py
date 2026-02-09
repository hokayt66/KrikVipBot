import os
import json
import time
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StorageKey

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

STICKER_ID = "CAACAgIAAxkBAAIXo2mJlDUnJgJtip4xMw6mOz75nLKCAAKtcQACB4pYS9zy4G9qyrjcOgQ"

ORDERS_FILE = "orders.json"
FSM_FILE = "fsm_storage.json"

ORDER_TIMEOUT = 15 * 60
REMINDER_TIME = 5 * 60

# ================== JSON FSM STORAGE ==================

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
        # Обязательный метод для BaseStorage (aiogram 3.4.1)
        pass

# ================== BOT ==================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=JsonFSMStorage(FSM_FILE))

# ================== FSM ==================

class OrderState(StatesGroup):
    choosing_weight = State()
    choosing_area = State()
    confirming = State()
    waiting_payment = State()

# ================== DATA ==================

TEST_PRODUCTS = {
    "test_025": "🧊 TEST 0.25g 🧊",
    "test_05": "🧊 TEST 0.5g 🧊",
    "test_1": "🧊 TEST 1g 🧊",
    "test_2": "🧊 TEST 2g 🧊",
}

TEST_PRICES = {
    "test_025": 1,
    "test_05": 3,
    "test_1": 5,
    "test_2": 7,
}

TEST_AREAS = {
    "test_025": ["🏠 Харьковская 🏠", "🏠 СКД 🏠"],
    "test_05": ["🏠 Прокофьева 🏠", "🏠 9ка 🏠", "🏠 12й 🏠"],
    "test_1": ["🏠 Химик 🏠", "🏠 СКД 🏠"],
    "test_2": [
        "🏠 Харьковская 🏠",
        "🏠 СКД 🏠",
        "🏠 Прокофьева 🏠",
        "🏠 9ка 🏠",
        "🏠 12й 🏠",
        "🏠 Химик 🏠",
    ],
}

# ================== STORAGE ==================

active_timers = {}

def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return {}
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_orders(data):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

orders_store = load_orders()

# ================== HELPERS ==================

async def has_active_order(user_id: int, state: FSMContext) -> bool:
    if str(user_id) in orders_store:
        return True
    return await state.get_state() is not None

# ================== TIMERS ==================

async def reminder_task(user_id: int, delay: int):
    await asyncio.sleep(delay)
    await bot.send_message(user_id, "⏰ Напоминание!\nДо отмены заказа осталось 5 минут.")

async def timeout_task(user_id: int, delay: int):
    await asyncio.sleep(delay)

    orders_store.pop(str(user_id), None)
    save_orders(orders_store)

    try:
        ctx = dp.fsm.get_context(bot, user_id, user_id)
        await ctx.clear()
    except:
        pass

    await bot.send_message(user_id, "❌ Время на оплату истекло.\nЗаказ отменён.")

def restore_timers():
    now = int(time.time())

    for user_id, order in list(orders_store.items()):
        created = order.get("created_at", now)
        remaining = ORDER_TIMEOUT - (now - created)

        if remaining <= 0:
            orders_store.pop(user_id, None)
            continue

        uid = int(user_id)

        r_task = None
        if remaining > REMINDER_TIME:
            r_task = asyncio.create_task(
                reminder_task(uid, remaining - REMINDER_TIME)
            )

        t_task = asyncio.create_task(timeout_task(uid, remaining))
        active_timers[uid] = (t_task, r_task)

    save_orders(orders_store)

# ================== START ==================

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer_sticker(STICKER_ID)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧊 TEST 🧊", callback_data="product_test")],
            [InlineKeyboardButton(text="🙋‍♀️ Оператор 🙋‍♀️", url="https://example.com")],
            [InlineKeyboardButton(text="📢 Чат 📢", url="https://example.com")],
            [InlineKeyboardButton(text="🚴‍♀️ Ищу курьера 🚴‍♀️", url="https://example.com")],
        ]
    )

    await message.answer("Главное меню (Сумы)📞:", reply_markup=keyboard)

# ================== PRODUCT ==================

@dp.callback_query(F.data == "product_test")
async def choose_weight(call: CallbackQuery, state: FSMContext):
    if await has_active_order(call.from_user.id, state):
        await call.answer(
            "❗ У вас уже есть активный заказ.\nЗавершите его или дождитесь отмены.",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=v, callback_data=k)]
            for k, v in TEST_PRODUCTS.items()
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_start")]]
    )

    await state.set_state(OrderState.choosing_weight)
    await call.message.edit_text("🧊 TEST\nВыберите вес:", reply_markup=keyboard)
    await call.answer()

# ================== AREA ==================

@dp.callback_query(F.data.in_(TEST_PRODUCTS))
async def choose_area(call: CallbackQuery, state: FSMContext):
    await state.update_data(
        product_key=call.data,
        product_name=TEST_PRODUCTS[call.data],
        price=TEST_PRICES[call.data],
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=a, callback_data=f"area_{i}")]
            for i, a in enumerate(TEST_AREAS[call.data])
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="product_test")]]
    )

    await state.set_state(OrderState.choosing_area)
    await call.message.edit_text(
        f"{TEST_PRODUCTS[call.data]}\nВыберите район:",
        reply_markup=keyboard
    )
    await call.answer()

# ================== CONFIRM ==================

@dp.callback_query(F.data.startswith("area_"))
async def confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = int(call.data.split("_")[1])
    area = TEST_AREAS[data["product_key"]][idx]

    await state.update_data(area=area)
    await state.set_state(OrderState.confirming)

    text = (
        "🧾 Подтверждение заказа\n\n"
        f"{data['product_name']}\n"
        f"Район: {area}\n"
        f"Сумма: {data['price']} грн\n\n"
        "Подтвердить покупку?"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить ✅", callback_data="confirm_payment")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=data["product_key"])],
        ]
    )

    await call.message.edit_text(text, reply_markup=keyboard)
    await call.answer()

# ================== PAYMENT ==================

@dp.callback_query(F.data == "confirm_payment")
async def payment(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    data = await state.get_data()

    if str(user_id) in orders_store:
        await call.answer("❗ Заказ уже существует", show_alert=True)
        return

    data["created_at"] = int(time.time())
    orders_store[str(user_id)] = data
    save_orders(orders_store)

    r = asyncio.create_task(reminder_task(user_id, ORDER_TIMEOUT - REMINDER_TIME))
    t = asyncio.create_task(timeout_task(user_id, ORDER_TIMEOUT))
    active_timers[user_id] = (t, r)

    await state.set_state(OrderState.waiting_payment)

    await call.message.edit_text(
        "💳 PAYMENT_DETAILS_HERE 💳\n\n"
        f"🏷️ {data['price']} грн 🏷️\n"
        "⏳ Время на оплату: 15 минут ⏳\n\n"
        "❗ После оплаты отправьте PDF-файл напрямую боту ❗"
    )
    await call.answer()

# ================== PDF ==================

@dp.message(F.document)
async def receive_pdf(message: Message, state: FSMContext):
    if message.document.mime_type != "application/pdf":
        await message.answer("❌ Отправьте PDF файл.")
        return

    uid = message.from_user.id

    timers = active_timers.pop(uid, None)
    if timers:
        for t in timers:
            if t:
                t.cancel()

    orders_store.pop(str(uid), None)
    save_orders(orders_store)

    await state.clear()
    await message.answer("✅ Файл получен. Заказ завершён.")

# ================== BACK ==================

@dp.callback_query(F.data == "back_start")
async def back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await start(call.message, state)
    await call.answer()

# ================== RUN ==================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    restore_timers()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
