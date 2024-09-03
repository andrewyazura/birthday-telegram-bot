import configparser
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_file_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')

config = configparser.ConfigParser()

if not config.read(config_file_path):
    logger.error(f"Configuration file {config_file_path} not found.")
    raise FileNotFoundError(f"Configuration file {config_file_path} not found.")

try:
    BOT_TOKEN = config["Main"]["bot_token"]
    CREATOR_ID = int(config["Main"]["creator_id"])
except KeyError as e:
    logger.error(f"Missing key in configuration file: {e}")
    raise
except ValueError as e:
    logger.error(f"Invalid value in configuration file: {e}")
    raise