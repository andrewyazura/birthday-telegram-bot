from telegram import Update, BotCommand, Bot
from telegram.ext import ApplicationBuilder

from core.config import BOT_TOKEN
from handlers.add import add_conv_handler


def main() -> None:
    """BirthdayBot main function.

    Create and start polling an application with handlers for manipulating birthdays.

    """

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(add_conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
