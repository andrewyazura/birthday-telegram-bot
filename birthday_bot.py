from telegram import Update, BotCommand, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from marshmallow import ValidationError
import re
from schema import BirthdaysSchema
from api_requests import post_request
from config import BOT_TOKEN


ADD_NAME, ADD_DATE, ADD_NOTE = range(3)


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
        return await post_birthday(update, context)
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
        return await post_birthday(update, context)

    await update.message.reply_text(
        "Would you like to add a note for this reminder? If yes, please type your note now. If not, send /skip"
    )
    return ADD_NOTE


async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["skipped_note"] = True
    return await post_birthday(update, context)


async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    context.user_data["note"] = note
    return await post_birthday(update, context)


async def post_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text(
        "Birthday added successfully! /list to see all birthdays"
    )
    return ConversationHandler.END


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

# print(f"Current state: {state_name.get(state, 'UNKNOWN')}")


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
