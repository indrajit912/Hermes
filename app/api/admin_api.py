from flask import Blueprint, jsonify
from app.models import User
from app.extensions import db
from app.utils.auth import admin_only

admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


@admin_bp.route("/approve-user/<user_id>", methods=["POST"])
@admin_only
def approve_api_key(user_id):
    """
    Approve a pending user's API key (admin-only).

    Endpoint: POST /api/v1/admin/approve-user/<user_id>

    Description:
    ------------
    Admins can approve a user’s API key using this endpoint. Once approved,
    the API key will be encrypted automatically by the User model and returned
    in plaintext **only once**.

    Headers:
    --------
    - X-API-KEY: <Admin user's personal API key> OR
    - X-STATIC-KEY: <Hermes static API key>

    URL Parameters:
    ---------------
    - user_id: ID of the user to approve

    Response (Success):
    -------------------
    Status Code: 200
    {
        "success": True,
        "user_id": "<user_id>",
        "api_key": "<decrypted API key for one-time use>"
    }

    Response (Errors):
    ------------------
    Status Code: 404
    {
        "error": "User not found"
    }
    OR
    Status Code: 200
    {
        "message": "User already approved"
    }
    OR
    Status Code: 400
    {
        "error": "No pending API key found for this user"
    }
    OR
    Status Code: 403
    {
        "error": "Admin access required"
    }
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.api_key_approved:
        return jsonify({"message": "User already approved"}), 200
    if not user.api_key_plain:
        return jsonify({"error": "No pending API key found for this user"}), 400

    # Use the property setter to encrypt automatically
    user.api_key = user.api_key_plain
    user.api_key_plain = None
    user.api_key_approved = True
    db.session.commit()

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

    Endpoint: GET /api/v1/admin/list-users

    Headers:
    --------
    - X-API-KEY: <Admin user's personal API key> OR
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
            "email_bots": u.email_bots
        } for u in users
    ]
    return jsonify({"success": True, "users": user_list})
