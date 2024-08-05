from telegram import Update, BotCommand, Bot
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.warnings import PTBUserWarning
from warnings import filterwarnings

filterwarnings(
    action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
)

from core.config import BOT_TOKEN
from handlers.add import add_conv_handler
from handlers.change import change_conv_handler
from handlers.delete import delete_conv_handler
from handlers.list import list_birthdays


def main() -> None:
    """BirthdayBot main function.

    Create and start polling an application with handlers for manipulating birthdays.

    """

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(add_conv_handler)
    application.add_handler(change_conv_handler)
    application.add_handler(delete_conv_handler)
    application.add_handler(CommandHandler("list", list_birthdays))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
