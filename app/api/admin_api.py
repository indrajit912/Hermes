import logging

from flask import Blueprint, jsonify

from app.models import User
from app.extensions import db
from app.utils.auth import admin_only
from app.utils.mailer import send_email
from config import Config

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


@admin_bp.route("/approve-user/<user_id>", methods=["POST"])
@admin_only
def approve_user(user_id):
    """
    Approve a user's API key request (admin-only).

    Endpoint:
    ---------
    POST /api/v1/admin/approve-user/<user_id>

    Headers:
    --------
    - Authorization: Bearer <Admin user's personal API key>
      OR
    - X-STATIC-KEY: <Hermes static API key>

    Description:
    ------------
    Admins can approve a user's pending API key request. This will encrypt and store the user's API key,
    mark the user as approved, and send an approval email to the user.

    URL Parameters:
    ---------------
    - user_id: ID of the user to approve.

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": true,
        "user_id": "<user_id>",
        "api_key": "<approved_api_key>"
    }

    If already approved:
    Status Code: 200
    {
        "message": "User already approved"
    }

    Response (Errors):
    ------------------
    Status Code: 404
    {
        "error": "User not found"
    }

    Status Code: 400
    {
        "error": "No pending API key found for this user"
    }

    Status Code: 403
    {
        "error": "Admin access required"
    }

    Example CURL:
    -------------
    # Using Bearer token (admin personal API key)
    curl -X POST http://localhost:5000/api/v1/admin/approve-user/<user_id> \
        -H "Authorization: Bearer <admin_api_key>"

    # Using Hermes static key
    curl -X POST http://localhost:5000/api/v1/admin/approve-user/<user_id> \
        -H "X-STATIC-KEY: <hermes_static_key>"
    """
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
    try:
        user.api_key = user.api_key_plain
        user.api_key_plain = None
        user.api_key_approved = True
        db.session.commit()
        logger.info(f"User {user_id} API key approved and committed to DB")
    except Exception as e:
        logger.error(f"Error approving user {user_id}: {str(e)}")
        return jsonify({"error": "Database error during approval"}), 500

    # Send email to the user confirming the approval
    try:
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
        logger.info(f"Approval email sent to user {user_id} ({user.email})")
    except Exception as e:
        logger.error(f"Failed to send approval email to user {user_id}: {str(e)}")

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
    logger.info("Admin requested list of all users")
    try:
        users = User.query.all()
        logger.info(f"Fetched {len(users)} users from database")
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({"error": "Database error"}), 500

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
    logger.debug(f"User list response: {user_list}")
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
    logger.info(f"Admin attempting to delete user {user_id}")
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User not found for deletion: {user_id}")
        return jsonify({"error": "User not found"}), 404

    try:
        db.session.delete(user)
        db.session.commit()
        logger.info(f"User {user_id} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({"error": "Database error during deletion"}), 500

    return jsonify({
        "success": True,
        "message": "User deleted successfully",
        "user_id": user_id
    })