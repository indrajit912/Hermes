
from flask import Blueprint, render_template
from datetime import datetime

home_bp = Blueprint("home", __name__)

@home_bp.route("/", methods=["GET"])
def homepage():
    return render_template("homepage.html", year=datetime.now().year)

@home_bp.route("/docs", methods=["GET"])
def full_docs():
    return render_template("full_docs.html", year=datetime.now().year)
