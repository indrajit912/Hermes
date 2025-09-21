# Hermes

Hermes is a Flask-based API system with user authentication via API keys, admin approval workflows, and support for Email Bots.
It includes both REST API endpoints and CLI scripts for managing users, keys, and configurations.

---

## Features

* **User Registration & API Keys**

  * Users can register via API and receive a pending API key.
  * Admins approve API keys before they become active.
  * Approved keys are delivered via email to the user.

* **Admin Utilities**

  * Approve/reject users.
  * List all users.
  * Manage user roles (promote to admin / revoke admin).
  * Rotate encryption keys safely.

* **Email Bots**

  * Users can create email bots with encrypted credentials.
  * Supports multiple bots per user.
  * Secure storage of email + app password.

* **Security**

  * All sensitive fields (API keys, emails, passwords) are encrypted.
  * API access requires a valid `Authorization: Bearer <API_KEY>` header.
  * Admin routes are restricted to admins only.

---

## API Overview

### User APIs

* **Request API Key**
  `POST /api/v1/request-api-key`

* **Add Email Bot**
  `POST /api/v1/emailbot`

* **List Email Bots**
  `GET /api/v1/emailbot`

### Admin APIs

* **Approve API Key**
  `POST /api/v1/admin/approve-api-key/<user_id>`

* **List Users**
  `GET /api/v1/admin/list-users`

### Send Email API - [Click here](./docs/send_email.md)


---

## CLI Utilities

Examples:

```bash
# Create user
python scripts/manage_users.py create --name "Alice" --email "alice@example.com"

# Approve user
python scripts/manage_users.py approve alice@example.com

# Update user (make admin)
python scripts/manage_users.py update alice@example.com --make-admin

# Delete user
python scripts/manage_users.py delete alice@example.com

# List all users
python scripts/manage_users.py list

# Rotate encryption key
python scripts/rotate_key.py
```

---

## Notes

* API keys are shown **only once** after admin approval.
* All sensitive values are encrypted in the database.
* Email notifications are sent on approval.
* Rotate encryption keys carefully using the provided script.

---

📧 Maintainer: **Indrajit Ghosh**

