# Hermes - config.py
# Author: Indrajit Ghosh
# Created On: Sep 20, 2025

import os
from pathlib import Path

class Config:
    BASE_DIR = Path(__name__).parent.absolute()
    LOG_DIR = BASE_DIR / "logs"
    LOG_FILE = LOG_DIR / 'hermes.log'

    SQLALCHEMY_DATABASE_URI = "sqlite:///hermes.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_STATIC_KEY = os.getenv("API_STATIC_KEY")
    FERNET_KEY = os.getenv("FERNET_KEY")

    # Bot Email
    BOT_EMAIL = os.getenv("BOT_EMAIL")
    BOT_PASSWORD = os.getenv("BOT_PASSWORD")
    BOT_MAIL_SERVER = os.getenv("BOT_SMTP_SERVER")
    BOT_MAIL_PORT = os.getenv("BOT_SMTP_PORT")
    MAIL_USE_TLS = True


LOG_FILE = Config.LOG_FILE

LOG_DIR = Config.LOG_DIR
LOG_DIR.mkdir(exist_ok=True) # create logs directory if not exists