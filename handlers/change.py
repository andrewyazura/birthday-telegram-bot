import logging
from re import findall

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from marshmallow import ValidationError

from core.api_requests import put_request, get_request, get_by_id_request
from core.schema import BirthdaysSchema
from handlers.fallback import stop


CHANGE_GET_BIRTHDAY, CHANGE_NAME, CHANGE_DATE, CHANGE_NOTE = range(4)

birthdays_schema = BirthdaysSchema()


async def change_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request all birthdays, give user a keyboard to choose which birthday to change."""
    logging.info(f"User {update.effective_user.id} is changing a birthday")

    context.user_data.clear()

    try:
        response = get_request(update.effective_user.id)
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
        logging.info(
            f"Retrieved {len(data)} birthdays for user {update.effective_user.id}"
        )
    except Exception as e:
        logging.error(
            f"Failed to retrieve birthdays for user {update.effective_user.id}: {e}"
        )
        await update.message.reply_text("Failed. Please try again")
        return ConversationHandler.END

    if response.status_code == 404:
        logging.warning(f"No birthdays found for user {update.effective_user.id}")
        await update.message.reply_text("No birthdays found. /add_birthday to add one")
        return ConversationHandler.END

    data = sorted(data, key=lambda x: x["name"])

    keyboard = []
    for birthday in data:
        keyboard.append(
            [InlineKeyboardButton(birthday["name"], callback_data=birthday["id"])]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Choose whose birthday to change:", reply_markup=reply_markup
    )
    return CHANGE_GET_BIRTHDAY


async def change_get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request chosen birthday, ask for new name or to keep the same one."""
    # HACK: Not optimal to request the birthday again, fix later

    query = update.callback_query
    await query.answer()

    birthday_id = query.data
    logging.info(f"User {update.effective_user.id} selected birthday ID: {birthday_id}")

    try:
        response = get_by_id_request(update.effective_user.id, birthday_id)
        response.raise_for_status()
        birthday_json = response.json()
        logging.info(f"Retrieved birthday data for ID {birthday_id}: {birthday_json}")
    except Exception as e:
        logging.error(
            f"Failed to retrieve birthday ID {birthday_id} for user {update.effective_user.id}: {e}"
        )
        await query.edit_message_text(
            "Failed. Please try again. {traceback.format_exc()}"
        )
        return ConversationHandler.END

    context.user_data["birthday_id"] = birthday_json["id"]
    context.user_data["name"] = birthday_json["name"]
    context.user_data["day"] = birthday_json["day"]
    context.user_data["month"] = birthday_json["month"]
    context.user_data["year"] = birthday_json["year"]
    context.user_data["note"] = birthday_json["note"]

    logging.info(
        f"User {update.effective_user.id} will now edit birthday: {birthday_json['name']}"
    )

    await query.edit_message_text(
        text=f'Changing birthday of: {birthday_json["name"]}\nInput a new name or send /skip to keep the same name'
    )
    return CHANGE_NAME


async def change_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check new name, ask for new date or to keep the same one."""
    new_name = update.message.text
    logging.info(f"User {update.effective_user.id} entered new name: {new_name}")

    if len(new_name) > 255:
        logging.warning(
            f"User {update.effective_user.id} entered a name that is too long: {new_name}"
        )
        await update.message.reply_text(
            "That name is too long. Please choose a shorter one or send /skip to keep the same name:"
        )
        return CHANGE_NAME
    if new_name == context.user_data["name"]:
        logging.warning(
            f"User {update.effective_user.id} entered the same name: {new_name}"
        )
        await update.message.reply_text(
            "This name is the same. Input a new name or send /skip to keep the same name:"
        )
        return CHANGE_NAME

    context.user_data["new_name"] = new_name

    if "new_day" in context.user_data or context.user_data.get("skipped_date"):
        return await put_birthday(update, context)

    date = f"{context.user_data['day']}.{context.user_data['month']}"
    if context.user_data["year"]:
        date += f".{context.user_data['year']}"

    await update.message.reply_text(
        f"Great! Enter the date (format: `DD.MM.YYYY` or `DD.MM`) or send /skip to keep the same date.\nCurrent date: {date}"
    )
    return CHANGE_DATE


async def skip_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Not changing name, ask for new date or to keep the same one."""
    logging.info(f"User {update.effective_user.id} chose to skip changing the name")

    if "new_day" in context.user_data or context.user_data.get("skipped_date"):
        return await put_birthday(update, context)

    date = f"{context.user_data['day']}.{context.user_data['month']}"
    if context.user_data["year"]:
        date += f".{context.user_data['year']}"
    await update.message.reply_text(
        f"Enter the date (format: `DD.MM.YYYY` or `DD.MM`) or send /skip to keep the same date.\nCurrent date: {date}"
    )
    return CHANGE_DATE


