
from flask import Blueprint, render_template
from datetime import datetime
from config import Config

home_bp = Blueprint("home", __name__)

@home_bp.route("/", methods=["GET"])
def homepage():
    return render_template("homepage.html", year=datetime.now().year)

@home_bp.route("/docs", methods=["GET"])
def full_docs():
    email_client_code_path = Config.SCRIPTS_DIR / "send_email_client.py"
    email_client_code = email_client_code_path.read_text() if email_client_code_path.exists() else "# send_email_client.py not found."
    return render_template(
        "full_docs.html", 
        year=datetime.now().year, 
        hermes_default_bot_limit=Config.HERMES_DEFAULT_BOT_LIMIT,
        email_client_code=email_client_code,
        hermes_github_repo=Config.HERMES_GITHUB_REPO
    )
