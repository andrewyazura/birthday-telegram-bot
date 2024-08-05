import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from core.api_requests import delete_request, get_request
from core.schema import BirthdaysSchema
from handlers.fallback import stop


DELETE_REQUEST = range(1)


birthdays_schema = BirthdaysSchema()


async def delete_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    try:
        response = get_request(update.effective_user.id)
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        # TODO: log error
        # TODO: notify admin
        await update.message.reply_text(f"{e}. Please try again")
        return ConversationHandler.END

    if response.status_code == 404:
        await update.message.reply_text("No birthdays found. /add_birthday to add one")
        return ConversationHandler.END

    keyboard = []
    for birthday in data:
        keyboard.append(
            [InlineKeyboardButton(birthday["name"], callback_data=birthday["id"])]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Choose whose birthday to delete:", reply_markup=reply_markup
    )
    return DELETE_REQUEST


async def delete_handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    birthday_id = query.data

    try:
        response = delete_request(update.effective_user.id, birthday_id)
        response.raise_for_status()
    except Exception as e:
        await query.edit_message_text(
            f"{e}. Please try again. {traceback.format_exc()}"
        )
        return ConversationHandler.END

    await query.edit_message_text(
        "Birthday deleted successfully. /list to see updated list"
    )
    return ConversationHandler.END


delete_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("delete_birthday", delete_birthday)],
    states={DELETE_REQUEST: [CallbackQueryHandler(delete_handle_response)]},
    fallbacks=[CommandHandler("stop", stop)],
    allow_reentry=True,
)
