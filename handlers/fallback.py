from telegram import Update
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End conversation."""
    return ConversationHandler.END
