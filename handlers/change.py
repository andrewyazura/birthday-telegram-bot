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

import traceback


CHANGE_GET_BIRTHDAY, CHANGE_NAME, CHANGE_DATE, CHANGE_NOTE = range(4)


birthdays_schema = BirthdaysSchema()


async def change_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    try:
        response = get_request(update.effective_user.id)
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        await update.message.reply_text(f"{e}. Please try again")
        return ConversationHandler.END

    if response.status_code == 404:
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
    # bad but okay - request selected birthday, add to context data
    query = update.callback_query
    await query.answer()

    birthday_id = query.data

    try:
        response = get_by_id_request(update.effective_user.id, birthday_id)
        response.raise_for_status()
        birthday_json = response.json()
    except Exception as e:
        # TODO: send to admin
        await query.edit_message_text(
            f"{e}. Please try again. {traceback.format_exc()}"
        )
        return ConversationHandler.END

    # add data to context
    context.user_data["birthday_id"] = birthday_json["id"]
    context.user_data["name"] = birthday_json["name"]
    context.user_data["day"] = birthday_json["day"]
    context.user_data["month"] = birthday_json["month"]
    context.user_data["year"] = birthday_json["year"]
    context.user_data["note"] = birthday_json["note"]

    await query.edit_message_text(
        text=f'Changing birthday of: {birthday_json["name"]}\nInput a new name or send /skip to keep the same name'
    )
    return CHANGE_NAME


async def change_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get new name
    new_name = update.message.text

    if len(new_name) > 255:
        await update.message.reply_text(
            "That name is too long. Please choose a shorter one or send /skip to keep the same name:"
        )
        print("returning ADD_NAME")
        return CHANGE_NAME
    if new_name == context.user_data["name"]:
        await update.message.reply_text(
            "This name is the same. Input a new name or send /skip to keep the same name:"
        )
        return CHANGE_NAME

    context.user_data["new_name"] = new_name

    if "new_day" in context.user_data:
        return await put_birthday(update, context)

    date = f"{context.user_data['day']}.{context.user_data['month']}"
    if context.user_data["year"]:
        date += f".{context.user_data['year']}"
    # ask user for new date or skip
    await update.message.reply_text(
        f"Great! Enter the date (format: `DD.MM.YYYY` or `DD.MM`) or send /skip to keep the same date.\nCurrent date: {date}"
    )
    return CHANGE_DATE


async def skip_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "new_day" in context.user_data:  # for some unexpected /skip
        return await put_birthday(update, context)

    date = f"{context.user_data['day']}.{context.user_data['month']}"
    if context.user_data["year"]:
        date += f".{context.user_data['year']}"
    await update.message.reply_text(
        f"Enter the date (format: `DD.MM.YYYY` or `DD.MM`) or send /skip to keep the same date.\nCurrent date: {date}"
    )
    return CHANGE_DATE


async def change_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # check new date
    new_date_text = update.message.text
    ints_from_text = findall(r"\d+", new_date_text)
    day = int(ints_from_text[0])
    month = int(ints_from_text[1])
    year = int(ints_from_text[2]) if len(ints_from_text) > 2 else None
    date_json = {
        "day": day,
        "month": month,
        "year": year,
    }

    try:
        birthdays_schema.valid_date(date_json)
    except ValidationError as e:
        error_messages = "\n".join(e.messages)
        await update.message.reply_text(
            f"{error_messages}. Try again or send /skip to keep the same date:"
        )
        return CHANGE_DATE

    context.user_data["new_day"] = date_json["day"]
    context.user_data["new_month"] = date_json["month"]
    context.user_data["new_year"] = date_json["year"]

    if "new_note" in context.user_data or context.user_data.get("skipped_note") == True:
        return await put_birthday(update, context)

    current_note_str = ""
    if "note" in context.user_data and context.user_data["note"] is not None:
        current_note_str = f"\nCurrent note: {context.user_data['note']}. Send /delete_note to delete it:\n"
    await update.message.reply_text(
        f"Nice. Enter a new note or send /skip to keep the same note. {current_note_str}"
    )
    return CHANGE_NOTE


async def skip_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        "new_note" in context.user_data or context.user_data.get("skipped_note") == True
    ):  # for some unexpected /skip
        return await put_birthday(update, context)

    current_note_str = ""
    if "note" in context.user_data and context.user_data["note"] is not None:
        current_note_str = f"\nCurrent note: {context.user_data['note']}. Send /delete_note to delete it:\n"
    await update.message.reply_text(
        f"Enter a new note or send /skip to keep the same note. {current_note_str}"
    )
    return CHANGE_NOTE


async def change_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_note = update.message.text

    if len(new_note) > 255:
        await update.message.reply_text(
            "This note is too long. Please choose a shorter one. Send /skip to keep the same note, /delete_note to delete it:"
        )
        return CHANGE_NOTE

    if new_note == context.user_data["note"]:
        await update.message.reply_text(
            "This note is the same. Enter a new note. Send /skip to keep the same note, /delete_note to delete it::"
        )
        return CHANGE_NOTE

    context.user_data["new_note"] = new_note

    return await put_birthday(update, context)


async def delete_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_note"] = None
    return await put_birthday(update, context)


async def skipped_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["skipped_note"] = True
    return await put_birthday(update, context)


async def put_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # collect all data
    user_id = update.effective_user.id
    data_json = _collect_data(context.user_data)

    # hande response
    try:
        response = put_request(user_id, context.user_data["birthday_id"], data_json)
        if response.status_code != 422:
            response.raise_for_status()
    except Exception as e:
        await update.message.reply_text(f"{e}. Please try again")
        context.user_data.clear()
        return ConversationHandler.END

    if response.status_code == 422:
        if response.json()["field"] == "name":
            if "new_name" in context.user_data:
                context.user_data.pop("name")

            await update.message.reply_text(
                "Name is already in use. Please choose another one:"
            )
            return CHANGE_NAME
        elif response.json()["field"] == "date":
            if context.user_data.get("new_day"):
                context.user_data.pop("new_day")
                context.user_data.pop("new_month")
                context.user_data.pop("new_year")
            elif context.user_data.get("day"):
                context.user_data.pop("day")
                context.user_data.pop("month")
                context.user_data.pop("year")

            await update.message.reply_text(
                "Date is invalid. Please enter a valid date (format: `DD.MM.YYYY` or `DD.MM`):"
            )
            return CHANGE_DATE
        else:
            await update.message.reply_text("Invalid data. Please try again")
            return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text(
        "Birthday changed successfully! /list to see all birthdays"
    )
    return ConversationHandler.END


def _collect_data(user_data) -> dict:
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
            CommandHandler("skip", skipped_note),
            CommandHandler("delete_note", delete_note),
        ],
    },
    fallbacks=[CommandHandler("stop", stop)],
    allow_reentry=True,
)

# TODO: handle if nothing changed
