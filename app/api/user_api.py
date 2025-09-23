import uuid
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User, EmailBot
from app.utils.auth import get_current_user, require_api_key
from app.utils.mailer import send_email


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
    """
    data = request.json
    name, email = data.get("name"), data.get("email")

    if not name or not email:
        return jsonify({"error": "Name and email required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "User already exists"}), 400

    plain_key = str(uuid.uuid4().hex)
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

        send_email(
            to=admin_emails,
            subject=subject,
            html_template="new_user_notification.html",
            template_context=context,
            from_name="Hermes Bot"
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
    - Authorization: Bearer <User personal API key>

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
    - Authorization: Bearer <User personal API key>

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "bots": [
            {
                "bot_id": "<bot_id>",
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
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400

    bots = EmailBot.query.filter_by(user_id=user.id).all()
    bot_list = [{
        "bot_id": bot.id,
        "username": bot.username,
        "email": bot.email,  # decrypted automatically
        "smtp_server": bot.smtp_server,
        "smtp_port": bot.smtp_port
    } for bot in bots]

    return jsonify({"success": True, "bots": bot_list})


# -------------------------
# UPDATE EMAIL BOT
# -------------------------
@user_bp.route("/emailbot/<bot_id>", methods=["PUT"])
@require_api_key
def update_email_bot(bot_id):
    """
    Update an existing EmailBot of the authenticated user.

    Endpoint: PUT /api/v1/emailbot/<bot_id>

    Headers:
    --------
    - Authorization: Bearer <User personal API key>

    Request JSON (all fields optional, only send what you want to update):
    ---------------------------------------------------------------------
    {
        "username": "UpdatedBotName",       # optional
        "email": "updatedbot@gmail.com",    # optional
        "password": "new-app-password",     # optional
        "smtp_server": "smtp.outlook.com",  # optional
        "smtp_port": 465                     # optional
    }

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "EmailBot updated successfully",
        "bot_id": "<bot_id>"
    }

    Response (Errors):
    ------------------
    Status Code: 400
    {
        "error": "Bot not found"
    }
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400

    bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
    if not bot:
        return jsonify({"error": "Bot not found"}), 400

    data = request.json or {}

    if "username" in data:
        bot.username = data["username"]
    if "email" in data:
        bot.email = data["email"]  # encrypted automatically
    if "password" in data:
        bot.password = data["password"]  # encrypted automatically
    if "smtp_server" in data:
        bot.smtp_server = data["smtp_server"]
    if "smtp_port" in data:
        bot.smtp_port = data["smtp_port"]

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "EmailBot updated successfully",
        "bot_id": bot.id
    })


# -------------------------
# DELETE EMAIL BOT
# -------------------------
@user_bp.route("/emailbot/<bot_id>", methods=["DELETE"])
@require_api_key
def delete_email_bot(bot_id):
    """
    Delete an EmailBot owned by the authenticated user.

    Endpoint: DELETE /api/v1/emailbot/<bot_id>

    Headers:
    --------
    - Authorization: Bearer <User personal API key>

    URL Parameters:
    ---------------
    - bot_id: ID of the EmailBot to delete.

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "EmailBot deleted successfully",
        "bot_id": "<bot_id>"
    }

    Response (Errors):
    ------------------
    Status Code: 404
    {
        "error": "EmailBot not found or not owned by user"
    }
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400

    bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
    if not bot:
        return jsonify({"error": "EmailBot not found or not owned by user"}), 404

    db.session.delete(bot)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "EmailBot deleted successfully",
        "bot_id": bot_id
    }), 200
