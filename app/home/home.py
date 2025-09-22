from flask import Blueprint, render_template
from datetime import datetime

home_bp = Blueprint("home", __name__)

@home_bp.route("/", methods=["GET"])
def homepage():
    return render_template("homepage.html", year=datetime.now().year)
