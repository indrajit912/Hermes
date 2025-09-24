# Hermes - config.py
# Author: Indrajit Ghosh
# Created On: Sep 20, 2025

import os
from os.path import join, dirname
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

class Config:
    BASE_DIR = Path(__name__).parent.absolute()
    LOG_DIR = BASE_DIR / "logs"
    LOG_FILE = LOG_DIR / 'hermes.log'
    SCRIPTS_DIR = BASE_DIR / "scripts"

    SQLALCHEMY_DATABASE_URI = "sqlite:///hermes.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    API_STATIC_KEY = os.getenv("API_STATIC_KEY") or "e387faae9cf0478eb6e9dc1b4912e89e"
    FERNET_KEY = os.getenv("FERNET_KEY") or "UvrPTrfAkO_bmmADbon0yV-8dVhi3bhOLvqXllsbr-Q="

    HERMES_GITHUB_REPO = "https://github.com/indrajit912/Hermes.git"
    HERMES_HOMEPAGE = "https://hermesbot.pythonanywhere.com"
    HERMES_DEFAULT_BOT_LIMIT = os.getenv("HERMES_DEFAULT_BOT_LIMIT") or 10

    # Email Bot Credentials
    BOT_EMAIL = os.getenv("BOT_EMAIL") or "default@gmail.com"
    BOT_PASSWORD = os.getenv("BOT_PASSWORD") or "defaultpassword"
    BOT_MAIL_SERVER = os.getenv("BOT_SMTP_SERVER")  or "smtp.gmail.com"
    BOT_MAIL_PORT = int(os.getenv("BOT_SMTP_PORT")) or 587
    MAIL_USE_TLS = True


LOG_FILE = Config.LOG_FILE

LOG_DIR = Config.LOG_DIR
LOG_DIR.mkdir(exist_ok=True) # create logs directory if not exists