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

TEST_AREAS = {
    "test_025": [
        "🏠 Харьковская 🏠",
        "🏠 СКД 🏠",
    ],
    "test_05": [
        "🏠 Прокофьева 🏠",
        "🏠 9ка 🏠",
        "🏠 12й 🏠",
    ],
    "test_1": [
        "🏠 Химик 🏠",
        "🏠 СКД 🏠",
    ],
    "test_2": [
        "🏠 Харьковская 🏠",
        "🏠 СКД 🏠",
        "🏠 Прокофьева 🏠",
        "🏠 9ка 🏠",
        "🏠 12й 🏠",
        "🏠 Химик 🏠",
    ],
}

# ---------- START ----------

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer_sticker(STICKER_ID)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧊 TEST 🧊", callback_data="product_test")]
        ]
    )

    await message.answer(
        "Выберите товар 📞:",
        reply_markup=keyboard
    )

# ---------- МЕНЮ TEST ----------

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
    areas = TEST_AREAS.get(call.data, [])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=area, callback_data="selected_area")]
            for area in areas
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="product_test")]]
    )

    await call.message.edit_text(
        f"{TEST_PRODUCTS[call.data]}\nВыберите район:",
        reply_markup=keyboard
    )
    await call.answer()

# ---------- ВЫБОР РАЙОНА (пока заглушка) ----------

@dp.callback_query(F.data == "selected_area")
async def area_selected(call: CallbackQuery):
    await call.message.edit_text(
        "Район выбран ✅"
    )
    await call.answer()

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
