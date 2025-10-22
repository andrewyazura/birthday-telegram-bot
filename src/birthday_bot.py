from datetime import time
from warnings import filterwarnings

import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.warnings import PTBUserWarning

import src.core.logger
from src.handlers.reminder import reminder

filterwarnings(
    action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
)

from src.core.config import BOT_TOKEN
from src.handlers.add import add_conv_handler
from src.handlers.change import change_conv_handler
from src.handlers.delete import delete_conv_handler
from src.handlers.list import list_birthdays
from src.handlers.start import start


def main() -> None:
    """BirthdayBot main function.

    Create and start polling an application with handlers for manipulating birthdays using
    [birthday-api](https://github.com/orehzzz/birthday-api).

    Send a daily reminder about the birthdays
    """

    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
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


async def post_init(application: ApplicationBuilder) -> None:
    """Post initialization function for the bot.

    Set bot's name, short/long description and commands.
    """
    # Comment this if you need to restart the bot several times
    await application.bot.set_my_name("BirthdayBot")
    await application.bot.set_my_short_description("To remember everyone's birthday!")
    await application.bot.set_my_description(
        "This bot helps you to remember everyone's birthday.\n"
        "You can add, change, delete and list birthdays.\n"
        "It also sends you a daily reminder about upcoming birthdays."
    )

    # /start is excluded from the commands list
    await application.bot.set_my_commands(
        [
            ("list", "list all birthdays"),
            ("add", "add a birthday"),
            ("change", "change a birthday"),
            ("delete", "delete a birthday"),
            (
                "skip",
                "skip the current action (if possible) during /add or /change commands",
            ),
            ("stop", "dissrupt current dialogue"),
        ]
    )


if __name__ == "__main__":
    main()
