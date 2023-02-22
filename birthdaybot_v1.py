import datetime
import traceback

from peewee import CharField, DateField, Model, PostgresqlDatabase, TextField
from telegram.bot import Bot, BotCommand
from telegram.ext import Filters
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.conversationhandler import ConversationHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.updater import Updater

psql_db = PostgresqlDatabase("birthdays", user="postgres", password="l9999l")


class BaseModel(Model):
    class Meta:
        database = psql_db


class User(BaseModel):
    col_name = CharField()
    col_date = DateField()
    col_note = TextField(null=True)
    col_creator = CharField()


with psql_db:
    psql_db.create_tables([User])


updater = Updater("5749842477:AAE72SsmVUNh0hFhy5KwTgnICe0m_zEqTyU", use_context=True)


NAME, DATE, NOTE = range(3)


commands = [
    BotCommand("list", "your added birthdays"),
    BotCommand("add_birthday", "adds a birthday to your list"),
    BotCommand("del_birthday", "deletes a birthday from your list"),
    BotCommand("add_note", "add some info about someone"),
    BotCommand("help", "list of commands"),
    BotCommand("exit", "to stop"),
]
bot = Bot("5749842477:AAE72SsmVUNh0hFhy5KwTgnICe0m_zEqTyU")
bot.set_my_commands(commands)


def help(update, context):
    update.message.reply_text(
        """
        Commands to use:
    /list
    /add_birthday
    /del_birthday
    /add_note

    /help
    /exit
    """
    )


def add_birthday(update, context):
    update.message.reply_text("Print person's name:")
    return NAME


def _add_name(update, context):
    name = update.message.text
    context.user_data["current_name"] = name
    update.message.reply_text("Print a date (example:02.02.2002):")
    return DATE


def _add_date(update, context):
    date = update.message.text
    date = datetime.datetime.strptime(date, "%d.%m.%Y").date()
    User.create(
        col_name=context.user_data["current_name"],
        col_date=date,
        col_creator=update.effective_user.id,
    )
    update.message.reply_text("Succesfully added!")
    help(update, context)
    return ConversationHandler.END


def add_note(update, context):
    update.message.reply_text("About whom you want to add a note?(print a name)")
    list(update, context)
    return NAME


def _find_name(update, context):
    name = update.message.text
    context.user_data["current_name"] = name
    update.message.reply_text(
        """
    Print a description:
    (it could be a hint for a present or some notes for the future, etc.)
    """
    )
    return NOTE


def _add_descr(update, context):
    note = update.message.text
    User.update(col_note=note).where(
        User.col_name == context.user_data["current_name"]
    ).execute()
    update.message.reply_text("Succesfully added!")
    help(update, context)
    return ConversationHandler.END


def del_birthday(update, context):
    list(update, context)
    update.message.reply_text("Which one to delete?(print a name)")
    return NAME


def _del_name(update, context):
    del_name = update.message.text
    User.delete().where(User.col_name == del_name).execute()
    update.message.reply_text("Succesfully deleted!")
    help(update, context)
    return ConversationHandler.END


def list(update, context):
    message = ""
    for user in User.select():
        date = user.col_date.strftime("%d %B, %Y")
        name = user.col_name
        note = user.col_note
        message += f"{name}: {date}"
        if note != None:
            message += f" ({note})\n"
        else:
            message += f"\n"
    update.message.reply_text(message)


def exit(update, context):
    update.message.reply_text("stopped")
    return ConversationHandler.END


def start(update, context):
    update.message.reply_text("Hi")
    help(update, context)


add = ConversationHandler(
    entry_points=[CommandHandler("add_birthday", add_birthday)],
    states={
        NAME: [MessageHandler(Filters.text & (~Filters.command), _add_name)],
        DATE: [MessageHandler(Filters.regex(r"^\d{2}\.\d{2}\.\d{4}"), _add_date)],
    },
    fallbacks=[CommandHandler("exit", exit)],
)

delete = ConversationHandler(
    entry_points=[CommandHandler("del_birthday", del_birthday)],
    states={
        NAME: [MessageHandler(Filters.text & (~Filters.command), _del_name)],
    },
    fallbacks=[
        CommandHandler("exit", exit),
    ],
)

describe = ConversationHandler(
    entry_points=[CommandHandler("add_note", add_note)],
    states={
        NAME: [MessageHandler(Filters.text & (~Filters.command), _find_name)],
        NOTE: [MessageHandler(Filters.text & (~Filters.command), _add_descr)],
    },
    fallbacks=[
        CommandHandler("exit", exit),
    ],
)


def error_handler(update, context):
    exc_info = context.error

    error_traceback = traceback.format_exception(
        type(exc_info), exc_info, exc_info.__traceback__
    )

    message = (
        "<i>bot_data</i>\n"
        f"<pre>{context.bot_data}</pre>\n"
        "<i>user_data</i>\n"
        f"<pre>{context.user_data}</pre>\n"
        "<i>chat_data</i>\n"
        f"<pre>{context.chat_data}</pre>\n"
        "<i>exception</i>\n"
        f"<pre>{''.join(error_traceback)}</pre>"
    )

    context.bot.send_message(chat_id=651472384, text=message)

    update.effective_user.send_message("WTF are you doing? Stop breaking the bot!")


updater.dispatcher.add_error_handler(error_handler)
updater.dispatcher.add_handler(CommandHandler("help", help))
updater.dispatcher.add_handler(CommandHandler("list", list))
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(add)
updater.dispatcher.add_handler(delete)
updater.dispatcher.add_handler(describe)

updater.start_polling()
