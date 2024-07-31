import re

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from marshmallow import ValidationError

from core.api_requests import put_request, get_request
from core.schema import BirthdaysSchema
from handlers.fallback import stop


CHANGE_GET_BIRTHDAY, CHANGE_NAME, CHANGE_DATE, CHANGE_NOTE = range(4)


birthdays_schema = BirthdaysSchema()


async def change_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # request all the birthdays
    # handle response
    # print as a inline keyboard
    return CHANGE_GET_BIRTHDAY


async def change_get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get selected birthday, maybe add to context data
    # ask to skip or input new name
    return CHANGE_NAME


async def change_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get new name
    # ask user for new date or skip
    return CHANGE_DATE


async def skip_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # name sould remain the same!!!
    # ask user for new date or skip
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
        CHANGE_GET_BIRTHDAY: [
            MessageHandler(filters.Text & ~filters.Command(), change_get_birthday)
        ],
        CHANGE_NAME: [
            MessageHandler(filters.Text & ~filters.Command(), change_name),
            CommandHandler("skip", skip_name),
        ],
        CHANGE_DATE: [
            MessageHandler(filters.Text & ~filters.Command(), change_date),
            CommandHandler("skip", skip_date),
        ],
        CHANGE_NOTE: [
            MessageHandler(filters.Text & ~filters.Command(), change_note),
            CommandHandler("skip", skip_note),
        ],
    },
    fallbacks=[CommandHandler("stop", stop)],
)
