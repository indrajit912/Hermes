

# Hermes API

Hermes is a free, secure, and developer-friendly API for sending emails from your applications. It provides personal API keys, EmailBot management, and robust admin workflows—no need to set up your own email server.

## What is Hermes?

Hermes lets you send emails programmatically using a simple REST API. You can use your personal API key or create EmailBots for custom sender addresses. All sensitive data is encrypted, and admin approval is required for new users.

## Key Features

- **Send Emails via API**: Integrate email sending into any app with a single POST request.
- **Personal API Keys**: Register and get your own API key (admin approval required).
- **EmailBot Management**: Create, update, and delete EmailBots for custom sender addresses.
- **Admin Controls**: Approve users, manage roles, rotate encryption keys, and view all users.
- **Security**: All sensitive fields (API keys, emails, passwords) are encrypted.
- **Activity Logs**: Fetch your recent API activity logs.

## API Endpoints

### User Endpoints

- `POST /api/v1/register` — Request a personal API key (admin approval required).
- `POST /api/v1/send-email` — Send an email using your API key or an EmailBot.
- `POST /api/v1/apikey/rotate` — Rotate your personal API key.
- `POST /api/v1/emailbot` — Add a new EmailBot.
- `GET /api/v1/emailbot` — List your EmailBots.
- `PUT /api/v1/emailbot/<bot_id>` — Update an EmailBot.
- `DELETE /api/v1/emailbot/<bot_id>` — Delete an EmailBot.
- `GET /api/v1/logs` — Fetch your recent API activity logs.

### Admin Endpoints

- `POST /api/v1/admin/approve-user/<user_id>` — Approve a pending user.
- `GET /api/v1/admin/list-users` — List all registered users.
- `DELETE /api/v1/admin/delete-user/<user_id>` — Delete a user.

## Example: Send Email

```http
POST /api/v1/send-email
Authorization: Bearer <User personal API key>
Content-Type: application/json

{
  "bot_id": "<optional: EmailBot ID>",
  "from_name": "Your App",
  "to": ["recipient@example.com"],
  "subject": "Hello from Hermes",
  "email_plain_text": "Plain text body",
  "email_html_text": "<p>HTML body</p>",
  "cc": ["cc@example.com"],
  "bcc": ["bcc@example.com"],
  "attachments": ["path/to/file.pdf"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email sent"
}
```

See more details in [`docs/send_email.md`](./docs/send_email.md).

## CLI Utilities

Run management scripts from the `scripts/` directory:

```bash
# Create a user
python scripts/manage_users.py create --name "Alice" --email "alice@example.com"

# Approve a user
python scripts/manage_users.py approve alice@example.com

# Promote to admin
python scripts/manage_users.py update alice@example.com --make-admin

# Delete a user
python scripts/manage_users.py delete alice@example.com

# List users
python scripts/manage_users.py list

# Rotate encryption key
python scripts/rotate_key.py
```

## Security Notes

- API keys are displayed only once after approval.
- All sensitive values are encrypted in the database.
- Email notifications are sent on approval.
- Use the key rotation script with care.

---

**Maintainer:** [Indrajit Ghosh](https://indrajitghosh.onrender.com)

