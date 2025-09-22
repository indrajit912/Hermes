import uuid
from flask import Blueprint, request, jsonify, render_template, current_app
from app.extensions import db
from app.models import User, EmailBot
from app.utils.auth import get_current_user
from app.api.email_api import require_api_key
from app.utils.email_message import EmailMessage

user_bp = Blueprint("user_api", __name__, url_prefix="/api/v1")


@user_bp.route("/register", methods=["POST"])
def register():
    """
    Request a personal API key for Hermes.

    Endpoint: POST /api/v1/register

    Description:
    ------------
    This endpoint allows a new user to request access to the Hermes API.
    The API key will be generated and stored in the database, but it remains
    inactive until approved by an admin.

    Request JSON:
    -------------
    {
        "name": "<User's full name>",
        "email": "<User's email address>"
    }

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "API key requested, waiting for admin approval."
    }

    Response (Errors):
    ------------------
    Status Code: 400
    {
        "error": "Name and email required"
    }
    OR
    {
        "error": "User already exists"
    }

    Example CURL:
    -------------
    curl -X POST http://localhost:5000/api/v1/register \
        -H "Content-Type: application/json" \
        -d '{"name": "Alice", "email": "alice@example.com"}'
    """
    data = request.json
    name, email = data.get("name"), data.get("email")

    if not name or not email:
        return jsonify({"error": "Name and email required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "User already exists"}), 400

    plain_key = str(uuid.uuid4())
    user = User(name=name, email=email, api_key_plain=plain_key)
    db.session.add(user)
    db.session.commit()

    # Send email to the admin for approval
    # get all approved admins
    admin_emails = [
        admin.email for admin in User.query.filter_by(is_admin=True).all()
    ]

    if admin_emails:
        subject = "Hermes - New User Registration Pending Approval"
        context = {
            "name": user.name,
            "email": user.email,
            "user_id": user.id
        }

        html_body = render_template("new_user_notification.html", **context)

        msg = EmailMessage(
            sender_email_id=current_app.config.get('BOT_EMAIL'),
            to=admin_emails,
            subject=subject,
            email_html_text=html_body,
            formataddr_text="Hermes Bot"
        )

        msg.send(
            sender_email_password=current_app.config.get('BOT_PASSWORD'),
            server_info=(current_app.config.get("BOT_MAIL_SERVER"), current_app.config.get("BOT_MAIL_PORT")),
            print_success_status=False
        )

    return jsonify({
        "success": True,
        "message": "You are registered. Please wait for admin approval.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "account_activated": user.api_key_approved
        }
    }), 201


# -------------------------
# ADD EMAIL BOT
# -------------------------
@user_bp.route("/emailbot", methods=["POST"])
@require_api_key
def add_email_bot():
    """
    Add a new EmailBot for the authenticated user.

    Endpoint: POST /api/v1/emailbot

    Headers:
    --------
    - X-API-KEY: <User personal API key>
    - X-STATIC-KEY: <Hermes static API key> (optional for admin/trusted apps)

    Request JSON:
    -------------
    {
        "username": "AliceBot",             # optional friendly name
        "email": "alicebot@gmail.com",      # bot email
        "password": "app-password",         # bot app password
        "smtp_server": "smtp.gmail.com",    # optional, default "smtp.gmail.com"
        "smtp_port": 587                     # optional, default 587
    }

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "EmailBot added successfully",
        "bot_id": "<newly_created_bot_id>"
    }

    Response (Errors):
    ------------------
    Status Code: 400
    {
        "error": "Missing email or password"
    }

    Example CURL:
    -------------
    curl -X POST http://localhost:5000/api/v1/emailbot \
        -H "Content-Type: application/json" \
        -H "X-API-KEY: <user_api_key>" \
        -d '{"username": "AliceBot", "email": "alicebot@gmail.com", "password": "app-password"}'
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400

    data = request.json
    email = data.get("email")
    password = data.get("password")
    username = data.get("username")
    smtp_server = data.get("smtp_server", "smtp.gmail.com")
    smtp_port = data.get("smtp_port", 587)

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    bot = EmailBot(
        user_id=user.id,
        username=username,
        smtp_server=smtp_server,
        smtp_port=smtp_port
    )
    bot.email = email       # encrypted automatically
    bot.password = password # encrypted automatically

    db.session.add(bot)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "EmailBot added successfully",
        "bot_id": bot.id
    })


# -------------------------
# LIST EMAIL BOTS
# -------------------------
@user_bp.route("/emailbot", methods=["GET"])
@require_api_key
def list_email_bots():
    """
    List all EmailBots of the authenticated user.

    Endpoint: GET /api/v1/emailbot

    Headers:
    --------
    - X-API-KEY: <User personal API key>
    - X-STATIC-KEY: <Hermes static API key> (admin/trusted apps can view all)

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "bots": [
            {
                "id": "<bot_id>",
                "username": "AliceBot",
                "email": "alicebot@gmail.com",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587
            },
            ...
        ]
    }

    Response (Errors):
    ------------------
    Status Code: 400
    {
        "error": "User not found"
    }

    Example CURL:
    -------------
    curl -X GET http://localhost:5000/api/v1/emailbot \
        -H "X-API-KEY: <user_api_key>"
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400

    bots = EmailBot.query.filter_by(user_id=user.id).all()
    bot_list = [{
        "id": bot.id,
        "username": bot.username,
        "email": bot.email,  # decrypted automatically
        "smtp_server": bot.smtp_server,
        "smtp_port": bot.smtp_port
    } for bot in bots]

    return jsonify({"success": True, "bots": bot_list})
