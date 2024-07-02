import logging
import datetime
import traceback
import pytz
import configparser

from telegram import Bot, BotCommand
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
    filters
) 
import requests

logging.basicConfig(
    filename="birthdaybot_log.txt",
    level=logging.DEBUG,
    format=" %(asctime)s - %(levelname)s - %(message)s",
)

config = configparser.ConfigParser()
config.read("config.ini")
CREATOR_ID = config["Bot"]["creator_id"]
BOT_TOKEN = config["Bot"]["bot_token"]

text_config = configparser.ConfigParser()
text_config.read(r"conf_en.ini")

application = Application.builder().token(BOT_TOKEN).build()

# commands = [
#     BotCommand("list", "your added birthdays"),
#     BotCommand("add_birthday", "adds a birthday to your list"),
#     BotCommand("delete_birthday", "deletes a birthday from your list"),
#     BotCommand("add_note", "add some info about someone"),
#     BotCommand("help", "general info"),
#     BotCommand("language", "change Bot's language"),
#     BotCommand("stop", "to stop"),
# ]
# bot = Bot(BOT_TOKEN)
# bot.set_my_commands(commands)


ADD_2, ADD_3, DEL_2, CHANGE_2, CHANGE_3, LANG_2 = range(6)


async def help(update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"""
    {text(update, "Help", "head")}:
    /list - {text(update, "Help", "list")}
    /add_birthday - {text(update, "Help", "add_birthday")} 
    /delete_birthday - {text(update, "Help", "delete_birthday")}
    /add_note - {text(update, "Help", "add_note")}
    /langauge - {text(update, "Help", "language")}

    /help - {text(update, "Help", "help")}
    /stop - {text(update, "Help", "stop")}
    """
    )


async def reminder(context: ContextTypes.DEFAULT_TYPE):
    # await context.bot.send_message(chat_id=CREATOR_ID, text="One message every minute")
    update = None
    response = requests.get("http://127.0.0.1/birthdays/incoming")
    print(response)
    # when_remind_dict = {
    #     datetime.date.today() + datetime.timedelta(days=7): "week",
    #     datetime.date.today() + datetime.timedelta(days=1): "tomorrow",
    #     datetime.date.today(): "today",
    # }
    # for when_remind in when_remind_dict:
    #     for birthday in Birthdays.select().where(
    #         (Birthdays.col_day == when_remind.day)
    #         & (Birthdays.col_month == when_remind.month)
    #     ):
    #         lang = User.get(User.id == birthday.col_creator).col_language
    #         name = birthday.col_name
    #         note = birthday.col_note
    #         message = text(update, "Reminder", "message_start", lang=lang).format(
    #             name=name,
    #             when=text(update, "Reminder", when_remind_dict[when_remind], lang=lang),
    #         )
    #         if birthday.col_year:
    #             age = when_remind.year - birthday.col_year
    #             message += text(update, "Reminder", "message_age", lang=lang).format(
    #                 age=age
    #             )
    #         if note:
    #             message += "\n" + text(
    #                 update, "Reminder", "message_note", lang=lang
    #             ).format(note=note)
    #         message += "\n" + text(update, "Reminder", "message_end", lang=lang)
    #         await context.bot.send_message(
    #             chat_id=User.get(User.id == birthday.col_creator).col_creator,
    #             text=message,
    #         )


def text(update, section, key, lang=None):
    lang = "en"
    text_config.read(f"conf_{lang}.ini")
    return text_config[section][key]


async def language(update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="en"),
            InlineKeyboardButton("Українська", callback_data="ua"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text(update, "Language", "choose"), reply_markup=reply_markup
    )
    return LANG_2


