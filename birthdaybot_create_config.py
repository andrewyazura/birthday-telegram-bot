# 5936456116:AAFSjRwO1TqBjwbodOxREQW3ZsWGXWvDFzA - @remember_about_birthdays_bot;
# 5749842477:AAE72SsmVUNh0hFhy5KwTgnICe0m_zEqTyU - @oleh1bot
# orehzzz's id - 651472384

import configparser

config = configparser.ConfigParser()
config["Bot"] = {
    "creator_id": "651472384",
    "bot_token": "5749842477:AAE72SsmVUNh0hFhy5KwTgnICe0m_zEqTyU",
}
config["Database"] = {"name": "birthdays", "user": "postgres", "password": "l9999l"}

with open("birthdaybot_config_test.ini", "w") as configfile:
    config.write(configfile)
