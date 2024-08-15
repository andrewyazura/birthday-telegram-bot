from datetime import time
import pytz

from telegram import Update, BotCommand, Bot
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.warnings import PTBUserWarning
from warnings import filterwarnings

from handlers.reminder import reminder

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

    Create and start polling an application with handlers for manipulating birthdays using
    [birthday-api](https://github.com/orehzzz/birthday-api).

    Send a daily reminder about the birthdays
    """

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(add_conv_handler)
    application.add_handler(change_conv_handler)
    application.add_handler(delete_conv_handler)
    application.add_handler(CommandHandler("list", list_birthdays))

    job_queue = application.job_queue
    job_queue.run_daily(
        callback=reminder,
        time=time(hour=10, tzinfo=pytz.timezone("Europe/Kyiv")),
    )

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
