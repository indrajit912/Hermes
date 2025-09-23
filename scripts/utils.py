# Some utility functions
#
# Author: Indrajit Ghosh
# Created On: May 10, 2025
#
from datetime import datetime, timezone

def utcnow():
    """
    Get the current UTC datetime.

    Returns:
        datetime: A datetime object representing the current UTC time.
    """
    return datetime.now(timezone.utc)