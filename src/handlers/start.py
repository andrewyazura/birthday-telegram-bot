from telegram import Update
from telegram.ext import (
    ContextTypes,
)
import logging


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"User {update.effective_user.id} started the bot")

    await update.message.reply_text(
        "Welcome to BirthdayBot!\nYou can start by adding a birthday with /add command."
    )
