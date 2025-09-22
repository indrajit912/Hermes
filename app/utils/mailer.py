import os
from app.utils.email_message import EmailMessage
from flask import render_template
from typing import List, Optional, Union

BOT_EMAIL = os.getenv("BOT_EMAIL")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
SMTP_SERVER = os.getenv("BOT_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("BOT_SMTP_PORT", 587))


def send_email(
    to: Union[str, List[str]],
    subject: str,
    html_template: str = None,
    template_context: dict = None,
    plain_text: str = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    sender_email: str = BOT_EMAIL,
    sender_password: str = BOT_PASSWORD,
    smtp_server: str = SMTP_SERVER,
    smtp_port: int = SMTP_PORT,
    from_name: str = "Hermes Bot"
):
    """
    Send an email with HTML and/or plain text content.

    Parameters:
    -----------
    - to: recipient email address or list of emails
    - subject: subject of the email
    - html_template: name of Jinja2 HTML template (optional)
    - template_context: dict to render the template (optional)
    - plain_text: fallback plain text body (optional)
    - cc: list of CC email addresses (optional)
    - bcc: list of BCC email addresses (optional)
    - attachments: list of file paths to attach (optional)
    - sender_email: sender's email (if None, use default bot email)
    - sender_password: sender's password (if None, use default bot password)
    - smtp_server: SMTP server (default: Gmail)
    - smtp_port: SMTP port (default: 587)
    - sender_name: display name for sender

    Returns:
    --------
    - True if email sent successfully, False otherwise
    """
    try:
        # Render HTML template if provided
        html_body = None
        if html_template and template_context is not None:
            html_body = render_template(html_template, **template_context)

        msg = EmailMessage(
            sender_email_id=sender_email,
            to=to,
            subject=subject,
            email_html_text=html_body,
            email_plain_text=plain_text,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            formataddr_text=from_name
        )

        msg.send(
            sender_email_password=sender_password,
            server_info=(smtp_server, smtp_port),
            print_success_status=False
        )

        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
