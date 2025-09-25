# Some utility functions
#
# Author: Indrajit Ghosh
# Created On: May 10, 2025
#
from datetime import datetime, timezone
from email_validator import validate_email, EmailNotValidError

def utcnow():
    """
    Get the current UTC datetime.

    Returns:
        datetime: A datetime object representing the current UTC time.
    """
    return datetime.now(timezone.utc)

def is_valid_email_address(address: str):
    """
    Validate an email address for correct format and MX record existence.
    Returns (True, None) if valid, else (False, error_message).
    """
    try:
        # Step 1: Validate syntax
        v = validate_email(address)
        email = v["email"]  # normalized form
        domain = v["domain"]
    except EmailNotValidError as e:
        return False, f"Invalid email format: {str(e)}"

    return True, None