"""
Hermes - rotate_key.py
Author: Indrajit Ghosh
Created On: Sep 20, 2025

Rotates the Fernet key used for encrypting sensitive data in the database.
"""

import os
import click
from cryptography.fernet import Fernet
from app import create_app
from app.extensions import db
from app.models import User, EmailBot

app = create_app()

ENV_FILE = ".env"

def update_env_key(new_key, old_key_exists=True):
    """Update .env with new FERNET_KEY and move old to OLD_FERNET_KEY"""
    if not os.path.exists(ENV_FILE):
        click.echo(f"❌ .env file not found at {ENV_FILE}")
        return False

    lines = []
    with open(ENV_FILE, "r") as f:
        lines = f.readlines()

    fernet_found = False
    old_fernet_set = False
    new_lines = []

    for line in lines:
        if line.startswith("FERNET_KEY="):
            if old_key_exists:
                # Move old key to OLD_FERNET_KEY
                old_value = line.strip().split("=", 1)[1]
                new_lines.append(f"OLD_FERNET_KEY={old_value}\n")
                old_fernet_set = True
            # Set new FERNET_KEY
            new_lines.append(f"FERNET_KEY={new_key}\n")
            fernet_found = True
        else:
            new_lines.append(line)

    if not fernet_found:
        new_lines.append(f"FERNET_KEY={new_key}\n")
        if old_key_exists:
            # backup old key if exists in env
            old_value = os.environ.get("FERNET_KEY")
            if old_value:
                new_lines.append(f"OLD_FERNET_KEY={old_value}\n")
                old_fernet_set = True

    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)

    click.echo(f"✅ Updated {ENV_FILE} with new FERNET_KEY")
    if old_fernet_set:
        click.echo(f"ℹ️ Old FERNET_KEY moved to OLD_FERNET_KEY")

    return True


@click.command()
def rotate_key():
    """Rotate the Fernet encryption key and re-encrypt all sensitive DB fields."""
    old_key = click.prompt("Enter current FERNET_KEY", hide_input=True)
    new_key = Fernet.generate_key().decode()
    click.echo(f"🔑 Generated new Fernet key: {new_key}")

    # Set old key in memory for decryption
    os.environ["FERNET_KEY"] = old_key

    with app.app_context():
        # Re-encrypt User API keys
        users = User.query.all()
        for u in users:
            if u.api_key_encrypted:
                plain = u.api_key  # decrypted automatically
                u.api_key_encrypted = None  # reset
                u.api_key = plain           # re-encrypted with new key

            if u.api_key_plain_encrypted:
                plain = u.api_key_plain
                u.api_key_plain_encrypted = None
                u.api_key_plain = plain

        # Re-encrypt EmailBot fields
        bots = EmailBot.query.all()
        for b in bots:
            if b.email_encrypted:
                plain = b.email
                b.email_encrypted = None
                b.email = plain
            if b.password_encrypted:
                plain = b.password
                b.password_encrypted = None
                b.password = plain

        db.session.commit()
        click.echo("✅ All sensitive fields re-encrypted with new key")

    # Update .env
    update_env_key(new_key, old_key_exists=True)
    click.echo("🎉 Key rotation completed successfully!")


if __name__ == "__main__":
    rotate_key()
