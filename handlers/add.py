from re import findall
import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from marshmallow import ValidationError

import core.logger
from core.api_requests import post_request
from core.schema import BirthdaysSchema
from handlers.fallback import stop


ADD_NAME, ADD_DATE, ADD_NOTE = range(3)


birthdays_schema = BirthdaysSchema()


async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for the person's name."""
    logging.info(f"User {update.effective_user.id} is adding a birthday")

    context.user_data.clear()

    await update.message.reply_text("Enter the person's name:")

    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check and store name, ask for a date.

    Return `ADD_DATE` if a date is to be added, otherwise call `post_birthday()`.

    """
    name = update.message.text
    if len(name) > 255:
        await update.message.reply_text(
            "That name is too long. Please choose a shorter one:"
        )
        logging.warning(
            f"User {update.effective_user.id} entered a name that is too long: {name}"
        )
        print("returning ADD_NAME")
        return ADD_NAME

    context.user_data["name"] = name
    logging.info(f"User {update.effective_user.id} entered name: {name}")

    if context.user_data.get("day"):
        return await post_birthday(update, context)
    await update.message.reply_text(
        "Great! Enter the date (format: `DD.MM.YYYY` or `DD.MM`):"
    )
    return ADD_DATE


async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check and store date, ask for a note.

    Year is optional.
    Return `ADD_NOTE` if a note is to be added, otherwise call `post_birthday()`.

    """
    date_text = update.message.text
    logging.info(f"User {update.effective_user.id} provided date: {date_text}")

    try:
        ints_from_text = findall(r"\d+", date_text)
        day = int(ints_from_text[0])
        month = int(ints_from_text[1])
        year = int(ints_from_text[2]) if len(ints_from_text) > 2 else None

        date_json = {"day": day, "month": month, "year": year}
        birthdays_schema.valid_date(date_json)

        context.user_data["day"] = date_json["day"]
        context.user_data["month"] = date_json["month"]
        context.user_data["year"] = date_json["year"]

    except (ValueError, IndexError, ValidationError) as e:
        logging.warning(f"Validation error for date: {date_text}. Error: {e}")
        await update.message.reply_text(
            "\n".join(e.messages)
            if isinstance(e, ValidationError)
            else "Invalid date format, please try again"
        )
        return ADD_DATE

    if "note" in context.user_data and context.user_data["note"] is not None:
        return await post_birthday(update, context)

    await update.message.reply_text(
        "Would you like to add a note for this reminder? If yes, please type your note now. If not, send /skip"
    )
    return ADD_NOTE


async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle skiping adding a note, call `post_birthday()`."""
    logging.info(f"User {update.effective_user.id} skipped adding a note")
    context.user_data["note"] = None
    return await post_birthday(update, context)


async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store note, call `post_birthday()`."""
    note = update.message.text
    logging.info(f"User {update.effective_user.id} added a note: {note}")
    context.user_data["note"] = note
    return await post_birthday(update, context)


async def post_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a post request to the API with the data from `context.user_data`.

    Used as a part of `add_conv_handler`. Handles the response from the API.

    All values need to be present in `context.user_data` (at least equal to `None`).

    If the request fails due to a name conflict - return `ADD_NAME` to ask for another name.
    If the request fails due to an invalid date - return `ADD_DATE` to ask for another date.

    If success or unpredicted failure - notify and end conversation.

    """
    data = {
        "name": context.user_data["name"],
        "day": context.user_data["day"],
        "month": context.user_data["month"],
        "year": context.user_data["year"],
        "note": context.user_data["note"],
    }

    try:
        response = post_request(update.effective_user.id, data)
        if response.status_code != 422:
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error posting birthday data for user {update.effective_user.id}: {str(e)}")
        await update.message.reply_text("Failed. Please try again")
        return ConversationHandler.END

    # TODO: print response.json()["message"] to user
    if response.status_code == 422:
        error_field = response.json().get("field")
        logging.warning(f"Validation error from API for user {update.effective_user.id}: {response.json()}")

        if error_field == "name":
            context.user_data.pop("name", None)
            await update.message.reply_text("Name is already in use. Please choose another one:")
            return ADD_NAME
        elif error_field == "date":
            context.user_data.pop("day", None)
            context.user_data.pop("month", None)
            context.user_data.pop("year", None)
            await update.message.reply_text("Date is invalid. Please enter a valid date (format: `DD.MM.YYYY` or `DD.MM`):")
            return ADD_DATE
        else:
            await update.message.reply_text("Invalid data. Please try again")
            return ConversationHandler.END

    context.user_data.clear()
    logging.info(f"Birthday added successfully for user {update.effective_user.id}")
    await update.message.reply_text(
        "Birthday added successfully! /list to see all birthdays"
    )
    return ConversationHandler.END


add_conv_handler = ConversationHandler(
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
