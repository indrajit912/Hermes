"""
Hermes - manage_users.py
Author: Indrajit Ghosh
Created On: Sep 20, 2025

# Usage Examples:

# Create a normal user
python -m scripts.manage_users create --name "Alice" --email "alice@example.com"

# Create an admin user
python -m scripts.manage_users create --name "Bob" --email "bob@example.com" --admin

# Approve user
python -m scripts.manage_users approve alice@example.com

# Update user (make admin)
python -m scripts.manage_users update alice@example.com --make-admin

# Update user (rename + change email)
python -m scripts.manage_users update alice@example.com --name "Alicia" --new-email "alicia@example.com"

# Delete user
python -m scripts.manage_users delete alicia@example.com

# List all users
python -m scripts.manage_users list
"""

import click
import uuid
from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

@click.group()
def cli():
    """Manage Hermes Users"""
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

        plain_key = str(uuid.uuid4())
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
@cli.command("list")
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
    """Show detailed examples of how to use Hermes manage_users.py"""
    examples = """
Hermes - manage_users.py
Author: Indrajit Ghosh
Created On: Sep 20, 2025

# Create a normal user
python -m scripts.manage_users create --name "Alice" --email "alice@example.com"

# Create an admin user
python -m scripts.manage_users create --name "Bob" --email "bob@example.com" --admin

# Approve user
python -m scripts.manage_users approve alice@example.com

# Update user (make admin)
python -m scripts.manage_users update alice@example.com --make-admin

# Update user (rename + change email)
python -m scripts.manage_users update alice@example.com --name "Alicia" --new-email "alicia@example.com"

# Delete user
python -m scripts.manage_users delete alicia@example.com

# List all users
python -m scripts.manage_users list
"""
    click.echo(examples)


if __name__ == "__main__":
    cli()
