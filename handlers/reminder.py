import traceback
import datetime

from telegram.ext import ContextTypes

from core.requests.api_requests import incoming_birthdays_request


async def reminder(context: ContextTypes.DEFAULT_TYPE):
    try:
        response = incoming_birthdays_request()
        if response.status_code == 404:
            return
        response.raise_for_status()
    except Exception as e:
        print(traceback.format_exc())
        # log error+
        # notify admin
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

        await context.bot.send_message(
            chat_id=birthday["creator"]["telegram_id"],
            text=message,
            parse_mode="Markdown",
        )
        # log if send message returns error
