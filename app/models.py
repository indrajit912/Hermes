# models.py

import uuid
from datetime import timezone
from app.extensions import db
from app.utils.crypto import encrypt_value, decrypt_value
from scripts.utils import utcnow

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4().hex))
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    api_key_encrypted = db.Column(db.String(256), unique=True, nullable=True)  # encrypted
    api_key_plain_encrypted = db.Column(db.String(128), nullable=True)  # store plain only until approval
    is_admin = db.Column(db.Boolean, default=False)
    api_key_approved = db.Column(db.Boolean, default=False)
    hermes_default_usage = db.Column(db.Integer, default=0)

    date_joined = db.Column(db.DateTime(timezone=True), default=utcnow)

    # Cascade delete: remove all associated EmailBots when this user is deleted
    email_bots = db.relationship(
        "EmailBot",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<User {self.email}>"
    
    @property
    def date_joined_iso(self):
        """
        Return the date_joined in ISO 8601 format with timezone info.
        """
        if self.date_joined:
            return self.date_joined.astimezone(timezone.utc).isoformat()
        return None

    @property
    def email_bot_count(self):
        """Return the total number of EmailBots owned by this user"""
        return len(self.email_bots)
    

    # --------- API Key (Encrypted) ------------
    @property
    def api_key(self):
        """Return decrypted API key"""
        if self.api_key_encrypted:
            return decrypt_value(self.api_key_encrypted)
        return None

    @api_key.setter
    def api_key(self, value):
        """Encrypt and store API key"""
        if value:
            self.api_key_encrypted = encrypt_value(value)
        else:
            self.api_key_encrypted = None

    def _set_api_key(self, value, fernet_key):
        """This method is used during key rotation"""
        if value:
            self.api_key_encrypted = encrypt_value(value, key=fernet_key)
        else:
            self.api_key_encrypted = None

    @property
    def total_api_calls(self) -> int:
        """Total API calls made by this user"""
        return len(self.logs)  # uses backref relationship

    def count_endpoint_usage(self, endpoint: str) -> int:
        """Count number of calls to a specific endpoint"""
        return sum(1 for log in self.logs if log.endpoint == endpoint)

    @property
    def send_email_usage(self) -> int:
        """Number of times user has used the send-email API"""
        return self.count_endpoint_usage("/api/v1/send-email")

    @property
    def last_activity(self):
        """Timestamp of the last API call"""
        if not self.logs:
            return None
        return max(log.timestamp for log in self.logs)

    @property
    def success_rate(self) -> float:
        """Ratio of successful (200) responses"""
        total = len(self.logs)
        if total == 0:
            return 0.0
        successes = sum(1 for log in self.logs if log.status_code == 200)
        return successes / total

    def usage_summary(self) -> dict:
        """Return a dictionary of all relevant usage stats"""
        return {
            "total_api_calls": self.total_api_calls,
            "send_email_calls": self.send_email_usage,
            "last_activity": (
                self.last_activity.astimezone(timezone.utc).isoformat()
                if self.last_activity else None
            ),
            "success_rate": round(self.success_rate, 2),
        }


    # --------- API Key Plain (Encrypted) ------------
    @property
    def api_key_plain(self):
        """Return decrypted plain API key"""
        if self.api_key_plain_encrypted:
            return decrypt_value(self.api_key_plain_encrypted)
        return None

    @api_key_plain.setter
    def api_key_plain(self, value):
        """Encrypt and store plain API key"""
        if value:
            self.api_key_plain_encrypted = encrypt_value(value)
        else:
            self.api_key_plain_encrypted = None

    def _set_api_key_plain(self, value, fernet_key):
        """This method is used during key rotation"""
        if value:
            self.api_key_plain_encrypted = encrypt_value(value, key=fernet_key)
        else:
            self.api_key_plain_encrypted = None

    
class EmailBot(db.Model):
    __tablename__ = "email_bot"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4().hex))
    user_id = db.Column(db.String, db.ForeignKey("user.id"), nullable=False)
    username = db.Column(db.String(50), nullable=True)  # optional bot name
    email_encrypted = db.Column(db.String(256), nullable=False)
    password_encrypted = db.Column(db.String(256), nullable=False)
    smtp_server = db.Column(db.String(128), nullable=False, default="smtp.gmail.com")
    smtp_port = db.Column(db.Integer, nullable=False, default=587)

    date_created = db.Column(db.DateTime(timezone=True), default=utcnow)

    # Relationship to user
    user = db.relationship("User", back_populates="email_bots")

    def __repr__(self):
        return f"<EmailBot {self.username or self.email}>"
    
    @property
    def date_created_iso(self):
        """
        Return the date_created in ISO 8601 format with timezone info.
        """
        if self.date_created:
            return self.date_created.astimezone(timezone.utc).isoformat()
        return None

    @property
    def email(self):
        """Return decrypted email"""
        return decrypt_value(self.email_encrypted)

    @email.setter
    def email(self, value):
        """Encrypt and store email"""
        self.email_encrypted = encrypt_value(value)
    
    def _set_email(self, value, fernet_key):
        """This method is used during key rotation"""
        self.email_encrypted = encrypt_value(value, key=fernet_key)

    @property
    def password(self):
        """Return decrypted password"""
        return decrypt_value(self.password_encrypted)

    @password.setter
    def password(self, value):
        """Encrypt and store password"""
        self.password_encrypted = encrypt_value(value)

    def _set_password(self, value, fernet_key):
        """This method is used during key rotation"""
        self.password_encrypted = encrypt_value(value, key=fernet_key)


class Log(db.Model):
    __tablename__ = "log"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4().hex))
    user_id = db.Column(db.String, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    endpoint = db.Column(db.String(256), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationship to user with cascade delete
    user = db.relationship(
        "User",
        backref=db.backref("logs", lazy=True, cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<Log {self.method} {self.endpoint} by {self.user_id} at {self.timestamp}>"
    
    @property
    def timestamp_iso(self):
        """
        Return the timestamp in ISO 8601 format with timezone info.
        """
        if self.timestamp:
            return self.timestamp.astimezone(timezone.utc).isoformat()
        return None
