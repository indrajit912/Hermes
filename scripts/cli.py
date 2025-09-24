"""
Hermes - cli.py
Author: Indrajit Ghosh
Created On: Sep 20, 2025

# Usage Examples:

# Create a normal user
python -m scripts.cli create --name "Alice" --email "alice@example.com"

# Create an admin user
python -m scripts.cli create --name "Bob" --email "bob@example.com" --admin

# Approve user
python -m scripts.cli approve alice@example.com

# Update user (make admin)
python -m scripts.cli update alice@example.com --make-admin

# Update user (rename + change email)
python -m scripts.cli update alice@example.com --name "Alicia" --new-email "alicia@example.com"

# Delete user
python -m scripts.cli delete alicia@example.com

# List all users
python -m scripts.cli list-user

# Rotate encryption keys
python -m scripts.cli rotate --fernet-key
python -m scripts.cli rotate --api-secret-key

# Generate new keys
python -m scripts.cli generate-keys
"""
import os
import click
import uuid
from cryptography.fernet import Fernet
from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

@click.group()
def cli():
    """CLI for Hermes

    Available Commands:
      create         Create a new user (pending approval)
      approve        Approve a user
      update         Update user details (make admin, rename, change email)
      delete         Delete a user
      list-user      List all users
      rotate         Rotate encryption keys (--fernet-key, --api-secret-key)
      generate-keys  Generate new keys
    """
    pass

# -------------------------
# CREATE USER
# -------------------------
@cli.command("create")
@click.option("--name", prompt=True, help="Name of the user")
@click.option("--email", prompt=True, help="Email of the user")
@click.option("--admin", is_flag=True, help="Make this user an admin")
def create_user(name, email, admin):
    """Create a new user (pending approval)"""
    with app.app_context():
        if User.query.filter_by(email=email).first():
            click.echo("❌ User with this email already exists")
            return

        plain_key = str(uuid.uuid4().hex)
        user = User(
            name=name,
            email=email,
            api_key_plain=plain_key,  # automatically encrypted
            is_admin=admin
        )
        db.session.add(user)
        db.session.commit()

        click.echo(f"✅ User created: {user.name} ({user.email})")
        click.echo(f"   Pending approval. API Key (plain): {plain_key}")


# -------------------------
# APPROVE USER
# -------------------------
@cli.command("approve")
@click.argument("email")
def approve_user(email):
    """Approve a user and store their API key as encrypted"""
    from app.utils.mailer import send_email

    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo("❌ User not found")
            return
        if user.api_key_approved:
            click.echo("ℹ️ User already approved")
            return
        if not user.api_key_plain:
            click.echo("❌ No pending API key found for this user")
            return

        # Move plain API key to encrypted field via property
        user.api_key = user.api_key_plain
        user.api_key_plain = None
        user.api_key_approved = True
        db.session.commit()

        api_key = user.api_key  # decrypted automatically via property

        click.echo(f"✅ User approved: {user.name} ({user.email})")
        click.echo(f"   API Key (give to user): {api_key}")

        # Email using Jinja template
        success = send_email(
            to=user.email,
            subject="Hermes API Access Approved ✅",
            html_template="approval.html",
            template_context={
                "name": user.name, 
                "api_key": user.api_key, 
                "homepage_url": "hermes.com"
            }
        )
        if success:
            click.echo("📧 Approval email sent successfully.")
        else:
            click.echo("⚠️ Failed to send approval email. Check logs.")


# -------------------------
# DELETE USER
# -------------------------
@cli.command("delete")
@click.argument("email")
def delete_user(email):
    """Delete a user by email"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo("❌ User not found")
            return
        db.session.delete(user)
        db.session.commit()
        click.echo(f"🗑️ Deleted user {email}")


# -------------------------
# UPDATE USER
# -------------------------
@cli.command("update")
@click.argument("email")
@click.option("--name", help="Change user's name")
@click.option("--new-email", help="Change user's email")
@click.option("--make-admin", is_flag=True, help="Grant admin rights")
@click.option("--revoke-admin", is_flag=True, help="Remove admin rights")
def update_user(email, name, new_email, make_admin, revoke_admin):
    """Update user details"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo("❌ User not found")
            return

        if name:
            user.name = name
        if new_email:
            user.email = new_email
        if make_admin:
            user.is_admin = True
        if revoke_admin:
            user.is_admin = False

        db.session.commit()
        click.echo(f"✅ Updated user {user.email}")


