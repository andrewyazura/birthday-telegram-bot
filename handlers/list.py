from calendar import month_name
from datetime import datetime
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from core.api_requests import get_request
import core.logger


async def list_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a list of birthdays to the user"""
    context.user_data.clear()
    logging.info(f"Sending a list of birthdays to user {update.effective_user.id}")

    try:
        response = get_request(update.effective_user.id)
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
        else:
            await update.message.reply_text(
                "No birthdays found. /add_birthday to add one"
            )
            return
    except Exception as e:
        logging.error(
            f"Failed to retrieve birthdays for user {update.effective_user.id}: {e}"
        )
        await update.message.reply_text("Failed. Please try again")
        return

    data = sorted(data, key=lambda x: (x["month"], x["day"]))

    list_of_birthdays = "_Your list:_\n"
    today = datetime.now()
    today_str = f"{today.day} {month_name[today.month]}"
    border = "============================\n"

    inserted_today_panel = False

    for birthday in data:
        day = birthday["day"]
        month = month_name[birthday["month"]]
        year = birthday["year"]
        date = f"{day} {month}, {year}" if year is not None else f"{day} {month}"

        note = f' ({birthday["note"]})' if birthday["note"] is not None else ""

        # Check if the birthday is today
        if birthday["day"] == today.day and birthday["month"] == today.month:
            list_of_birthdays += (
                f"{border} _Today:_ {date} --- *{birthday['name']}*{note}\n{border}"
            )
            inserted_today_panel = True
        # Add today's panel if it's not inserted yet and the birthday is in the future
        elif not inserted_today_panel and (
            birthday["month"] > today.month
            or (birthday["month"] == today.month and birthday["day"] >= today.day)
        ):
            list_of_birthdays += f"{border}• {today_str} --- today\n{border}"
            inserted_today_panel = True
        # Add the birthday to the list
        else:
            list_of_birthdays += f"• {date} --- *{birthday['name']}*{note}\n"

    # If today's panel was not inserted, add it at the end
    if not inserted_today_panel:
        list_of_birthdays += f"{border}• {today_str} --- today\n{border}"

    logging.info(f"Sent list of birthdays to user {update.effective_user.id}")
    await update.message.reply_text(list_of_birthdays, parse_mode="Markdown")


# TODO: add this simple markdown everywhere (not v2, you'll have to put / everywhere)`)
