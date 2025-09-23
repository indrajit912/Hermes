"""
Hermes - rotate_keys.py
Author: Indrajit Ghosh
Created On: Sep 23, 2025

Rotates the Fernet key used for encrypting sensitive data in the database.
"""
import os
import argparse
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from app import create_app, db
from app.models import User, EmailBot
from app.utils.crypto import decrypt_value

ENV_FILE = ".env"


def update_env_var(key, new_value):
    """Update a key=value pair in the .env file"""
    lines = []
    updated = False
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={new_value}\n")
                    updated = True
                else:
                    lines.append(line)

    if not updated:
        lines.append(f"{key}={new_value}\n")

    with open(ENV_FILE, "w") as f:
        f.writelines(lines)


def rotate_fernet_key(app):
    """Rotate FERNET_KEY and re-encrypt all data"""
    old_key = os.getenv("FERNET_KEY")
    if not old_key:
        print("❌ No existing FERNET_KEY found in .env")
        return

    print("🔑 Rotating FERNET_KEY...")

    # Generate new key
    new_key = Fernet.generate_key().decode()

    with app.app_context():
        users = User.query.all()
        bots = EmailBot.query.all()

        for user in users:
            if user.api_key_encrypted:
                plain = decrypt_value(user.api_key_encrypted, key=old_key)
                user._set_api_key(plain, fernet_key=new_key)

            if user.api_key_plain_encrypted:
                plain = decrypt_value(user.api_key_plain_encrypted, key=old_key)
                user._set_api_key_plain(plain, fernet_key=new_key)

        for bot in bots:
            if bot.email_encrypted:
                plain = decrypt_value(bot.email_encrypted, key=old_key)
                bot._set_email(plain, fernet_key=new_key)

            if bot.password_encrypted:
                plain = decrypt_value(bot.password_encrypted, key=old_key)
                bot._set_password(plain, fernet_key=new_key)

        db.session.commit()

    # Update the .env with new key
    update_env_var("FERNET_KEY", new_key)
    print("✅ FERNET_KEY rotated successfully and data re-encrypted.")


def rotate_api_static_key():
    """Generate and update API_STATIC_KEY"""
    from scripts.generate_keys import generate_static_api_key
    new_key = generate_static_api_key()
    update_env_var("API_STATIC_KEY", new_key)
    print("✅ API_STATIC_KEY rotated successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rotate sensitive keys in .env and re-encrypt database if needed."
    )
    parser.add_argument(
        "--fernet-key", action="store_true",
        help="Rotate the FERNET_KEY and re-encrypt all DB fields"
    )
    parser.add_argument(
        "--api-static-key", action="store_true",
        help="Rotate the API_STATIC_KEY only"
    )
    args = parser.parse_args()

    load_dotenv(ENV_FILE)
    app = create_app()

    if args.fernet_key:
        rotate_fernet_key(app)

    if args.api_static_key:
        rotate_api_static_key()
