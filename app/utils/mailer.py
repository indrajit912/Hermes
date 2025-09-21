import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.utils.email_message import EmailMessage

BOT_EMAIL = os.getenv("BOT_EMAIL")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
SMTP_SERVER = os.getenv("BOT_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("BOT_SMTP_PORT", 587))

# Setup Jinja environment
template_env = Environment(
    loader=FileSystemLoader("app/email_templates"),
    autoescape=select_autoescape(["html", "xml"])
)

def render_template(template_name, **kwargs):
    """Render email template with given context"""
    template = template_env.get_template(template_name)
    return template.render(**kwargs)

def send_email_with_template(to_email: str, subject: str, template_name: str, context: dict, plain_body: str = None):
    """Send HTML email using Jinja2 templates"""
    try:
        html_body = render_template(template_name, **context)

        msg = EmailMessage(
            sender_email_id=BOT_EMAIL,
            to=to_email,
            subject=subject,
            email_plain_text=plain_body,
            email_html_text=html_body,
            formataddr_text="Hermes Bot"
        )
        msg.send(
            sender_email_password=BOT_PASSWORD,
            server_info=(SMTP_SERVER, SMTP_PORT),
            print_success_status=False
        )
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
