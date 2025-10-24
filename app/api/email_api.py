import os
import base64
import tempfile
import logging

from flask import Blueprint, request, jsonify, current_app
from app.models import EmailBot
from app.extensions import db
from config import Config
from app.utils.email_message import EmailMessage
from scripts.utils import is_valid_email_address
from app.utils.auth import get_current_user, require_api_key, log_request

logger = logging.getLogger(__name__)

email_bp = Blueprint("email_api", __name__, url_prefix="/api/v1")

@email_bp.route("/send-email", methods=["POST"])
@require_api_key
@log_request
def send_email():
    """
    Send an email using either a user-owned EmailBot or the default Hermes bot.

    Endpoint:
    ---------
    POST /api/v1/send-email

    Authentication:
    ---------------
    - Requires an API key in the Authorization header.
      Example: Authorization: Bearer <API_KEY>

    Request Body (JSON):
    --------------------
    {
        "to": "recipient@example.com",            # required, recipient email
        "subject": "Test Email",                  # optional, subject line
        "email_plain_text": "Hello world!",       # optional, plain text body
        "email_html_text": "<p>Hello world!</p>", # optional, HTML body
        "cc": ["cc1@example.com"],                # optional, list of CC recipients
        "bcc": ["bcc1@example.com"],              # optional, list of BCC recipients
        "from_name": "Hermes Bot",                # optional, display name for sender
        "bot_id": 123,                            # optional, use a specific EmailBot
        "attachments": [                          # optional, attachments
            {
                "filename": "hello.txt",
                "content": "SGVsbG8gd29ybGQh"     # base64 for "Hello world!"
            }
        ]
        # also accepts:
        # - list of file paths ["./path/to/file1.txt", "./path/to/file2.pdf"]
        # - single file path string "./path/to/file.txt"
    }

    Validation:
    -----------
    - "to" address is validated for:
        * correct email format (RFC-compliant)
    - Invalid or malformed addresses return HTTP 400.

    Responses:
    ----------
    200 OK
    {
        "success": true,
        "message": "Email sent successfully!",
        "hermes_default_usage": {     # only if default Hermes bot is used
            "used": 2,
            "remaining": 3,
            "limit": 5,
            "docs": "https://<your-domain>/docs"
        }
    }

    400 Bad Request
    {
        "success": false,
        "error": "Invalid email format: ..."
    }
    or
    {
        "success": false,
        "error": "Invalid bot ID or bot does not belong to user"
    }
    or
    {
        "success": false,
        "error": "User not found"
    }

    403 Forbidden
    {
        "success": false,
        "error": "Default Hermes bot usage limit exceeded. Please create your own EmailBot.",
        "docs": "https://<your-domain>/docs"
    }

    500 Internal Server Error
    {
        "success": false,
        "error": "<detailed error message>"
    }

    Example (cURL):
    ---------------
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
                    "content": "SGVsbG8gd29ybGQh"
                }
            ]
          }'
    """
    data = request.json
    user = get_current_user()
    if not user:
        logger.warning("Send-email failed: User not found")
        return jsonify({"success": False, "error": "User not found"}), 400

    logger.info(f"Send-email request started by user_id={user.id}")

    bot_id = data.get("bot_id")
    if bot_id:
        # --- using user’s own bot ---
        bot = EmailBot.query.filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            logger.warning(f"Send-email failed: Invalid bot_id={bot_id} for user_id={user.id}")
            return jsonify({"success": False, "error": "Invalid bot ID or bot does not belong to user"}), 400

        sender_email = bot.email
        sender_password = bot.password
        smtp_server = bot.smtp_server
        smtp_port = bot.smtp_port
        logger.info(f"Using user-owned EmailBot (id={bot.id}) for user_id={user.id}")
    else:
        # --- using default Hermes bot ---
        if user.hermes_default_usage >= Config.HERMES_DEFAULT_BOT_LIMIT:
            logger.warning(
                f"User {user.id} exceeded Hermes default bot usage "
                f"(limit={Config.HERMES_DEFAULT_BOT_LIMIT})"
            )
            return jsonify({
                "success": False,
                "error": "Default Hermes bot usage limit exceeded. "
                         "Please create your own EmailBot.",
                "docs": f"{Config.HERMES_HOMEPAGE}/docs"
            }), 403

        user.hermes_default_usage += 1
        db.session.commit()
        logger.info(
            f"User {user.id} used Hermes default bot "
            f"({user.hermes_default_usage}/{Config.HERMES_DEFAULT_BOT_LIMIT})"
        )

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
                # Create a temporary directory (unique for this run)
                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir, att["filename"])
    
                # If you want to avoid overwriting existing files
                counter = 1
                original_file_path = file_path
                while os.path.exists(file_path):
                    file_path = os.path.join(temp_dir, f"{counter}_{att['filename']}")
                    counter += 1
    
                # Write the file
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(att["content"]))
    
                attachments.append(file_path)
                logger.debug(f"Attachment saved to temp file {file_path}")
    
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

        response_data = {"success": True, "message": "Email sent successfully!"}

        # If Hermes default bot was used, include usage info
        if not bot_id:
            remaining = Config.HERMES_DEFAULT_BOT_LIMIT - user.hermes_default_usage
            response_data["hermes_default_usage"] = {
                "used": user.hermes_default_usage,
                "remaining": max(remaining, 0),
                "limit": Config.HERMES_DEFAULT_BOT_LIMIT,
                "docs": f"{Config.HERMES_HOMEPAGE}/docs"
            }

        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Email send failed for user_id={user.id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
