import logging

from flask import Blueprint, jsonify, request

from app.models import User
from app.extensions import db
from app.utils.auth import admin_only, log_request
from app.utils.mailer import send_email
from config import Config

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


@admin_bp.route("/approve-user/<user_id>", methods=["POST"])
@admin_only
@log_request
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


@admin_bp.route("/users", methods=["GET"])
@admin_bp.route("/users/<user_id>", methods=["GET"])
@admin_only
@log_request
def list_users_admin(user_id=None):
    """
    List all users or get a single user (admin-only).

    Endpoint:
    ---------
    GET /api/v1/admin/users           → returns all users
    GET /api/v1/admin/users/<user_id> → returns a single user

    Headers:
    --------
    - Authorization: Bearer <Admin user's personal API key>

    Description:
    ------------
    Admins can retrieve detailed information about users registered in the Hermes system.
    - When calling `/users`, the response includes all users with their basic info, 
      email bot counts, Hermes default bot usage, and metrics across the system.
    - When calling `/users/<user_id>`, the response returns detailed info for the specified user.

    Response (Success - all users):
    -------------------------------
    Status Code: 200
    {
        "success": True,
        "users": [
            {
                "id": "<user_id>",
                "name": "Alice",
                "email": "alice@example.com",
                "api_key_approved": true,
                "is_admin": false,
                "api_key": "<encrypted_api_key>",
                "api_key_plain": "<plain_api_key_if_approved>",
                "date_joined": "<ISO timestamp>",
                "email_bot_count": 2,
                "email_bots": [
                    {"bot_id": "<bot_id>", "bot_username": "AliceBot"}
                ],
                "hermes_default_usage": 3
            },
            ...
        ],
        "metrics": {
            "total_users": 50,
            "total_email_bots": 120,
            "user_with_most_email_bots": {"id": "<user_id>", "name": "Bob", "email_bot_count": 10},
            "user_with_highest_hermes_usage": {"id": "<user_id>", "name": "Charlie", "hermes_default_usage": 7},
            "top_3_hermes_default_users": [
                {"id": "<user_id>", "name": "Charlie", "hermes_default_usage": 7},
                {"id": "<user_id>", "name": "Alice", "hermes_default_usage": 5},
                {"id": "<user_id>", "name": "Eve", "hermes_default_usage": 4}
            ]
        }
    }

    Response (Success - single user):
    ---------------------------------
    Status Code: 200
    {
        "success": True,
        "user": {
            "id": "<user_id>",
            "name": "Alice",
            "email": "alice@example.com",
            "api_key_approved": true,
            "is_admin": false,
            "api_key": "<encrypted_api_key>",
            "api_key_plain": "<plain_api_key_if_approved>",
            "date_joined": "<ISO timestamp>",
            "email_bot_count": 2,
            "email_bots": [
                {"bot_id": "<bot_id>", "bot_username": "AliceBot"}
            ],
            "hermes_default_usage": 3
        }
    }

    Response (Errors):
    ------------------
    Status Code: 403
    {
        "error": "Admin access required"
    }

    Status Code: 404 (single user)
    {
        "error": "User not found"
    }

    Example CURL:
    -------------
    # Get all users
    curl -X GET http://localhost:5000/api/v1/admin/users \
        -H "Authorization: Bearer <admin_api_key>"

    # Get single user
    curl -X GET http://localhost:5000/api/v1/admin/users/<user_id> \
        -H "Authorization: Bearer <admin_api_key>"

    # Using Hermes static key
    curl -X GET http://localhost:5000/api/v1/admin/users \
        -H "X-STATIC-KEY: <hermes_static_key>"
    """

    if user_id:
        logger.info(f"Admin requested details for user_id={user_id}")
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "api_key_approved": user.api_key_approved,
                "is_admin": user.is_admin,
                "api_key": user.api_key,
                "api_key_plain": user.api_key_plain,
                "date_joined": user.date_joined_iso,
                "email_bot_count": user.email_bot_count,
                "usage_summary": user.usage_summary(),
                "hermes_default_usage": user.hermes_default_usage,
                "email_bots": [
                    {"bot_id": bot.id, "bot_username": bot.username}
                    for bot in user.email_bots
                ],
            }
            return jsonify({"success": True, "user": user_data})

        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}", exc_info=True)
            return jsonify({"error": "Database error"}), 500

    else:
        logger.info("Admin requested list of all users")
        try:
            users = User.query.all()
        except Exception as e:
            logger.error(f"Error fetching users: {str(e)}", exc_info=True)
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
                "date_joined": u.date_joined_iso,
                "email_bot_count": u.email_bot_count,
                "email_bots": [
                    {"bot_id": bot.id, "bot_username": bot.username}
                    for bot in u.email_bots
                ],
            }
            for u in users
        ]
        
        # ----------------------------
        # Dynamic Metrics Calculation
        # ----------------------------
        total_users = len(users)
        total_email_bots = sum(u.email_bot_count for u in users)
        most_email_bots_user = max(users, key=lambda u: u.email_bot_count, default=None)
        most_hermes_usage_user = max(users, key=lambda u: u.hermes_default_usage, default=None)
        top_3_hermes_users = sorted(users, key=lambda u: u.hermes_default_usage, reverse=True)[:3]

        metrics = {
            "total_users": total_users,
            "total_email_bots": total_email_bots,
            "user_with_most_email_bots": {
                "id": most_email_bots_user.id,
                "name": most_email_bots_user.name,
                "email_bot_count": most_email_bots_user.email_bot_count
            } if most_email_bots_user else None,
            "user_with_highest_hermes_usage": {
                "id": most_hermes_usage_user.id,
                "name": most_hermes_usage_user.name,
                "hermes_default_usage": most_hermes_usage_user.hermes_default_usage
            } if most_hermes_usage_user else None,
            "top_3_hermes_default_users": [
                {"id": u.id, "name": u.name, "hermes_default_usage": u.hermes_default_usage}
                for u in top_3_hermes_users
            ]
        }

        return jsonify({"success": True, "users": user_list, "metrics": metrics})


