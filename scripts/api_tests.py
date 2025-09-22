import requests
import json

PERSONAL_API_KEY = "e520db06-d81e-4eb5-b1eb-70c3807e92b9"

url = "http://localhost:8080/api/v1/send-email"

payload = json.dumps({
  "to": ["rs_math1902@isibang.ac.in"],
  "from_name": "Kapoor's Cafe",
  "subject": "Invitation to Cafe",
  "email_plain_text": "Hello there!",
  "email_html_text": "<h1>Hello there!</h1>",
  "cc": [],
  "bcc": [],
  "attachments": []
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {PERSONAL_API_KEY}'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
