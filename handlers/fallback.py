from telegram import Update
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop current conversation

    Use as a fallback in handlers
    """
    return ConversationHandler.END