async def _language_2(update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.callback_query.data
    User.update(col_language=answer).where(
        User.col_creator == update.effective_user.id
    ).execute()
    text_config.read(f"conf_{answer}.ini")
    await update.callback_query.edit_message_text(
        text=text(update, "Language", "changed")
    )
    help(update, context)
    return ConversationHandler.END


async def add_birthday(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(text(update, "AddBirthday", "print_name"))
    return ADD_NAME


async def _add_birthday_2(update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    user = User.select().where(User.col_creator == update.effective_user.id).first()
    if len(name) > 255:
        await update.message.reply_text(text(update, "AddBirthday", "too_long"))
        return ADD_NAME
    if user.birthdays.select().where(Birthdays.col_name == name).first():
        await update.message.reply_text(text(update, "AddBirthday", "already_taken"))
        return ADD_NAME
    context.user_data["current_name"] = name
    await update.message.reply_text(text(update, "AddBirthday", "print_date"))
    return ADD_DATE


async def _add_birthday_3(update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text
    try:
        if not date[2] == ".":
            raise ValueError
        day, month = int(date[:2]), int(date[3:5])
        if day == 29 and month == 2:
            await update.message.reply_text(
                text(update, "AddBirthday", "29th").format(newline1="\n", newline2="\n")
            )
            return ADD_DATE
        year = None
        if len(date) == 10:
            if not date[5] == ".":
                raise ValueError
            year = int(date[-4:])
            if datetime.date.today() < datetime.date(year, month, day):
                raise ValueError
        datetime.date(datetime.date.today().year, month, day)
    except Exception:
        await update.message.reply_text(text(update, "AddBirthday", "invalid_date"))
        return ADD_DATE
    Birthdays.create(
        col_name=context.user_data["current_name"],
        col_day=day,
        col_month=month,
        col_year=year,
        col_creator=User.get(User.col_creator == update.effective_user.id),
    )
    await update.message.reply_text(text(update, "AddBirthday", "added"))
    help(update, context)
    return ConversationHandler.END


async def add_note(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(text(update, "AddNote", "print_name"))
    list(update, context)
    return DESC_NAME


async def _add_note_2(update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    user = User.select().where(User.col_creator == update.effective_user.id).first()
    if not user.birthdays.select().where(Birthdays.col_name == name):
        await update.message.reply_text(text(update, "AddNote", "invalid_name"))
        return DESC_NAME
    context.user_data["current_name"] = name
    await update.message.reply_text(
        text(update, "AddNote", "print_desc").format(newline="\n")
    )
    return ADD_NOTE


async def _add_note_3(update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    user = User.select().where(User.col_creator == update.effective_user.id).first()
    Birthdays.update(col_note=note).where(
        (Birthdays.col_name == context.user_data["current_name"])
        & (Birthdays.col_creator == user.id)
    ).execute()
    await update.message.reply_text(text(update, "AddNote", "added"))
    help(update, context)
    return ConversationHandler.END


async def delete_birthday(update, context: ContextTypes.DEFAULT_TYPE):
    list(update, context)
    await update.message.reply_text(text(update, "DeleteBirthday", "print_name"))
    return DEL_NAME


async def _delete_birthday_2(update, context: ContextTypes.DEFAULT_TYPE):
    del_name = update.message.text
    user = User.select().where(User.col_creator == update.effective_user.id).first()
    query = Birthdays.delete().where(
        (Birthdays.col_creator == user) & (Birthdays.col_name == del_name)
    )
    if not await query.execute():
        await update.message.reply_text(text(update, "DeleteBirthday", "invalid_name"))
        return DEL_NAME
    await update.message.reply_text(text(update, "DeleteBirthday", "deleted"))
    help(update, context)
    return ConversationHandler.END


async def list(update, context: ContextTypes.DEFAULT_TYPE):
    message = text(update, "List", "head") + "\n"
    border = "=" * 30
    today = datetime.date.today()
    today_added = 0

    # user = (
    #     User.select()
    #     .where(User.col_creator == update.effective_user.id)
    #     .first()
    #     .birthdays
    # )

    # for birthday in user.select().order_by(Birthdays.col_month, Birthdays.col_day):
    #     name, note = birthday.col_name, birthday.col_note
    #     day, month, year = (
    #         str(birthday.col_day),
    #         text(update, "Month", str(birthday.col_month)),
    #         str(birthday.col_year),
    #     )

    #     if datetime.date(today.year, birthday.col_month, int(day)) == today:
    #         today_birthday = text(update, "List", "today_birthday").format(name=name)
    #         message += f"{border}\n{day} {month} --- {today_birthday}\n{border}\n"
    #         today_added = 1
    #         continue
    #     elif (
    #         datetime.date(today.year, birthday.col_month, int(day)) > today
    #         and not today_added
    #     ):
    #         word_today = text(update, "List", "today")
    #         today_month = text(update, "Month", str(today.month))
    #         message += (
    #             f"{border}\n{today.day} {today_month} --- {word_today}\n{border}\n"
    #         )
    #         today_added = 1
    #     space = "-"
    #     if len(name) < 9:
    #         space = "-" * (10 - len(name))
    #     message += f"{day} {month}"
    #     if birthday.col_year:
    #         message += f", {year}"
    #     message += f"  {space}  {name}"
    #     if note:
    #         message += f" ({note})\n"
    #     else:
    #         message += f"\n"

    # if message == text(update, "List", "head"):
    #     await update.message.reply_text(
    #         text(update, "List", "empty").format(newline="\n")
    #     )
    # else:
    #     if today_added == 0:
    #         today_month = text(update, "Month", str(today.month))
    #         word_today = text(update, "List", "today")
    #         message += (
    #             f"{border}\n{today.day} {today_month} --- {word_today}\n{border}\n"
    #         )
    #     await update.message.reply_text(message)


async def stop(update, context: ContextTypes.DEFAULT_TYPE):
    return ConversationHandler.END


async def start(update, context: ContextTypes.DEFAULT_TYPE):
    if not User.select().where(User.col_creator == update.effective_user.id):
        User.create(col_creator=update.effective_user.id)
    await update.message.reply_text(text(update, "Misc", "start"))
    help(update, context)


add = ConversationHandler(
    entry_points=[CommandHandler("add_birthday", add_birthday)],
    states={
        ADD_2: [MessageHandler(filters.TEXT & (~filters.COMMAND), _add_birthday_2)],
        ADD_3: [MessageHandler(filters.TEXT & (~filters.COMMAND), _add_birthday_3)],
    },
    fallbacks=[
        MessageHandler(filters.COMMAND, stop),
    ],
)

delete = ConversationHandler(
    entry_points=[CommandHandler("delete_birthday", delete_birthday)],
    states={
        DEL_2: [
            MessageHandler(filters.TEXT & (~filters.COMMAND), _delete_birthday_2)
        ],
    },
    fallbacks=[
        MessageHandler(filters.COMMAND, stop),
    ],
)

describe = ConversationHandler(
    entry_points=[CommandHandler("add_note", add_note)],
    states={
        CHANGE_2: [MessageHandler(filters.TEXT & (~filters.COMMAND), _add_note_2)],
        CHANGE_3: [MessageHandler(filters.TEXT & (~filters.COMMAND), _add_note_3)],
    },
    fallbacks=[
        MessageHandler(filters.COMMAND, stop),
    ],
)


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
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

    await context.bot.send_message(chat_id=CREATOR_ID, text=message, parse_mode="HTML")
    await update.effective_user.send_message(text(update, "Misc", "error"))


application.add_error_handler(error_handler)
application.add_handler(CommandHandler("help", help), 0)
application.add_handler(CommandHandler("list", list), 0)
application.add_handler(CommandHandler("start", start, 0))
application.add_handler(CommandHandler("stop", stop), 0)
application.add_handler(CommandHandler("language", language), 1)
application.add_handler(
    CallbackQueryHandler(_language_2, pattern="ua|en"),
    0,
)
application.add_handler(add, 2)
application.add_handler(delete, 3)
application.add_handler(describe, 4)
# application.add_handler(CommandHandler('start', start_callback))


job_queue = application.job_queue
job_queue.run_daily(
    callback=reminder,
    time=datetime.time(hour=9, minute=0, tzinfo=pytz.timezone("Europe/Kyiv")),
)


application.run_polling(allowed_updates=Update.ALL_TYPES)
