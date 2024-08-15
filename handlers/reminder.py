import traceback
import datetime
import logging

from telegram.ext import ContextTypes

from core.api_requests import incoming_birthdays_request
import core.logger


async def reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send reminders about incoming birthdays

    A callback function for the `job_queue`.
    Request the API for incoming birthdays and send a message to the user if
      they are today, tomorrow or in a week.
    """
    logging.info("Sending reminders about incoming birthdays")

    try:
        response = incoming_birthdays_request()
        if response.status_code == 404:
            return
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to retrieve incoming birthdays: {e}")
        # TODO: notify admin
        return

    data = response.json()

    for birthday in data:
        name = birthday["name"]
        note = birthday["note"]
        year = birthday["year"]

        if birthday["incoming_in_days"] == 0:
            message = "*Today*"
        elif birthday["incoming_in_days"] == 1:
            message = "Tomorrow"
        elif birthday["incoming_in_days"] == 7:
            message = "Next week"

        message += f" is *{name}*'s birthday"

        if year:
            age = datetime.date.today().year - birthday["year"]
            message += f" - turning {age}"

        if birthday["incoming_in_days"] == 0:
            message += "!"
        else:
            message += "."

        if note:
            message += f"\n(your note: {note})"

        if birthday["incoming_in_days"] == 0:
            message += "\nSend them best wishes! :)"

        try:
            await context.bot.send_message(
                chat_id=birthday["creator"]["telegram_id"],
                text=message,
                parse_mode="Markdown",
            )
            logging.info(
                f"Sent message to user {birthday['creator']['telegram_id']}. Data: {birthday}"
            )
        except Exception as e:
            logging.error(
                f"Failed to send message: {e}. User: {birthday['creator']['telegram_id']}, birthday id: {birthday['id']}"
            )
            # TODO: notify admin
