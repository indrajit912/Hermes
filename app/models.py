# models.py

import uuid
from app.extensions import db
from app.utils.crypto import encrypt_value, decrypt_value

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    api_key_encrypted = db.Column(db.String(256), unique=True, nullable=True)  # encrypted
    api_key_plain_encrypted = db.Column(db.String(128), nullable=True)  # store plain only until approval
    is_admin = db.Column(db.Boolean, default=False)
    api_key_approved = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User {self.email}>"

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

    
class EmailBot(db.Model):
    __tablename__ = "email_bot"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, db.ForeignKey("user.id"), nullable=False)
    username = db.Column(db.String(50), nullable=True)  # optional bot name
    email_encrypted = db.Column(db.String(256), nullable=False)
    password_encrypted = db.Column(db.String(256), nullable=False)
    smtp_server = db.Column(db.String(128), nullable=False, default="smtp.gmail.com")
    smtp_port = db.Column(db.Integer, nullable=False, default=587)

    # Relationship to user
    user = db.relationship("User", backref=db.backref("email_bots", lazy=True))

    def __repr__(self):
        return f"<EmailBot {self.username or self.email}>"

    @property
    def email(self):
        """Return decrypted email"""
        return decrypt_value(self.email_encrypted)

    @email.setter
    def email(self, value):
        """Encrypt and store email"""
        self.email_encrypted = encrypt_value(value)

    @property
    def password(self):
        """Return decrypted password"""
        return decrypt_value(self.password_encrypted)

    @password.setter
    def password(self, value):
        """Encrypt and store password"""
        self.password_encrypted = encrypt_value(value)
