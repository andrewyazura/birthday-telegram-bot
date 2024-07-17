import requests
import configparser

from telegram import Update, BotCommand, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import date

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64
import requests
import re


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

config = configparser.ConfigParser()
config.read("config.ini")
CREATOR_ID = config["Bot"]["creator_id"]
BOT_TOKEN = config["Bot"]["bot_token"]
# print(BOT_TOKEN)

ADD_NAME, ADD_DATE, ADD_NOTE = range(3)


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
            raise ValidationError(
                "29th of February is forbidden. Choose 28.02 or 1.03:"
            )

        try:
            birthday = date(year, data["month"], data["day"])
        except ValueError:
            raise ValidationError("Invalid date, try again:")
        if date.today() < birthday:
            raise ValidationError("Future dates are forbidden, try again:")


birthdays_schema = BirthdaysSchema()

# conv_handler_ref = None


# print_name = Enter the person's name:
# too_long = That name is too long. Please choose a shorter one:
# already_taken = That name is already in use. Please choose another one:
# print_date = Great! Enter the date (format: DD.MM.YYYY or DD.MM):
# 29th = February 29th is a special case{newline1}Please choose a different date like 01.03 or 28.02 and add a note that the actual birthday is on 29.02 using the /add_note command{newline2}Sorry for the inconvenience
# invalid_date = That date is invalid. Please enter a valid date:
# added = Birthday added successfully!
async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text("Enter the person's name:")

    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if len(name) > 255:
        await update.message.reply_text(
            "That name is too long. Please choose a shorter one:"
        )
        print("returning ADD_NAME")
        return ADD_NAME

    context.user_data["name"] = name
    if context.user_data.get("day"):
        return await post_state(update, context)
    await update.message.reply_text(
        "Great! Enter the date (format: `DD.MM.YYYY` or `DD.MM`):"
    )
    return ADD_DATE


async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    ints_from_text = re.findall(r"\d+", date_text)
    day = int(ints_from_text[0])
    month = int(ints_from_text[1])
    year = int(ints_from_text[2]) if len(ints_from_text) > 2 else None

    date_json = {
        "day": day,
        "month": month,
    }
    if year != None:
        date_json["year"] = year

    try:
        birthdays_schema.valid_date(date_json)
    except ValidationError as e:
        await update.message.reply_text("\n".join(e.messages))
        return ADD_DATE

    context.user_data["day"] = date_json["day"]
    context.user_data["month"] = date_json["month"]
    if "year" in date_json:
        context.user_data["year"] = date_json["year"]

    if "note" in context.user_data or "skipped_note" in context.user_data:
        return await post_state(update, context)

    await update.message.reply_text(
        "Would you like to add a note for this reminder? If yes, please type your note now. If not, send /skip"
    )
    return ADD_NOTE


async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["skipped_note"] = True
    return await post_state(update, context)


async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    context.user_data["note"] = note
    return await post_state(update, context)


async def post_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = {
        "name": context.user_data["name"],
        "day": context.user_data["day"],
        "month": context.user_data["month"],
    }
    if context.user_data.get("year"):
        data["year"] = context.user_data["year"]
    if context.user_data.get("note") is not None:
        data["note"] = context.user_data["note"]

    response = post_request(update.effective_user.id, data)

    # handle skips
    if response.status_code == 422:
        if response.json()["field"] == "name":
            if "name" in context.user_data:
                context.user_data.pop("name")
            await update.message.reply_text(
                "Name is already in use. Please choose another one:"
            )
            return ADD_NAME
        elif response.json()["field"] == "date":
            await update.message.reply_text(
                "Date is invalid. Please enter a valid date (format: `DD.MM.YYYY` or `DD.MM`):"
            )
            context.user_data.pop("day")
            context.user_data.pop("month")
            if context.user_data.get("year"):
                context.user_data.pop("year")
            return ADD_DATE
    elif response.status_code != 201:
        await update.message.reply_text("Failed to add birthday. Please try again")
        return ADD_NAME

    context.user_data.clear()
    await update.message.reply_text(
        "Birthday added successfully! /list to see all birthdays"
    )
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
    return post_birthday_response

    # def check_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     if conv_handler_ref is None:
    #         print("Conversation handler not found.")
    #         return 1
    #     conv_dict = conv_handler_ref._conversations
    #     user_id = update.effective_user.id
    #     chat_id = update.effective_chat.id

    #     state = conv_dict.get((chat_id, user_id), ConversationHandler.END)
    #     state_name = {
    #         ADD_NAME: "ADD_NAME",
    #         ADD_DATE: "ADD_DATE",
    #         ADD_NOTE: "ADD_NOTE",
    #         ConversationHandler.END: "END",
    #     }

    print(f"Current state: {state_name.get(state, 'UNKNOWN')}")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        """
        Commands to use:
        /list - your added birthdays
        /add_birthday - adds a birthday to your list
        """
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return ConversationHandler.END


def main() -> None:

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    add = ConversationHandler(
        entry_points=[CommandHandler("add_birthday", add_birthday)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_name)],
            ADD_DATE: [MessageHandler(filters.TEXT & (~filters.COMMAND), add_date)],
            ADD_NOTE: [
                CommandHandler("skip", skip_note),
                MessageHandler(filters.TEXT & (~filters.COMMAND), add_note),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, stop),
        ],
        allow_reentry=True,
    )
    # conv_handler_ref = add
    application.add_handler(add)
    # application.add_handler(CommandHandler("check_state", check_state))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
