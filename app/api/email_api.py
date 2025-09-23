from flask import Blueprint, request, jsonify, current_app
from app.models import EmailBot
from app.utils.email_message import EmailMessage
from app.utils.auth import get_current_user, require_api_key
import logging

email_bp = Blueprint("email_api", __name__, url_prefix="/api/v1")


@email_bp.route("/send-email", methods=["POST"])
@require_api_key
def send_email():
    logger = logging.getLogger("hermes")
    logger.info(f"Send email request received from user: {get_current_user().email if get_current_user() else 'Unknown'}")
    data = request.json
    user = get_current_user()
    if not user:
        logger.warning("User not found for send-email API call")
        return jsonify({"error": "User not found"}), 400

    bot_id = data.get("bot_id")
    if bot_id:
        # Use specified EmailBot
        bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            logger.warning(f"Invalid bot ID {bot_id} or bot does not belong to user")
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
            print_success_status=False
        )
        logger.info(f"Email sent successfully to {data['to']}")
        return jsonify({"success": True, "message": "Email sent"})
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
