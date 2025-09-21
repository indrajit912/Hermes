from flask import Blueprint

home_bp = Blueprint("home", __name__)

@home_bp.route("/", methods=["GET"])
def homepage():
    return "<h1>Welcome to Hermes!</h1>"