import logging

from flask import Blueprint, jsonify

from app.models import User
from app.extensions import db
from app.utils.auth import admin_only
from app.utils.mailer import send_email
from config import Config


admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


@admin_bp.route("/approve-user/<user_id>", methods=["POST"])
@admin_only
def approve_user(user_id):
    logger = logging.getLogger("hermes")
    logger.info(f"Admin attempting to approve user {user_id}")
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User not found for approval: {user_id}")
        return jsonify({"error": "User not found"}), 404
    if user.api_key_approved:
        logger.info(f"User {user_id} already approved")
        return jsonify({"message": "User already approved"}), 200
    if not user.api_key_plain:
        logger.warning(f"No pending API key for user {user_id}")
        return jsonify({"error": "No pending API key found for this user"}), 400

    # Use the property setter to encrypt automatically
    user.api_key = user.api_key_plain
    user.api_key_plain = None
    user.api_key_approved = True
    db.session.commit()

    # Send email to the user confirming the approval
    send_email(
        to=user.email,
        subject="Hermes API Access Approved ✅",
        html_template="approval.html",
        template_context={
            "name": user.name, 
            "api_key": user.api_key, 
            "hermes_homepage": Config.HERMES_HOMEPAGE
        }
    )

    logger.info(f"User {user_id} approved successfully")
    return jsonify({
        "success": True,
        "user_id": user.id,
        "api_key": user.api_key,  # show plain once
    })


@admin_bp.route("/list-users", methods=["GET"])
@admin_only
def list_users_admin():
    """
    List all registered users (admin-only).

    Endpoint:
    ---------
    GET /api/v1/admin/list-users

    Headers:
    --------
    - Authorization: Bearer <Admin user's personal API key>
      OR
    - X-STATIC-KEY: <Hermes static API key>

    Description:
    ------------
    Admins can retrieve a list of all users registered in the Hermes system.
    The response includes user ID, name, email, approval status, and role.

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "users": [
            {
                "id": "<user_id>",
                "name": "Alice",
                "email": "alice@example.com",
                "is_approved": true,
                "is_admin": false
            },
            ...
        ]
    }

    Response (Errors):
    ------------------
    Status Code: 403
    {
        "error": "Admin access required"
    }

    Example CURL:
    -------------
    # Using Bearer token (admin personal API key)
    curl -X GET http://localhost:5000/api/v1/admin/list-users \
        -H "Authorization: Bearer <admin_api_key>"

    # Using Hermes static key
    curl -X GET http://localhost:5000/api/v1/admin/list-users \
        -H "X-STATIC-KEY: <hermes_static_key>"
    """
    users = User.query.all()
    user_list = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "api_key_approved": u.api_key_approved,
            "is_admin": u.is_admin,
            "api_key": u.api_key,
            "api_key_plain": u.api_key_plain,
            "date_joined": u.date_joined.isoformat(),
            "email_bots": [
                {
                    "bot_username": bot.username,
                    "bot_id": bot.id
                } 
                for bot in u.email_bots
            ]
        } for u in users
    ]
    return jsonify({"success": True, "users": user_list})


@admin_bp.route("/delete-user/<user_id>", methods=["DELETE"])
@admin_only
def delete_user(user_id):
    """
    Delete a user (admin-only).

    Endpoint:
    ---------
    DELETE /api/v1/admin/delete-user/<user_id>

    Headers:
    --------
    - Authorization: Bearer <Admin user's personal API key>
      OR
    - X-STATIC-KEY: <Hermes static API key>

    Description:
    ------------
    Admins can delete a user account using this endpoint. All associated EmailBots
    will also be deleted automatically due to cascade behavior in the database.

    URL Parameters:
    ---------------
    - user_id: ID of the user to delete.

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "User deleted successfully",
        "user_id": "<user_id>"
    }

    Response (Errors):
    ------------------
    Status Code: 404
    {
        "error": "User not found"
    }

    Status Code: 403
    {
        "error": "Admin access required"
    }

    Example CURL:
    -------------
    # Using Bearer token (admin personal API key)
    curl -X DELETE http://localhost:5000/api/v1/admin/delete-user/<user_id> \
        -H "Authorization: Bearer <admin_api_key>"

    # Using Hermes static key
    curl -X DELETE http://localhost:5000/api/v1/admin/delete-user/<user_id> \
        -H "X-STATIC-KEY: <hermes_static_key>"
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "User deleted successfully",
        "user_id": user_id
    })
