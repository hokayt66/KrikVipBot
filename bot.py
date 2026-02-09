import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

STICKER_ID = "CAACAgIAAxkBAAIXo2mJlDUnJgJtip4xMw6mOz75nLKCAAKtcQACB4pYS9zy4G9qyrjcOgQ"

# ---------- ДАННЫЕ ----------

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

# временное хранилище заказов
user_orders = {}

# ---------- START ----------

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer_sticker(STICKER_ID)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧊 TEST 🧊", callback_data="product_test")],
            [InlineKeyboardButton(text="🙋‍♀️ Оператор 🙋‍♀️", url="https://example.com")],
            [InlineKeyboardButton(text="📢 Чат 📢", url="https://example.com")],
            [InlineKeyboardButton(text="🚴‍♀️ Ищу курьера 🚴‍♀️", url="https://example.com")],
        ]
    )

    await message.answer(
        "Главное меню (Сумы)📞:",
        reply_markup=keyboard
    )

# ---------- МЕНЮ ВЕСОВ ----------

@dp.callback_query(F.data == "product_test")
async def test_menu(call: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=key)]
            for key, name in TEST_PRODUCTS.items()
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_start")]]
    )

    await call.message.edit_text(
        "🧊 TEST\nВыберите вес:",
        reply_markup=keyboard
    )
    await call.answer()

# ---------- РАЙОНЫ ----------

@dp.callback_query(F.data.in_(TEST_PRODUCTS.keys()))
async def test_areas(call: CallbackQuery):
    user_orders[call.from_user.id] = {
        "product_key": call.data,
        "product_name": TEST_PRODUCTS[call.data],
        "price": TEST_PRICES[call.data],
    }

    areas = TEST_AREAS.get(call.data, [])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=area,
                    callback_data=f"area_{i}"
                )
            ]
            for i, area in enumerate(areas)
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="product_test")]]
    )

    await call.message.edit_text(
        f"{TEST_PRODUCTS[call.data]}\nВыберите район:",
        reply_markup=keyboard
    )
    await call.answer()

# ---------- ПОДТВЕРЖДЕНИЕ ----------

@dp.callback_query(F.data.startswith("area_"))
async def confirm_order(call: CallbackQuery):
    order = user_orders.get(call.from_user.id)
    if not order:
        await call.answer("Ошибка заказа", show_alert=True)
        return

    product_key = order["product_key"]
    area_index = int(call.data.split("_")[1])
    area = TEST_AREAS[product_key][area_index]

    order["area"] = area

    text = (
        "🧾 Подтверждение заказа\n\n"
        f"{order['product_name']}\n"
        f"Район: {area}\n"
        f"Сумма: {order['price']} грн\n\n"
        "Подтвердить покупку?"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить ✅", callback_data="confirm_payment")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=product_key)],
        ]
    )

    await call.message.edit_text(text, reply_markup=keyboard)
    await call.answer()

# ---------- ОПЛАТА (НЕЙТРАЛЬНО) ----------

@dp.callback_query(F.data == "confirm_payment")
async def payment_info(call: CallbackQuery):
    order = user_orders.get(call.from_user.id)

    text = (
        "💳 PAYMENT_DETAILS_HERE 💳\n\n"
        f"🏷️ {order['price']} грн 🏷️\n"
        "⏳ Время на оплату: 15 минут ⏳\n\n"
        "❗ После оплаты отправьте PDF-файл напрямую боту ❗"
    )

    await call.message.edit_text(text)
    await call.answer()

# ---------- ПРИЁМ PDF ----------

@dp.message(F.document)
async def receive_pdf(message: Message):
    if message.document.mime_type == "application/pdf":
        await message.answer(
            "✅ Файл получен.\n"
            "Мы проверим его и свяжемся с вами."
        )
    else:
        await message.answer("❌ Пожалуйста, отправьте файл в формате PDF.")

# ---------- НАЗАД ----------

@dp.callback_query(F.data == "back_start")
async def back_to_start(call: CallbackQuery):
    await start(call.message)
    await call.answer()

# ---------- RUN ----------

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
