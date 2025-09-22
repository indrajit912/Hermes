from flask import Blueprint, request, jsonify, current_app
from app.models import EmailBot
from app.utils.email_message import EmailMessage
from app.utils.auth import get_current_user, require_api_key

email_bp = Blueprint("email_api", __name__, url_prefix="/api/v1")


@email_bp.route("/send-email", methods=["POST"])
@require_api_key
def send_email():
    """
    Send an email using a specified EmailBot or the default Hermes bot.

    Endpoint: POST /api/v1/send-email

    Headers:
    --------
    - Authorization: Bearer <User personal API key>

    Request JSON:
    -------------
    {
        "bot_id": "<optional: EmailBot ID to use>",    # optional
        "from_name": "Indrajit's Bot",
        "to": ["recipient1@example.com"],
        "subject": "Email Subject",
        "email_plain_text": "Plain text body",
        "email_html_text": "<p>HTML body</p>",
        "cc": ["cc@example.com"],                      # optional
        "bcc": ["bcc@example.com"],                    # optional
        "attachments": ["path/to/file.pdf"]           # optional
    }

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "Email sent"
    }

    Response (Errors):
    ------------------
    Status Code: 400
    {
        "error": "Invalid bot ID or bot does not belong to user"
    }

    Status Code: 500
    {
        "success": False,
        "error": "<Error message>"
    }
    """
    data = request.json
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 400

    bot_id = data.get("bot_id")
    if bot_id:
        # Use specified EmailBot
        bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            return jsonify({"error": "Invalid bot ID or bot does not belong to user"}), 400

        sender_email = bot.email       # decrypted automatically
        sender_password = bot.password # decrypted automatically
        smtp_server = bot.smtp_server
        smtp_port = bot.smtp_port

    else:
        # Use default Hermes bot
        sender_email = current_app.config.get("BOT_EMAIL")
        sender_password = current_app.config.get("BOT_PASSWORD")
        smtp_server = current_app.config.get("BOT_MAIL_SERVER", "smtp.gmail.com")
        smtp_port = current_app.config.get("BOT_MAIL_PORT", 587)

    try:
        msg = EmailMessage(
            sender_email_id=sender_email,
            to=data["to"],
            subject=data.get("subject"),
            email_plain_text=data.get("email_plain_text"),
            email_html_text=data.get("email_html_text"),
            cc=data.get("cc"),
            bcc=data.get("bcc"),
            attachments=data.get("attachments"),
            formataddr_text=data.get("from_name")
        )
        msg.send(
            sender_email_password=sender_password,
            server_info=(smtp_server, smtp_port),
        )
        return jsonify({"success": True, "message": "Email sent"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
