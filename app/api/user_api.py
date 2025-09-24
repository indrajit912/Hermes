import uuid
import logging
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User, EmailBot, Log
from app.utils.auth import get_current_user, require_api_key, log_request
from app.utils.mailer import send_email
from config import Config

logger = logging.getLogger(__name__)

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
    logger.info(f"Register API called for email: {email}")

    if not name or not email:
        logger.warning("Name and email required for registration")
        return jsonify({"error": "Name and email required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        logger.warning(f"User already exists: {email}")
        return jsonify({"error": "User already exists"}), 400

    plain_key = str(uuid.uuid4().hex)
    user = User(name=name, email=email, api_key_plain=plain_key)
    db.session.add(user)
    db.session.commit()

    logger.info(f"User registered: {email}")

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
# GET CURRENT USER PROFILE
# -------------------------
@user_bp.route("/me", methods=["GET"])
@require_api_key
@log_request
def get_profile():
    """
    Get current authenticated user profile.

    Endpoint: GET /api/v1/me

    Headers:
    --------
    - Authorization: Bearer <User personal API key>

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "user": {
            "id": "<user_id>",
            "name": "Alice Example",
            "email": "alice@example.com",
            "api_key_approved": true,
            "date_joined": "...",
            "usage": {
                "total_api_calls": 45,
                "send_email_calls": 12,
                "last_activity": "2025-09-23T15:42:01+00:00",
                "success_rate": 0.91
            },
            "hermes_default_bot": {
                "usage": 3,
                "limit": 5,
                "exceeded": false
            }
        }
    }
    """
    logger.debug("Handling GET /api/v1/me request")

    user = get_current_user()
    if not user:
        logger.warning("GET /api/v1/me failed: no user found for provided API key")
        return jsonify({"error": "User not found"}), 400

    logger.info(f"User profile retrieved successfully for user_id={user.id}, email={user.email}")

    hermes_limit = getattr(Config, "HERMES_DEFAULT_BOT_LIMIT", 5)
    hermes_usage = user.hermes_default_usage or 0

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "api_key_approved": user.api_key_approved,
            "date_joined": user.date_joined_iso,
            "email_bot_count": user.email_bot_count,
            "usage": user.usage_summary(),
            "hermes_default_bot": {
                "usage": hermes_usage,
                "limit": hermes_limit,
                "exceeded": hermes_usage >= hermes_limit
            }
        }
    }), 200


