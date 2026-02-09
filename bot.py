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


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer_sticker(STICKER_ID)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧊 A-PVP 🧊",
                    callback_data="product_apvp"
                )
            ]
        ]
    )

    await message.answer(
        "Выберите товар 📞:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "product_apvp")
async def apvp_menu(call: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧊A-PVP 0.25g🧊", callback_data="apvp_025")],
            [InlineKeyboardButton(text="🧊A-PVP 0.5g🧊", callback_data="apvp_05")],
            [InlineKeyboardButton(text="🧊A-PVP 1g🧊", callback_data="apvp_1")],
            [InlineKeyboardButton(text="🧊A-PVP 2g🧊", callback_data="apvp_2")],
        ]
    )

    await call.message.edit_text(
        "🧊 A-PVP\nВыберите вес:",
        reply_markup=keyboard
    )
    await call.answer()


@dp.callback_query(F.data.startswith("apvp_"))
async def apvp_weight(call: CallbackQuery):
    weights = {
        "apvp_025": "0.25g",
        "apvp_05": "0.5g",
        "apvp_1": "1g",
        "apvp_2": "2g",
    }

    weight = weights.get(call.data, "неизвестно")

    await call.message.edit_text(
        f"Вы выбрали 🧊 A-PVP {weight} 🧊"
    )
    await call.answer()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
