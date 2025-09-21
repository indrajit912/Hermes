"""
Hermes - run.py
Author: Indrajit Ghosh
Created On: Sep 20, 2025

Hermes (Greek Mythology)
------------------------
Named after Hermes, the Greek god of messengers, communication, and travel, 
symbolizing speed, reliability, and seamless delivery of messages.

This is the entry point for the Hermes Email API server.

Key Concepts:

1. Static API Key
-----------------
- Purpose: For trusted applications or services that you control to directly access the Hermes API.
- How it works: 
    * Stored securely in the server's `.env` file as `API_STATIC_KEY`.
    * Applications include this key in the request headers: "X-API-KEY".
    * Hermes verifies this key before allowing access.
- Use case: Internal apps, automated scripts, or other backend services.

2. User API Keys
----------------
- Purpose: For individual users of Hermes to send emails via the API.
- How it works:
    * Users register and receive a unique personal API key (after admin approval).
    * The key is stored encrypted in the Hermes database.
    * Users include this key in requests to authenticate themselves.
- Use case: Regular Hermes users who want to send emails securely via API.

Notes:
- Static API Key and User API Keys are separate and serve different purposes.
- Users do not use the Static API Key; trusted apps do not use individual user keys.
- Emails are sent using the configured Bot email in `.env` (BOT_EMAIL and BOT_PASSWORD).

Example Usage:

# Using Static API Key (trusted apps)
import requests

headers = {"X-API-KEY": "<STATIC_API_KEY>"}
data = {"to": "alice@example.com", "subject": "Hello", "body": "Test"}
response = requests.post("http://hermes.com/send-email", json=data, headers=headers)

# Using User API Key (registered Hermes user)
headers = {"X-USER-KEY": "<USER_API_KEY>"}
data = {"to": "bob@example.com", "subject": "Hi", "body": "Hello Bob!"}
response = requests.post("http://hermes.com/send-email", json=data, headers=headers)
"""


from app import create_app

app = create_app()
