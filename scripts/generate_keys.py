# generate_keys.py
import uuid
from cryptography.fernet import Fernet

def generate_static_api_key():
    return uuid.uuid4().hex  # 32 hex characters

def generate_fernet_key():
    return Fernet.generate_key().decode()  # base64-encoded string

if __name__ == "__main__":
    static_api_key = generate_static_api_key()
    fernet_key = generate_fernet_key()

    print("STATIC_API_KEY=", static_api_key)
    print("FERNET_KEY=", fernet_key)
