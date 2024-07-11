import requests
import configparser

from telegram import Update, BotCommand, Bot
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

config = configparser.ConfigParser()
config.read("config.ini")
CREATOR_ID = config["Bot"]["creator_id"]
BOT_TOKEN = config["Bot"]["bot_token"]
# print(BOT_TOKEN)

application = ApplicationBuilder().token(BOT_TOKEN).build()


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
# awaitbot.set_my_commands(commands)


ADD_2, ADD_3, ADD_4, DEL_2, CHANGE_2, CHANGE_3, LANG_2 = range(7)


from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64
import requests


class UserSessionManager:
    def __init__(self):
        self.sessions = {}

    def get_session(self, username):
        if username not in self.sessions:
            self.sessions[username] = requests.Session()
        return self.sessions[username]


# Example usage
session_manager = UserSessionManager()
# user1_session = session_manager.get_session("user1")
# response = user1_session.get("https://example.com")

from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import date


class BirthdaysSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(max=255))
    day = fields.Integer(required=True)
    month = fields.Integer(required=True)
    year = fields.Integer()
    note = fields.String()

    @validates_schema
    def valid_date(self, data, **kwargs):
        try:
            year = data["year"]
        except KeyError:
            year = date.today().year - 1
        if (data["month"] == 2) and (data["day"] == 29):
            raise ValidationError("29th of February is forbidden. Choose 28.02 or 1.03")
        try:
            birthday = date(year, data["month"], data["day"])
        except ValueError:
            raise ValidationError("Non-existent date")
        if date.today() < birthday:
            raise ValidationError("Future dates are forbidden")
        


birthdays_schema = BirthdaysSchema()


# print_name = Enter the person's name:
# too_long = That name is too long. Please choose a shorter one:
# already_taken = That name is already in use. Please choose another one:
# print_date = Great! Enter the date (format: DD.MM.YYYY or DD.MM):
# 29th = February 29th is a special case{newline1}Please choose a different date like 01.03 or 28.02 and add a note that the actual birthday is on 29.02 using the /add_note command{newline2}Sorry for the inconvenience
# invalid_date = That date is invalid. Please enter a valid date:
# added = Birthday added successfully!
async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # await update.message.reply_text("Enter the person's name:")
    data = {
        "name": "fewfew",
        "day": 28,
        "month": 2,
        "year": 2020,
        "note": "test note",
    }
    post_request(update.effective_user.id, data)
    return ConversationHandler.END
    # return ADD_2


