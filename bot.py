from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8500086703:AAGtpZuc3RZjUEspm5kQ9tOL-97lbrJX6g8"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Кнопка 1", callback_data="btn_1")],
        [InlineKeyboardButton("Кнопка 2", callback_data="btn_2")],
        [InlineKeyboardButton("Кнопка 3", callback_data="btn_3")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привет 👋\nВыбери кнопку ниже:",
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_1":
        text = "Ты нажал Кнопку 1"
    elif query.data == "btn_2":
        text = "Ты нажал Кнопку 2"
    elif query.data == "btn_3":
        text = "Ты нажал Кнопку 3"
    else:
        text = "Неизвестная кнопка"

    await query.edit_message_text(text=text)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
