import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кнопка 1", callback_data="btn_1")],
        [InlineKeyboardButton(text="Кнопка 2", callback_data="btn_2")],
        [InlineKeyboardButton(text="Кнопка 3", callback_data="btn_3")],
    ])

    await message.answer(
        "Привет 👋\nВыбери кнопку ниже:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("btn_"))
async def buttons(call: CallbackQuery):
    texts = {
        "btn_1": "Ты нажал Кнопку 1",
        "btn_2": "Ты нажал Кнопку 2",
        "btn_3": "Ты нажал Кнопку 3",
    }

    await call.message.edit_text(texts.get(call.data, "Неизвестная кнопка"))
    await call.answer()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