async def _add_birthday_2(update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text

    #check if name is too long
    #check if name is already taken

    context.user_data["current_name"] = name
    await update.message.reply_text(
        "Great! Enter the date (format: DD.MM.YYYY or DD.MM):"
    )
    return ADD_3


async def _add_birthday_3(update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text

    #check if date is valid
    #check if date is 29th of February

    context.user_data["current_date"] = date
    await update.message.reply_text(
        "Would you like to add a note for this reminder? If yes, please type your note now. If not, press 'skip'"
    )
    return ADD_4


async def _add_birthday_4(update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text

    #skip button
    #check if note is too long

    context.user_data["current_note"] = note
    day = int(
        context.user_data["current_date"][:2]
    )  # maybe change for regex depending on points
    month = int(context.user_data["current_date"][3:5])
    data = {
        "name": context.user_data["current_name"],
        "day": day,
        "month": month,
    }
    if len(context.user_data["current_date"]) == 10:
        year = int(context.user_data["current_date"][-4:])
        data["year"] = year
    if note:
        data["note"] = note

    post_request(update.effective_user.id, data)

    #if error: return to the corresponding step


    await update.message.reply_text("Birthday added successfully!")
    return ConversationHandler.END


def post_request(id, data_json):
    user_session = session_manager.get_session(id)
    public_key_response = user_session.get("http://127.0.0.1:8080/public-key")

    if public_key_response.status_code != 200:
        print(f"Failed to get api key. {public_key_response.status_code}")
        exit(1)
    public_key_json = public_key_response.json()
    public_key = serialization.load_pem_public_key(
        public_key_json["public_key"].encode("utf-8")
    )
    bot_id = BOT_TOKEN.encode("utf-8")

    encrypted_data = public_key.encrypt(
        bot_id,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_data_base64 = base64.b64encode(encrypted_data).decode("utf-8")

    login_response = user_session.get(
        "http://127.0.0.1:8080/login",
        params={"encrypted_bot_id": encrypted_data_base64, "id": 651472384},
    )
    if login_response.status_code != 200:
        print(f"Failed to login to api. {login_response.status_code}")
        exit(1)

    csrf_access_token = user_session.cookies["csrf_access_token"]
    print(user_session.cookies)

    headers = {"X-CSRF-TOKEN": csrf_access_token}

    # post birthday
    post_birthday_response = user_session.post(
        "http://127.0.0.1:8080/birthdays", json=data_json, headers=headers
    )
    if post_birthday_response.status_code != 201:
        print(f"Failed to add birthday. {post_birthday_response.json()}")
    else:
        print(post_birthday_response.json())


# async def _add_birthday_3(update, context: ContextTypes.DEFAULT_TYPE):
#     date = update.message.text
#     try:
#         if not date[2] == ".":
#             raise ValueError
#         day, month = int(date[:2]), int(date[3:5])
#         if day == 29 and month == 2:
#             await update.message.reply_text(
#                 "This is an unusual date\nI will ask you to choose a different date like 01.03 or 28.02 and then add a note that it is actually on 29.02 by using /add_note command\nSorry for the inconvenience"
#             )
#             return ADD_3
#         year = None
#         if len(date) == 10:
#             if not date[5] == ".":
#                 raise ValueError
#             year = int(date[-4:])
#             if datetime.date.today() < datetime.date(year, month, day):
#                 raise ValueError
#         datetime.date(datetime.date.today().year, month, day)
#     except Exception:
#         await update.message.reply_text("This is an invalid date. Choose another one:")
#         return ADD_3
#     Birthdays.create(
#         col_name=context.user_data["current_name"],
#         col_day=day,
#         col_month=month,
#         col_year=year,
#         col_creator=User.get(User.col_creator == update.effective_user.id),
#     )

#     # login
#     user_session = session_manager.get_session(update.effective_user.id)
#     public_key_response = user_session.get("http://127.0.0.1:8080/public-key")

#     if public_key_response.status_code != 200:
#         print(f"Failed to get incoming birthdays. {public_key_response.status_code}")
#         exit(1)
#     data = public_key_response.json()
#     public_key = serialization.load_pem_public_key(data["public_key"].encode("utf-8"))
#     data = BOT_TOKEN.encode("utf-8")

#     encrypted_data = public_key.encrypt(
#         data,
#         padding.OAEP(
#             mgf=padding.MGF1(algorithm=hashes.SHA256()),
#             algorithm=hashes.SHA256(),
#             label=None,
#         ),
#     )
#     encrypted_data_base64 = base64.b64encode(encrypted_data).decode("utf-8")

#     login_response = user_session.get(
#         "http://127.0.0.1:8080/login",
#         params={"encrypted_bot_id": encrypted_data_base64, "id": 651472384},
#     )
#     if login_response.status_code != 200:
#         print(f"Failed to get incoming birthdays. {login_response.status_code}")
#         exit(1)

#     # post birthday
#     data = {
#         "name": context.user_data["current_name"],
#         "day": day,
#         "month": month,
#         "year": year,
#         "note": note,
#     }
#     post_birthday_response = user_session.post(
#         "http://127.0.0.1:8080/birthdays", json=data
#     )
#     if post_birthday_response.status_code != 200:
#         print(f"Failed to get incoming birthdays. {post_birthday_response.status_code}")
#         exit(1)
#     else:
#         print(post_birthday_response.json())

#     await update.message.reply_text("Successfully added!")
#     return ConversationHandler.END


async def help(update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        """
        Commands to use:
        /list - your added birthdays
        /add_birthday - adds a birthday to your list
        """
    )


async def stop(update, context: ContextTypes.DEFAULT_TYPE):
    return ConversationHandler.END


add = ConversationHandler(
    entry_points=[CommandHandler("add_birthday", add_birthday)],
    states={
        ADD_2: [MessageHandler(filters.TEXT & (~filters.COMMAND), _add_birthday_2)],
        ADD_3: [MessageHandler(filters.TEXT & (~filters.COMMAND), _add_birthday_3)],
        ADD_4: [
            MessageHandler(filters.TEXT, _add_birthday_4)
        ],  # later add for skip button
    },
    fallbacks=[
        MessageHandler(filters.COMMAND, stop),
    ],
)
application.add_handler(add, 2)


application.run_polling(allowed_updates=Update.ALL_TYPES)
