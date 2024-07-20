import configparser

config = configparser.ConfigParser()
config.read("config.ini")

BOT_TOKEN = config["Main"]["bot_token"]
CREATOR_ID = int(config["Main"]["creator_id"])
