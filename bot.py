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

# ✅ ID твоего стикера
STICKER_ID = "CAACAgIAAxkBAAIXo2mJlDUnJgJtip4xMw6mOz75nLKCAAKtcQACB4pYS9zy4G9qyrjcOgQ"


@dp.message(Command("start"))
async def start(message: Message):
    # Отправляем стикер
    await message.answer_sticker(STICKER_ID)

    # Кнопка товара
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

    # Текст + кнопка
    await message.answer(
        "Выберите товар 📞:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "product_apvp")
async def apvp_product(call: CallbackQuery):
    await call.message.edit_text("Вы выбрали 🧊 A-PVP 🧊")
    await call.answer()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
