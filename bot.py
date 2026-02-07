import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Кнопка 1", callback_data="btn_1")],
        [InlineKeyboardButton("Кнопка 2", callback_data="btn_2")],
        [InlineKeyboardButton("Кнопка 3", callback_data="btn_3")],
    ]

    await update.message.reply_text(
        "Привет 👋\nВыбери кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    texts = {
        "btn_1": "Ты нажал Кнопку 1",
        "btn_2": "Ты нажал Кнопку 2",
        "btn_3": "Ты нажал Кнопку 3",
    }

    await query.edit_message_text(
        text=texts.get(query.data, "Неизвестная кнопка")
    )


def main():
    if not TOKEN:
        logging.error("BOT_TOKEN не найден")
        raise RuntimeError("BOT_TOKEN не задан")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Бот запущен")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
