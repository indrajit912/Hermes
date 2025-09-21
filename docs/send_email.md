## Send Email API

This endpoint allows you to send an email by providing the necessary details such as recipient addresses, subject, and email content.

### Request

- **Method**: POST
- **URL**: `http://localhost:8080/api/v1/send-email`
- **Request Body**: The request body must be in JSON format and include the following parameters:
    - `to` (string): The primary recipient's email address.
    - `subject` (string): The subject line of the email.
    - `email_plain_text` (string): The plain text content of the email.
    - `cc` (string, optional): The email address to send a carbon copy.
    - `bcc` (string, optional): The email address to send a blind carbon copy.

**Example Request Body**:

``` json
{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "email_plain_text": "Email body content.",
  "cc": "cc@example.com",
  "bcc": "bcc@example.com"
}

 ```

### Response

Upon successful execution, the API will return a JSON response with the following structure:

- `message` (string): A message indicating the result of the operation (may be empty).
- `success` (boolean): Indicates whether the email was sent successfully.
    

**Example Response**:

``` json
{
  "message": "",
  "success": true
}

 ```

### Status Codes

- **200 OK**: The email was sent successfully.
- Other status codes may indicate errors or issues with the request.