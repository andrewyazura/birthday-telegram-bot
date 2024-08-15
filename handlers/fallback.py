from telegram import Update
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)
import logging

import core.logger


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop current conversation

    Use as a fallback function in handlers
    """
    logging.info(f"User {update.effective_user.id} stopped the conversation")
    return ConversationHandler.END