async def change_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check new date, ask for new note or to keep the same one."""
    new_date_text = update.message.text

    try:
        ints_from_text = findall(r"\d+", new_date_text)
        day = int(ints_from_text[0])
        month = int(ints_from_text[1])
        year = int(ints_from_text[2]) if len(ints_from_text) > 2 else None

        date_json = {"day": day, "month": month, "year": year}
        birthdays_schema.valid_date(date_json)

        context.user_data["day"] = date_json["day"]
        context.user_data["month"] = date_json["month"]
        context.user_data["year"] = date_json["year"]

        logging.info(
            f"Validated new date for user {update.effective_user.id}: {date_json}"
        )

    except (ValueError, IndexError, ValidationError) as e:
        logging.warning(f"Validation error for date: {new_date_text}. Error: {e}")
        await update.message.reply_text(
            "\n".join(e.messages)
            if isinstance(e, ValidationError)
            else "Invalid date format, please try again:"
        )
        return CHANGE_DATE

    if "new_note" in context.user_data or context.user_data.get("skipped_note"):
        return await put_birthday(update, context)

    current_note_str = ""
    if context.user_data.get("note"):
        current_note_str = f"\nCurrent note: {context.user_data['note']}. Send /delete_note to delete it:\n"
    await update.message.reply_text(
        f"Nice. Enter a new note or send /skip to keep the same note. {current_note_str}"
    )
    return CHANGE_NOTE


async def skip_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Not changing date, ask for new note or to keep the same one."""
    logging.info(f"User {update.effective_user.id} chose to skip changing the date")

    if "new_note" in context.user_data or context.user_data.get("skipped_note"):
        return await put_birthday(update, context)

    context.user_data["skipped_date"] = True

    current_note_str = ""
    if context.user_data.get("note"):
        current_note_str = f"\nCurrent note: {context.user_data['note']}. Send /delete_note to delete it:\n"
    await update.message.reply_text(
        f"Enter a new note or send /skip to keep the same note. {current_note_str}"
    )
    return CHANGE_NOTE


async def change_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check new note, call `put_birthday()`."""
    new_note = update.message.text
    logging.info(f"User {update.effective_user.id} entered new note: {new_note}")

    if len(new_note) > 255:
        logging.warning(
            f"User {update.effective_user.id} entered a note that is too long: {new_note}"
        )
        await update.message.reply_text(
            "This note is too long. Please choose a shorter one. Send /skip to keep the same note, /delete_note to delete it:"
        )
        return CHANGE_NOTE

    if new_note == context.user_data["note"]:
        logging.warning(
            f"User {update.effective_user.id} entered the same note: {new_note}"
        )
        await update.message.reply_text(
            "This note is the same. Input a new note, /delete_note to delete it, or send /skip to keep the same note:"
        )
        return CHANGE_NOTE

    context.user_data["new_note"] = new_note
    return await put_birthday(update, context)


async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Not changing note, call `put_birthday()`."""
    logging.info(f"User {update.effective_user.id} chose to skip changing the note")

    context.user_data["skipped_note"] = True
    return await put_birthday(update, context)


