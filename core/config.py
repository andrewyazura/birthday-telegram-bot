import configparser
import os
import logging


config_file_path = os.path.join(os.path.dirname(__file__), "..", "config.ini")

config = configparser.ConfigParser()

if not config.read(config_file_path):
    logging.error(f"Configuration file {config_file_path} not found.")
    raise FileNotFoundError(f"Configuration file {config_file_path} not found.")

try:
    BOT_TOKEN = config["Main"]["bot_token"]
    CREATOR_ID = int(config["Main"]["creator_id"])
    logging.info("Config loaded successfully.")
except KeyError as e:
    logging.error(f"Missing key in configuration file: {e}")
    raise
except ValueError as e:
    logging.error(f"Invalid value in configuration file: {e}")
    raise