@admin_bp.route("/delete-user/<user_id>", methods=["DELETE"])
@admin_only
@log_request
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

# -------------------------
# BLOCK / UNBLOCK USER
# -------------------------
@admin_bp.route("/block-user/<user_id>", methods=["POST"])
@admin_only
@log_request
def block_user(user_id):
    """
    Block or unblock a user (admin-only).

    Endpoint:
    ---------
    POST /api/v1/admin/block-user/<user_id>

    Headers:
    --------
    - Authorization: Bearer <Admin user's personal API key>
      OR
    - X-STATIC-KEY: <Hermes static API key>

    Description:
    ------------
    Admins can block or unblock a user account using this endpoint.
    A blocked user will not be able to access any API endpoints that require
    a personal API key. Passing "block": true will block the user, 
    while "block": false will unblock them.

    URL Parameters:
    ---------------
    - user_id: ID of the user to block/unblock.

    Request JSON:
    -------------
    {
        "block": true  # or false to unblock
    }

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "message": "User blocked successfully",
        "user_id": "<user_id>",
        "is_blocked": true
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
    # Block a user
    curl -X POST http://localhost:5000/api/v1/admin/block-user/<user_id> \
        -H "Authorization: Bearer <admin_api_key>" \
        -H "Content-Type: application/json" \
        -d '{"block": true}'

    # Unblock a user
    curl -X POST http://localhost:5000/api/v1/admin/block-user/<user_id> \
        -H "Authorization: Bearer <admin_api_key>" \
        -H "Content-Type: application/json" \
        -d '{"block": false}'
    """
    logger.info(f"Admin attempting to block/unblock user {user_id}")
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User not found for block/unblock: {user_id}")
        return jsonify({"error": "User not found"}), 404

    data = request.json
    block = data.get("block", True)  # default to block if not provided

    try:
        user.is_blocked = bool(block)
        db.session.commit()
        status_msg = "blocked" if user.is_blocked else "unblocked"
        logger.info(f"User {user_id} successfully {status_msg}")
    except Exception as e:
        logger.error(f"Error updating block status for user {user_id}: {str(e)}")
        return jsonify({"error": "Database error"}), 500

    return jsonify({
        "success": True,
        "message": f"User {status_msg} successfully",
        "user_id": user_id,
        "is_blocked": user.is_blocked
    })
