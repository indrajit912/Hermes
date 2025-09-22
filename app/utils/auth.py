from flask import request, current_app, jsonify
from functools import wraps
from app.models import User
from app.utils.crypto import decrypt_value

def get_current_user():
    """
    Returns the User object if the request has a valid personal API key.
    Returns None if invalid.

    Checks headers:
    ---------------
    - Authorization: Bearer <user_api_key>
    - X-STATIC-KEY: <Hermes static key> (optional, for trusted apps)
    """
    # Check static key first
    static_key = request.headers.get("X-STATIC-KEY")
    if static_key and static_key == current_app.config.get("API_STATIC_KEY"):
        return None  # static key requests are trusted, but no specific user

    # Check personal API key
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    api_key = auth_header.replace("Bearer ", "")
    if not api_key:
        return None

    users = User.query.filter_by(api_key_approved=True).all()
    for user in users:
        try:
            if user.api_key == api_key:  # api_key property decrypts automatically
                return user
        except Exception:
            continue

    return None

def admin_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check for static API key first (trusted apps)
        static_key = request.headers.get("X-STATIC-KEY")
        
        if static_key and static_key == current_app.config.get("API_STATIC_KEY"):
            return f(*args, **kwargs)

        # Check for logged-in admin
        user = get_current_user()
        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)
    return decorated

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not key:
            return jsonify({"error": "API key missing"}), 401

        # Look up ALL users (approved and not)
        users = User.query.all()
        for user in users:
            try:
                if user.api_key == key:
                    if not user.api_key_approved:
                        return jsonify({
                            "error": "Your API key is awaiting admin approval. "
                                     "You’ll receive an email with your API key once approved."
                        }), 403
                    return f(*args, **kwargs)
            except Exception:
                continue

        return jsonify({"error": "Invalid API key"}), 403

    return decorated