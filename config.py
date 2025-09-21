# Hermes - config.py
# Author: Indrajit Ghosh
# Created On: Sep 20, 2025

import os

class Config:
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