# -------------------------
# ROTATE API KEY
# -------------------------
@user_bp.route("/apikey/rotate", methods=["POST"])
@require_api_key
@log_request
def rotate_api_key():
    """
    Rotate the user's API key (invalidate old one, issue new).

    Endpoint: POST /api/v1/apikey/rotate

    Headers:
    --------
    - Authorization: Bearer <User personal API key>

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "API key rotated successfully",
        "new_api_key": "<new_api_key>"
    }
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400

    new_key = str(uuid.uuid4().hex)
    user.api_key = new_key
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "API key rotated successfully",
        "new_api_key": new_key
    })


# -------------------------
# ADD EMAIL BOT
# -------------------------
@user_bp.route("/emailbot", methods=["POST"])
@require_api_key
@log_request
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

    logging.info(f"EmailBot added: {bot.id} for user: {user.id}")

    return jsonify({
        "success": True,
        "message": "EmailBot added successfully",
        "bot_id": bot.id
    })

# -------------------------
# LIST EMAIL BOTS
# -------------------------
@user_bp.route("/emailbots", methods=["GET"])
@user_bp.route("/emailbots/<bot_id>", methods=["GET"])
@require_api_key
@log_request
def list_email_bots(bot_id=None):
    """
    List all EmailBots of the authenticated user, or a specific EmailBot if bot_id is provided.

    Endpoint:
    ---------
    GET /api/v1/emailbots              → returns all EmailBots of the user
    GET /api/v1/emailbots/<bot_id>     → returns a single EmailBot by ID

    Headers:
    --------
    - Authorization: Bearer <User personal API key>

    Description:
    ------------
    Authenticated users can retrieve their EmailBots. If no bot_id is provided, all EmailBots
    associated with the user are returned. If bot_id is provided, details of that specific bot
    are returned.

    Response (Success):
    -------------------
    # For all EmailBots
    Status Code: 200
    {
        "success": True,
        "bots": [
            {
                "bot_id": "<bot_id>",
                "username": "AliceBot",
                "email": "alicebot@gmail.com",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "date_created": "2025-09-24T12:34:56Z"
            },
            ...
        ]
    }

    # For a single EmailBot
    Status Code: 200
    {
        "success": True,
        "bot": {
            "bot_id": "<bot_id>",
            "username": "AliceBot",
            "email": "alicebot@gmail.com",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "date_created": "2025-09-24T12:34:56Z"
        }
    }

    Response (Errors):
    ------------------
    Status Code: 400
    {
        "error": "User not found"
    }

    Status Code: 404
    {
        "error": "EmailBot not found or not owned by user"
    }

    Notes:
    ------
    - Email and password fields are decrypted automatically before returning.
    - Only the owner of the EmailBot can view its details.
    """

    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400
    
    if bot_id:
        bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            return jsonify({"error": "EmailBot not found or not owned by user"}), 404
        bot_data = {
            "bot_id": bot.id,
            "username": bot.username,
            "email": bot.email,  # decrypted automatically
            "smtp_server": bot.smtp_server,
            "smtp_port": bot.smtp_port,
            "date_created": bot.date_created_iso,
        }
        return jsonify({"success": True, "bot": bot_data})
    else:
        logging.debug(f"Listing all EmailBots for user: {user.id}") 

        bots = EmailBot.query.filter_by(user_id=user.id).all()
        bot_list = [{
            "bot_id": bot.id,
            "username": bot.username,
            "email": bot.email,  # decrypted automatically
            "smtp_server": bot.smtp_server,
            "smtp_port": bot.smtp_port,
            "date_created": bot.date_created_iso,
        } for bot in bots]

        logging.info(f"Fetched EmailBots for user: {user.id}, count: {len(bot_list)}")

        return jsonify({"success": True, "bots": bot_list})


# -------------------------
# UPDATE EMAIL BOT
# -------------------------
@user_bp.route("/emailbots/<bot_id>", methods=["PUT"])
@require_api_key
@log_request
def update_email_bot(bot_id):
    """
    Update an existing EmailBot of the authenticated user.
    """
    logger.debug(f"Handling PUT /api/v1/emailbots/{bot_id} request")

    user = get_current_user()
    if not user:
        logger.warning("Update EmailBot failed: no user found for provided API key")
        return jsonify({"error": "User not found"}), 400

    bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
    if not bot:
        logger.warning(f"Update EmailBot failed: bot_id={bot_id} not found for user_id={user.id}")
        return jsonify({"error": "Bot not found"}), 400

    data = request.json or {}
    logger.debug(f"Update payload for bot_id={bot_id}: {data}")

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

    logger.info(f"EmailBot updated successfully: bot_id={bot.id} for user_id={user.id}, email={user.email}")

    return jsonify({
        "success": True,
        "message": "EmailBot updated successfully",
        "bot_id": bot.id
    }), 200


# -------------------------
# DELETE EMAIL BOT
# -------------------------
@user_bp.route("/emailbots/<bot_id>", methods=["DELETE"])
@require_api_key
@log_request
def delete_email_bot(bot_id):
    """
    Delete an EmailBot owned by the authenticated user.
    """
    logger.debug(f"Handling DELETE /api/v1/emailbots/{bot_id} request")

    user = get_current_user()
    if not user:
        logger.warning("Delete EmailBot failed: no user found for provided API key")
        return jsonify({"error": "User not found"}), 400

    bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
    if not bot:
        logger.warning(f"Delete EmailBot failed: bot_id={bot_id} not found for user_id={user.id}")
        return jsonify({"error": "EmailBot not found or not owned by user"}), 404

    db.session.delete(bot)
    db.session.commit()

    logger.info(f"EmailBot deleted successfully: bot_id={bot_id} for user_id={user.id}, email={user.email}")

    return jsonify({
        "success": True,
        "message": "EmailBot deleted successfully",
        "bot_id": bot_id
    }), 200


# -------------------------
# USER ACTIVITY LOGS
# -------------------------
@user_bp.route("/logs", methods=["GET"])
@require_api_key
@log_request
def get_logs():
    """
    Fetch recent API activity logs for the authenticated user.
    """
    logger.debug("Handling GET /api/v1/logs request")

    user = get_current_user()
    if not user:
        logger.warning("Fetch logs failed: no user found for provided API key")
        return jsonify({"error": "User not found"}), 400

    limit = int(request.args.get("limit", 20))
    logger.debug(f"Fetching logs for user_id={user.id}, limit={limit}")

    logs = (
        Log.query.filter_by(user_id=user.id)
        .order_by(Log.timestamp.desc())
        .limit(limit)
        .all()
    )

    log_list = [{
        "id": log.id,
        "endpoint": log.endpoint,
        "method": log.method,
        "timestamp": log.timestamp_iso,
        "status_code": log.status_code
    } for log in logs]

    logger.info(f"Fetched {len(log_list)} logs for user_id={user.id}, email={user.email}")

    return jsonify({"success": True, "logs": log_list}), 200