async def delete_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the note to None, call `put_birthday()`."""
    logging.info(f"User {update.effective_user.id} chose to delete the note")

    context.user_data["new_note"] = None
    return await put_birthday(update, context)


async def put_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a put request to the API with the data from `context.user_data`.

    Used as a part of `change_conv_handler`. Handles the response from the API.

    All new (and old) values need to be present in `context.user_data`.
    Old value will be overwritten if new is present.

    If the request fails due to a name conflict - return `CHANGE_NAME` to ask for a name again.
    If the request fails due to an invalid date - return `CHANGE_DATE` to ask for a date again.

    If success or unpredicted failure - notify and end conversation.
    """

    if nothing_changed(context.user_data):
        logging.warning(f"User {update.effective_user.id} didn't change anything")
        await update.message.reply_text("No changes made. Don't waste my time.")
        return ConversationHandler.END

    data_json = _collect_data(context.user_data)

    try:
        response = put_request(
            update.effective_user.id, context.user_data["birthday_id"], data_json
        )
        logging.info(f"Put request response: {response.json()}")
        if response.status_code != 422:
            response.raise_for_status()
    except Exception as e:
        logging.error(
            f"Error putting birthday data for user {update.effective_user.id}: {str(e)}"
        )
        await update.message.reply_text("Failed. Please try again")
        context.user_data.clear()
        return ConversationHandler.END

    # TODO: print response.json()["message"] to user
    if response.status_code == 422:
        if response.json()["field"] == "name":
            if "new_name" in context.user_data:
                context.user_data.pop("new_name")

            await update.message.reply_text(
                "Name is already in use. Please choose another one:"
            )
            return CHANGE_NAME
        elif response.json()["field"] == "date":
            if context.user_data.get("new_day"):
                context.user_data.pop("new_day", None)
                context.user_data.pop("new_month", None)
                context.user_data.pop("new_year", None)
            elif context.user_data.get("day"):
                context.user_data.pop("day", None)
                context.user_data.pop("month", None)
                context.user_data.pop("year", None)

            await update.message.reply_text(
                "Date is invalid. Please enter a valid date (format: `DD.MM.YYYY` or `DD.MM`):"
            )
            return CHANGE_DATE
        else:
            logging.warning(
                f"Validation error from API for user {update.effective_user.id}: {response.json()}"
            )
            await update.message.reply_text("Invalid data. Please try again")
            return ConversationHandler.END

    logging.info(f"User {update.effective_user.id} successfully changed birthday data")
    context.user_data.clear()
    await update.message.reply_text(
        "Birthday changed successfully! /list to see all birthdays"
    )
    return ConversationHandler.END


def nothing_changed(user_data) -> bool:
    """Check if any new value is present in `user_data`."""
    if "new_name" in user_data or "new_day" in user_data or "new_note" in user_data:
        return False
    return True


def _collect_data(user_data) -> dict:
    """Collects data from `user_data` and returns it in a dictionary ready to be sent to the API.

    If new value is present, it will be used, otherwise the old one will be used.
    `None` values for old/new `year` and `note` are axceptable.
    """
    data = {}

    if "new_name" in user_data:
        data["name"] = user_data["new_name"]
    else:
        data["name"] = user_data["name"]

    if "new_day" in user_data:
        data["day"] = user_data["new_day"]
        data["month"] = user_data["new_month"]
        data["year"] = user_data["new_year"]
    else:
        data["day"] = user_data["day"]
        data["month"] = user_data["month"]
        data["year"] = user_data["year"]

    if "new_note" in user_data:
        data["note"] = user_data["new_note"]
    elif "note" in user_data:
        data["note"] = user_data["note"]

    return data


change_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("change_birthday", change_birthday)],
    states={
        CHANGE_GET_BIRTHDAY: [CallbackQueryHandler(change_get_birthday, r"^[1-9]\d*$")],
        CHANGE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, change_name),
            CommandHandler("skip", skip_name),
        ],
        CHANGE_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, change_date),
            CommandHandler("skip", skip_date),
        ],
        CHANGE_NOTE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, change_note),
            CommandHandler("skip", skip_note),
            CommandHandler("delete_note", delete_note),
        ],
    },
    fallbacks=[CommandHandler("stop", stop)],
)
