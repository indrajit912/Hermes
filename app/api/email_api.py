import os
import base64
import tempfile
import logging

from flask import Blueprint, request, jsonify, current_app
from app.models import EmailBot
from app.utils.email_message import EmailMessage
from app.utils.auth import get_current_user, require_api_key

logger = logging.getLogger(__name__)

email_bp = Blueprint("email_api", __name__, url_prefix="/api/v1")

@email_bp.route("/send-email", methods=["POST"])
@require_api_key
def send_email():
    """
    Send an email using a specified or default bot.

    Endpoint: POST /api/v1/send-email

    Expects JSON with:
      - to: recipient email address (required)
      - subject: email subject (optional)
      - email_plain_text: plain text body (optional)
      - email_html_text: HTML body (optional)
      - cc: list of CC addresses (optional)
      - bcc: list of BCC addresses (optional)
      - from_name: sender name (optional)
      - bot_id: use a specific EmailBot (optional)
      - attachments: 
          - list of dicts with {"filename": ..., "content": ...} (base64-encoded)
          - or list of file paths (strings)
          - or a single file path (string)
        If a list of file paths is provided, will attempt to convert each to {"filename", "content"} if possible.
    Returns JSON with success status and message or error.
    """
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

    # Handle attachments: decode base64 and save as temp files if needed
    attachments = []
    raw_attachments = data.get("attachments", [])
    # If attachments is a single string (file path), convert to list
    if isinstance(raw_attachments, str):
        raw_attachments = [raw_attachments]
    # If attachments is a list of file paths, try to convert to dicts
    if isinstance(raw_attachments, list) and all(isinstance(a, str) for a in raw_attachments):
        converted = []
        for path in raw_attachments:
            try:
                with open(path, "rb") as f:
                    content = f.read()
                converted.append({
                    "filename": os.path.basename(path),
                    "content": base64.b64encode(content).decode("utf-8")
                })
            except Exception:
                # If file can't be read, keep as path
                converted.append(path)
        raw_attachments = converted

    for att in raw_attachments:
        if isinstance(att, dict) and "filename" in att and "content" in att:
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_' + att["filename"])
                temp_file.write(base64.b64decode(att["content"]))
                temp_file.close()
                attachments.append(temp_file.name)
            except Exception as e:
                logger.error(f"Failed to decode attachment {att.get('filename')}: {str(e)}")
        else:
            # Assume it's a file path
            attachments.append(att)

    try:
        msg = EmailMessage(
            sender_email_id=sender_email,
            to=data["to"],
            subject=data.get("subject"),
            email_plain_text=data.get("email_plain_text"),
            email_html_text=data.get("email_html_text"),
            cc=data.get("cc"),
            bcc=data.get("bcc"),
            attachments=attachments,
            formataddr_text=data.get("from_name")
        )
        msg.send(
            sender_email_password=sender_password,
            server_info=(smtp_server, smtp_port),
            print_success_status=False
        )
        logger.info(f"Email sent successfully to {data['to']}")
        # Optionally: clean up temp files after sending
        for f in attachments:
            if isinstance(f, str) and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        return jsonify({"success": True, "message": "Email sent"})
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500