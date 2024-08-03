import re

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
        # handle bad response
        # print(response.json())
        data = response.json()
    except Exception as e:
        await update.message.reply_text(f"{e}. Please try again")
        return ConversationHandler.END

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
        # handle bad response
        print(response.json())
        birthday_json = response.json()
    except Exception as e:
        await update.message.reply_text(
            f"{e}. Please try again. {traceback.format_exc()}"
        )
        return ConversationHandler.END

    # add data to context
    context.user_data["birthday_id"] = birthday_id
    context.user_data["name"] = birthday_json["name"]
    context.user_data["day"] = birthday_json["day"]
    context.user_data["month"] = birthday_json["month"]
    if "year" in birthday_json:
        context.user_data["year"] = birthday_json["year"]
    if "note" in birthday_json:
        context.user_data["note"] = birthday_json["note"]

    await query.edit_message_text(
        text=f'Changing birthday: {birthday_json["name"]}\n\n Input a new name or send /skip to keep the same name'
    )  # later print date and note if exist
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

    await update.message.reply_text(
        "Great! Enter the date (format: `DD.MM.YYYY` or `DD.MM`) or send /skip to keep the same date:"
    )
    # ask user for new date or skip
    return CHANGE_DATE


async def skip_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter the date (format: `DD.MM.YYYY` or `DD.MM`) or send /skip to keep the same date:"
    )
    return CHANGE_DATE


async def change_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # check new date
    # ask user for a note or skip
    return CHANGE_NOTE


async def skip_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # date sould remain the same!!!
    # ask user for a note or skip
    return CHANGE_NOTE


async def change_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # check new date
    return await put_birthday(update, context)


async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # note sould remain the same!!!
    # put_birthday
    return await put_birthday(update, context)


async def put_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # collect all data from context

    # put_request(user_id, data_json)

    # hande response

    return ConversationHandler.END


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
        ],
    },
    fallbacks=[CommandHandler("stop", stop)],
)