# -------------------------
# LIST USERS
# -------------------------
@cli.command("list-user")
def list_users():
    """List all users"""
    with app.app_context():
        users = User.query.all()
        if not users:
            click.echo("No users found")
            return
        for u in users:
            status = "✅ Approved" if u.api_key_approved else "⏳ Pending"
            role = "👮 Admin" if u.is_admin else "👤 User"
            click.echo(f"- {u.name} ({u.email}) [{status}, {role}]")


# -------------------------
# HELP COMMAND
# -------------------------
@cli.command("help")
def help_command():
    """Show detailed examples of how to use Hermes"""
    examples = """
Hermes - cli.py
Author: Indrajit Ghosh
Created On: Sep 20, 2025

# Initialize Hermes (generate keys)
python -m scripts.cli init-hermes

# Create a normal user
python -m scripts.cli create --name "Alice" --email "alice@example.com"

# Create an admin user
python -m scripts.cli create --name "Bob" --email "bob@example.com" --admin

# Approve user
python -m scripts.cli approve alice@example.com

# Update user (make admin)
python -m scripts.cli update alice@example.com --make-admin

# Update user (rename + change email)
python -m scripts.cli update alice@example.com --name "Alicia" --new-email "alicia@example.com"

# Delete user
python -m scripts.cli delete alicia@example.com

# List all users
python -m scripts.cli list-user

# Rotate encryption keys
python -m scripts.cli rotate --fernet-key
python -m scripts.cli rotate --api-secret-key
"""
    click.echo(examples)


# -------------------------
# ROTATE KEYS
# -------------------------
@cli.command("rotate")
@click.option("--fernet-key", is_flag=True, help="Rotate the Fernet encryption key")
@click.option("--api-secret-key", is_flag=True, help="Rotate the API secret key")
def rotate_keys(fernet_key, api_secret_key):
    """Rotate encryption keys using scripts/rotate_keys.py"""
    import subprocess
    args = ["python", "scripts/rotate_keys.py"]
    if fernet_key:
        args.append("--fernet-key")
    if api_secret_key:
        args.append("--api-secret-key")
    subprocess.run(args)

# -------------------------
# INIT HERMES (GENERATE KEYS)
# -------------------------
def generate_static_api_key():
    return uuid.uuid4().hex  # 32 hex characters

def generate_fernet_key():
    return Fernet.generate_key().decode()  # base64-encoded string

@cli.command("init-hermes")
def init_hermes():
    """
    Generate new keys (FERNET_KEY + API_STATIC_KEY) in .env and add them.
    If .env already has keys, they will be overwritten.
    """

    env_path = ".env"
    if not os.path.exists(env_path):
        click.echo("❌ .env file not found in current directory.")
        return

    # Read all lines from .env
    with open(env_path, "r") as f:
        lines = f.readlines()

    # Prepare new keys
    new_fernet_key = generate_fernet_key()
    new_api_static_key = generate_static_api_key()

    # Overwrite or add the keys
    found_fernet = False
    found_api_static = False
    new_lines = []
    for line in lines:
        if line.startswith("FERNET_KEY="):
            new_lines.append(f"FERNET_KEY={new_fernet_key}\n")
            found_fernet = True
        elif line.startswith("API_STATIC_KEY="):
            new_lines.append(f"API_STATIC_KEY={new_api_static_key}\n")
            found_api_static = True
        else:
            new_lines.append(line)

    if not found_fernet:
        new_lines.append(f"FERNET_KEY={new_fernet_key}\n")
    if not found_api_static:
        new_lines.append(f"API_STATIC_KEY={new_api_static_key}\n")

    # Write back to .env
    with open(env_path, "w") as f:
        f.writelines(new_lines)

    click.echo("✅ FERNET_KEY and API_STATIC_KEY have been generated and written to .env")
    click.echo(f"FERNET_KEY={new_fernet_key}")
    click.echo(f"API_STATIC_KEY={new_api_static_key}")

    click.echo("\nNow do the following:")
    click.echo("[-]ℹ️ Run: flask db upgrade")
    click.echo("[-]ℹ️ Create an admin user using the 'create' command")
    click.echo("[-]ℹ️ Approve the admin user using the 'approve' command")


if __name__ == "__main__":
    cli()
