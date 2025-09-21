import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise ValueError("FERNET_KEY not found in .env")

fernet = Fernet(FERNET_KEY.encode())

def encrypt_value(value: str):
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(token: str):
    return fernet.decrypt(token.encode()).decode()
