import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("FERNET_KEY not found in .env")

# Default cipher object
cipher = Fernet(FERNET_KEY.encode())


def encrypt_value(value: str, key: str = None):
    """
    Encrypt a string using Fernet.
    If no key is provided, use the global cipher.
    """
    fernet = Fernet(key.encode()) if key else cipher
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(token: str, key: str = None):
    """
    Decrypt a string using Fernet.
    If no key is provided, use the global cipher.
    """
    fernet = Fernet(key.encode()) if key else cipher
    return fernet.decrypt(token.encode()).decode()
