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

    Headers:
    --------
    - Authorization: Bearer <Admin user's personal API key>

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

    Returns:
    --------
    On success:
        {
            "success": true,
            "message": "Email sent"
        }
    On error:
        {
            "success": false,
            "error": "<error message>"
        }
        or
        {
            "error": "<error message>"
        }

    Example call (using curl):
    --------------------------
    curl -X POST https://<your-domain>/api/v1/send-email \\
      -H "Authorization: Bearer <API_KEY>" \\
      -H "Content-Type: application/json" \\
      -d '{
            "to": "recipient@example.com",
            "subject": "Test Email",
            "email_plain_text": "Hello, this is a test.",
            "cc": ["cc1@example.com"],
            "bcc": ["bcc1@example.com"],
            "from_name": "Hermes Bot",
            "attachments": [
                {
                    "filename": "hello.txt",
                    "content": "SGVsbG8gd29ybGQh"  // base64 for "Hello world!"
                }
            ]
          }'
    """
    data = request.json
    user = get_current_user()
    if not user:
        logger.warning("Send-email failed: User not found")
        return jsonify({"error": "User not found"}), 400

    logger.info(f"Send-email request started by user_id={user.id}")

    bot_id = data.get("bot_id")
    if bot_id:
        bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            logger.warning(f"Send-email failed: Invalid bot_id={bot_id} for user_id={user.id}")
            return jsonify({"error": "Invalid bot ID or bot does not belong to user"}), 400

        sender_email = bot.email       # decrypted automatically
        sender_password = bot.password # decrypted automatically
        smtp_server = bot.smtp_server
        smtp_port = bot.smtp_port
        logger.info(f"Using user-owned EmailBot (id={bot.id}) for user_id={user.id}")
    else:
        sender_email = current_app.config.get("BOT_EMAIL")
        sender_password = current_app.config.get("BOT_PASSWORD")
        smtp_server = current_app.config.get("BOT_MAIL_SERVER", "smtp.gmail.com")
        smtp_port = current_app.config.get("BOT_MAIL_PORT", 587)
        logger.info(f"Using default Hermes bot for user_id={user.id}")

    # ----------------------
    # Handle attachments
    # ----------------------
    attachments = []
    raw_attachments = data.get("attachments", [])
    if isinstance(raw_attachments, str):
        raw_attachments = [raw_attachments]

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
                logger.debug(f"Attachment {path} converted to base64")
            except Exception as e:
                logger.error(f"Failed to read attachment file {path}: {e}")
                converted.append(path)
        raw_attachments = converted

    for att in raw_attachments:
        if isinstance(att, dict) and "filename" in att and "content" in att:
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_' + att["filename"])
                temp_file.write(base64.b64decode(att["content"]))
                temp_file.close()
                attachments.append(temp_file.name)
                logger.debug(f"Attachment saved to temp file {temp_file.name}")
            except Exception as e:
                logger.error(f"Failed to decode attachment {att.get('filename')}: {str(e)}")
        else:
            attachments.append(att)
            logger.debug(f"Attachment added as path: {att}")

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
            formataddr_text=data.get("from_name"),
            stdout_print=False
        )
        msg.send(
            sender_email_password=sender_password,
            server_info=(smtp_server, smtp_port),
            print_success_status=False
        )
        logger.info(f"Email successfully sent to {data['to']} by user_id={user.id}")

        # Cleanup temp files
        for f in attachments:
            if isinstance(f, str) and os.path.exists(f):
                try:
                    os.remove(f)
                    logger.debug(f"Temp file {f} deleted after sending")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {f}: {e}")

        return jsonify({"success": True, "message": "Email sent"})
    except Exception as e:
        logger.error(f"Email send failed for user_id={user.id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500